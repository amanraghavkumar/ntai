"""Music Agent — live YouTube search. No invented tracks."""

from __future__ import annotations

import json
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

AGENT_NAME = "music_agent"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
INNERTUBE_URL = "https://www.youtube.com/youtubei/v1/search?prettyPrint=false"
CLIENT_VERSION = "2.20240815.01.00"
CTX = ssl.create_default_context()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _text_of(node: Any) -> str:
    if not node:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if node.get("simpleText"):
            return str(node["simpleText"])
        runs = node.get("runs") or []
        return "".join(str(r.get("text") or "") for r in runs if isinstance(r, dict))
    return ""


def _is_live(vr: dict[str, Any]) -> bool:
    badges = vr.get("badges") or []
    for badge in badges:
        label = _text_of((badge.get("metadataBadgeRenderer") or {}).get("label"))
        if label.lower() == "live":
            return True
    for overlay in vr.get("thumbnailOverlays") or []:
        status = (overlay.get("thumbnailOverlayTimeStatusRenderer") or {}).get("style")
        if status == "LIVE":
            return True
    return False


def _walk_videos(obj: Any):
    if isinstance(obj, dict):
        if "videoRenderer" in obj and isinstance(obj["videoRenderer"], dict):
            yield obj["videoRenderer"]
        for value in obj.values():
            yield from _walk_videos(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from _walk_videos(value)


def _normalize(vr: dict[str, Any]) -> dict[str, Any] | None:
    video_id = vr.get("videoId")
    title = _text_of(vr.get("title")).strip()
    if not video_id or not title:
        return None
    if _is_live(vr):
        return None
    channel = _text_of(vr.get("ownerText") or vr.get("longBylineText") or vr.get("shortBylineText"))
    length = _text_of(vr.get("lengthText"))
    thumbs = ((vr.get("thumbnail") or {}).get("thumbnails")) or []
    thumb = ""
    if thumbs:
        thumb = thumbs[-1].get("url") or ""
    if not thumb:
        thumb = f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    return {
        "id": video_id,
        "video_id": video_id,
        "title": title,
        "channel": channel or "YouTube",
        "duration": length,
        "thumbnail": thumb,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "source": "youtube",
    }


class MusicAgent:
    def __init__(self) -> None:
        self.name = AGENT_NAME
        self.status = "idle"
        self.current_action = "YouTube search ready."
        self.last_error: str | None = None
        self.query = ""
        self.results: list[dict[str, Any]] = []
        self.now_playing: dict[str, Any] | None = None
        self.index = 0
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._hydrate()

    def _hydrate(self) -> None:
        path = DATA_DIR / "last_run.json"
        if not path.exists():
            return
        try:
            pack = json.loads(path.read_text(encoding="utf-8"))
            self.results = pack.get("results") or []
            self.query = pack.get("query") or ""
            self.now_playing = pack.get("now_playing")
            self.index = int(pack.get("index") or 0)
            if self.results:
                self.status = "done"
                self.current_action = f"Last search: {self.query} · {len(self.results)} tracks."
        except Exception:
            pass

    def _persist(self) -> None:
        (DATA_DIR / "last_run.json").write_text(
            json.dumps(
                {
                    "saved_at": utc_now(),
                    "query": self.query,
                    "index": self.index,
                    "now_playing": self.now_playing,
                    "results": self.results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "current_action": self.current_action,
            "query": self.query,
            "results": self.results,
            "now_playing": self.now_playing,
            "index": self.index,
            "last_error": self.last_error,
            "source": "youtube",
        }

    def set_now_playing(self, video_id: str) -> dict[str, Any]:
        for i, row in enumerate(self.results):
            if row.get("video_id") == video_id:
                self.index = i
                self.now_playing = row
                self.current_action = f"Queued {row['title']}"
                self._persist()
                return self.snapshot()
        raise KeyError(video_id)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        raw = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=raw,
            method="POST",
            headers={
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-YouTube-Client-Name": "1",
                "X-YouTube-Client-Version": CLIENT_VERSION,
                "Origin": "https://www.youtube.com",
                "Referer": "https://www.youtube.com/",
            },
        )
        with urlopen(req, timeout=16, context=CTX) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))

    def _get_text(self, url: str) -> str:
        req = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept-Language": "en-IN,en;q=0.9",
                "Accept": "text/html",
            },
        )
        with urlopen(req, timeout=16, context=CTX) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def _search_innertube(self, query: str) -> list[dict[str, Any]]:
        data = self._post_json(
            INNERTUBE_URL,
            {
                "context": {
                    "client": {
                        "clientName": "WEB",
                        "clientVersion": CLIENT_VERSION,
                        "hl": "en",
                        "gl": "IN",
                    }
                },
                "query": query,
            },
        )
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for vr in _walk_videos(data):
            row = _normalize(vr)
            if not row or row["video_id"] in seen:
                continue
            seen.add(row["video_id"])
            out.append(row)
        return out

    def _search_html(self, query: str) -> list[dict[str, Any]]:
        html = self._get_text(
            "https://www.youtube.com/results?search_query=" + quote_plus(query) + "&sp=EgIQAQ%3D%3D"
        )
        match = re.search(r"ytInitialData\s*=\s*(\{.+?\});\s*</script>", html)
        if not match:
            return []
        data = json.loads(match.group(1))
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for vr in _walk_videos(data):
            row = _normalize(vr)
            if not row or row["video_id"] in seen:
                continue
            seen.add(row["video_id"])
            out.append(row)
        return out

    def search(self, query: str, limit: int = 8) -> dict[str, Any]:
        q = (query or "").strip()
        if not q:
            self.last_error = "Empty search."
            self.status = "error"
            self.current_action = "Type a song name."
            return self.snapshot()

        self.status = "fetching"
        self.current_action = f"Searching YouTube for “{q}”…"
        self.last_error = None
        self.query = q
        found: list[dict[str, Any]] = []
        errors: list[str] = []

        try:
            found = self._search_innertube(q)
        except (HTTPError, URLError, TimeoutError, ssl.SSLError, OSError, json.JSONDecodeError) as exc:
            errors.append(f"innertube: {exc}")

        if not found:
            try:
                found = self._search_html(q)
            except (HTTPError, URLError, TimeoutError, ssl.SSLError, OSError, json.JSONDecodeError) as exc:
                errors.append(f"html: {exc}")

        self.results = found[: max(1, min(limit, 12))]
        if self.results:
            self.status = "done"
            self.current_action = f"{len(self.results)} live YouTube tracks."
            if not self.now_playing:
                self.now_playing = self.results[0]
                self.index = 0
            else:
                ids = [r["video_id"] for r in self.results]
                if self.now_playing.get("video_id") in ids:
                    self.index = ids.index(self.now_playing["video_id"])
                else:
                    self.now_playing = self.results[0]
                    self.index = 0
        else:
            self.status = "error"
            self.last_error = "No YouTube results. " + (" · ".join(errors) if errors else "")
            self.current_action = self.last_error
            self.now_playing = None
            self.index = 0

        self._persist()
        return self.snapshot()


def run_once(query: str = "Arijit Singh official audio") -> dict[str, Any]:
    return MusicAgent().search(query)


if __name__ == "__main__":
    print(json.dumps(run_once(), ensure_ascii=False, indent=2)[:2000])
