"""Sector News Agent — live market news only.

Pulls Google News + ET + Moneycontrol + NSE, classifies by sector,
and forwards structured JSON to the parent News Agent.
Never invents headlines.
"""

from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from classify import SECTORS, classify, normalize_sector
from rss import utc_now
from sources import catalog, pull_feed

AGENT_NAME = "sector_news_agent"
ROOT = Path(__file__).resolve().parent
LOG_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
KEEP_PER_SECTOR = 30


def item_id(headline: str, url: str) -> str:
    return hashlib.sha1(f"{headline}|{url}".encode("utf-8", errors="ignore")).hexdigest()[:16]


class SectorNewsAgent:
    def __init__(
        self,
        on_log: Callable[[dict[str, Any]], None] | None = None,
        on_item: Callable[[dict[str, Any]], None] | None = None,
        on_status: Callable[[str], None] | None = None,
        on_action: Callable[[str], None] | None = None,
        on_step: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "Standing by for a live fetch cycle."
        self.logs: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.counts: dict[str, int] = {}
        self.steps: list[dict[str, Any]] = []
        self.last_error: str | None = None
        self.on_log = on_log
        self.on_item = on_item
        self.on_status = on_status
        self.on_action = on_action
        self.on_step = on_step
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._hydrate()

    def _hydrate(self) -> None:
        path = DATA_DIR / "last_run.json"
        if not path.exists():
            return
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
            self.items = pack.get("items") or []
            self.counts = pack.get("counts") or {}
            if self.items:
                self.status = "done"
                self.current_action = f"Last cycle: {len(self.items)} headlines on disk."
        except Exception:
            pass

    def _set_status(self, status: str, action: str | None = None) -> None:
        self.status = status
        if action:
            self.current_action = action
            if self.on_action:
                self.on_action(action)
        if self.on_status:
            self.on_status(status)

    def log(self, message: str, level: str = "info") -> dict[str, Any]:
        entry = {
            "timestamp": utc_now(),
            "level": level,
            "agent_name": self.name,
            "message": message,
        }
        self.logs.append(entry)
        if len(self.logs) > 500:
            self.logs = self.logs[-500:]
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with (LOG_DIR / f"{day}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if self.on_log:
            self.on_log(entry)
        return entry

    def _step(self, key: str, label: str, status: str, detail: str = "") -> None:
        row = {"key": key, "label": label, "status": status, "detail": detail, "at": utc_now()}
        existing = next((s for s in self.steps if s["key"] == key), None)
        if existing:
            existing.update(row)
        else:
            self.steps.append(row)
        if self.on_step:
            self.on_step(row)

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "current_action": self.current_action,
            "logs": self.logs[-80:],
            "items": list(reversed(self.items[-200:])),
            "counts": dict(self.counts),
            "steps": list(self.steps),
            "last_error": self.last_error,
        }

    def build_item(self, *, sector: str, headline: str, summary: str, source_url: str, source: str, published: str) -> dict[str, Any]:
        return {
            "id": item_id(headline, source_url),
            "agent_name": AGENT_NAME,
            "sector": sector,
            "headline": headline,
            "summary": summary or headline,
            "source_url": source_url,
            "source": source,
            "published": published,
            "timestamp": utc_now(),
            "status": "completed",
        }

    def _wanted(self, sectors: list[str] | None) -> list[str]:
        if not sectors:
            return list(SECTORS.keys())
        out: list[str] = []
        for raw in sectors:
            key = normalize_sector(raw) or ("IT" if str(raw).lower() == "it" else str(raw).lower())
            if key in SECTORS or key == "IT":
                out.append("IT" if key == "IT" else key)
        return out or list(SECTORS.keys())

    def _persist(self) -> None:
        payload = {
            "saved_at": utc_now(),
            "counts": self.counts,
            "items": self.items,
        }
        (DATA_DIR / "last_run.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def run(self, sectors: list[str] | None = None) -> list[dict[str, Any]]:
        wanted = self._wanted(sectors)
        self.items = []
        self.counts = {}
        self.steps = []
        self.last_error = None
        produced: list[dict[str, Any]] = []
        kept: dict[str, int] = {}
        seen: set[str] = set()

        self._set_status("fetching", "Opening live market sockets...")
        self.log("Sector News Agent online. Starting LIVE fetch cycle.")
        self.log(f"Target sectors: {', '.join(wanted)}")
        self._step("init", "Load sector map", "done", f"{len(wanted)} sectors")

        feeds = catalog(wanted)
        self._step("catalog", "Build source list", "done", f"{len(feeds)} live endpoints")
        self.log(f"Catalogued {len(feeds)} live endpoints (Google News + ET + Moneycontrol + NSE).")

        raw: list[tuple[dict, dict]] = []
        failures = 0
        self._step("fetch", "Fetch live feeds", "running", f"0/{len(feeds)}")
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = {pool.submit(pull_feed, feed): feed for feed in feeds}
            done = 0
            for fut in as_completed(futs):
                feed, rows, err = fut.result()
                done += 1
                self._set_status("fetching", f"Fetching {feed['label']} ({done}/{len(feeds)})...")
                if err:
                    failures += 1
                    self.log(f"{feed['label']} unavailable: {err}", level="warn")
                    continue
                self.log(f"{feed['label']}: {len(rows)} live items")
                for row in rows:
                    raw.append((feed, row))
                self._step("fetch", "Fetch live feeds", "running", f"{done}/{len(feeds)} · {len(raw)} raw")

        self._step("fetch", "Fetch live feeds", "done" if raw else "error", f"{len(raw)} headlines, {failures} sources down")
        if not raw:
            self.last_error = "All live sources failed."
            self._set_status("error", "No live source answered. Try RUN CYCLE again.")
            self.log("Cycle aborted — zero live items.", level="warn")
            return []

        self._set_status("processing", f"Classifying {len(raw)} live headlines...")
        self._step("classify", "Tag sectors", "running", str(len(raw)))
        skipped = 0
        for feed, row in raw:
            headline = row["headline"]
            summary = row.get("summary") or ""
            sector, score = classify(headline, "", feed.get("hint"))
            if not sector or score < 2 or sector not in wanted:
                skipped += 1
                continue
            url = row.get("source_url") or ""
            item = self.build_item(
                sector=sector,
                headline=headline,
                summary=summary,
                source_url=url,
                source=feed["source"],
                published=row.get("published") or utc_now(),
            )
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            self.counts[sector] = self.counts.get(sector, 0) + 1
            if kept.get(sector, 0) >= KEEP_PER_SECTOR:
                continue
            kept[sector] = kept.get(sector, 0) + 1
            produced.append(item)
            self.items.append(item)
            if self.on_item:
                self.on_item({**item, "status": "processing"})
                self.on_item(item)

        self._step("classify", "Tag sectors", "done", f"kept {len(produced)}, skipped {skipped}")
        self.log(f"Classifier kept {len(produced)} / skipped {skipped} unrelated rows.")

        mix = ", ".join(f"{k}={v}" for k, v in sorted(self.counts.items())) or "none"
        self._set_status("processing", f"Forwarding {len(produced)} items to News Agent...")
        self._step("forward", "Send to News Agent", "done", mix)
        self.log(f"Forwarding {len(produced)} structured items to news_agent ({mix}).")
        self._persist()
        self._set_status("done", f"Cycle complete. {len(produced)} live items sent to News Agent.")
        self.log("Cycle complete.")
        return produced


def run_once(sectors: list[str] | None = None) -> list[dict[str, Any]]:
    return SectorNewsAgent().run(sectors)


if __name__ == "__main__":
    items = run_once()
    print(json.dumps({"count": len(items), "sample": items[:5]}, indent=2, ensure_ascii=False))
