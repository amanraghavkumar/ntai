"""Central orb + News Agent API.

Discovers agents from /agents, runs sector_news_agent, and streams
live status to the HUD.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
AGENTS_ROOT = ROOT / "agents"
NEWS_ROOT = AGENTS_ROOT / "news_agent"
SECTOR_ROOT = NEWS_ROOT / "sector_news_agent"
FILINGS_ROOT = NEWS_ROOT / "corporate_filings_agent"
MACRO_ROOT = NEWS_ROOT / "macro_policy_agent"
SENT_ROOT = NEWS_ROOT / "sentiment_agent"
HIST_ROOT = NEWS_ROOT / "historical_correlation_agent"
PERF_ROOT = NEWS_ROOT / "news_agent_testing_performance"
AFTER_ROOT = NEWS_ROOT / "after_hours_agent"
EARN_ROOT = NEWS_ROOT / "earnings_surprise_agent"
SOCIAL_ROOT = AGENTS_ROOT / "social_agent"
REDDIT_ROOT = SOCIAL_ROOT / "reddit_flow_agent"
MUSIC_ROOT = AGENTS_ROOT / "music_agent"

sys.path.insert(0, str(NEWS_ROOT))
sys.path.insert(0, str(SECTOR_ROOT))
sys.path.insert(0, str(FILINGS_ROOT))
sys.path.insert(0, str(MACRO_ROOT))
sys.path.insert(0, str(SENT_ROOT))
sys.path.insert(0, str(HIST_ROOT))
sys.path.insert(0, str(PERF_ROOT))
sys.path.insert(0, str(AFTER_ROOT))
sys.path.insert(0, str(EARN_ROOT))
sys.path.insert(0, str(SOCIAL_ROOT))
sys.path.insert(0, str(REDDIT_ROOT))
sys.path.insert(0, str(MUSIC_ROOT))

from news_agent import NewsAgent  # noqa: E402
from sector_news_agent import SectorNewsAgent  # noqa: E402
from corporate_filings_agent import CorporateFilingsAgent  # noqa: E402
from macro_policy_agent import MacroPolicyAgent  # noqa: E402
from sentiment_agent import SentimentAgent  # noqa: E402
from historical_correlation_agent import HistoricalCorrelationAgent  # noqa: E402
from news_agent_testing_performance import NewsAgentTestingPerformance  # noqa: E402
from after_hours_agent import AfterHoursAgent  # noqa: E402
from earnings_surprise_agent import EarningsSurpriseAgent  # noqa: E402
from social_agent import SocialAgent  # noqa: E402
from reddit_flow_agent import RedditFlowAgent  # noqa: E402
from music_agent import MusicAgent  # noqa: E402

app = FastAPI(title="Agent HUD API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


class EventBus:
    def __init__(self) -> None:
        self.subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        if q in self.subscribers:
            self.subscribers.remove(q)

    def emit(self, event: str, payload: Any) -> None:
        packet = {"event": event, "payload": payload, "timestamp": utc_now()}
        dead: list[asyncio.Queue] = []
        for q in self.subscribers:
            try:
                q.put_nowait(packet)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)


bus = EventBus()


class CentralOrb:
    def __init__(self) -> None:
        self.name = "central_orb"
        self.inbox: list[dict[str, Any]] = []
        self.receiving = False
        self.last_packet_at: str | None = None
        self.active_count = 1

    def receive(self, packet: dict[str, Any]) -> None:
        self.inbox.append(packet)
        if len(self.inbox) > 400:
            self.inbox = self.inbox[-400:]
        self.receiving = True
        self.last_packet_at = utc_now()
        bus.emit("orb_receive", packet)
        bus.emit("transmit", {"from": "news_agent", "to": "central_orb", "item_id": packet.get("id")})

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "receiving": self.receiving,
            "last_packet_at": self.last_packet_at,
            "inbox_count": len(self.inbox),
            "latest": self.inbox[-8:][::-1],
        }


orb = CentralOrb()
news_parent = NewsAgent(on_forward=orb.receive)


def on_log(entry: dict[str, Any]) -> None:
    bus.emit("log", entry)


def on_item(item: dict[str, Any]) -> None:
    if item.get("status") == "completed":
        news_parent.receive_from_sub_agent(item)
    bus.emit("news_item", item)


def _on_reddit_item(item: dict[str, Any]) -> None:
    bus.emit("news_item", item)
    if item.get("status") != "completed":
        return
    social_parent.receive_from_sub_agent(item)
    # Named buzz only enters NEWS FLOW, never NEXT SESSION.
    if item.get("forward_to_news"):
        news_parent.receive_from_sub_agent(item)


def on_status(status: str) -> None:
    bus.emit("agent_status", {"agent": "sector_news_agent", "status": status})
    bus.emit("parent_status", {"agent": "news_agent", "status": "receiving" if status in {"fetching", "processing"} else "online"})


def on_action(action: str) -> None:
    bus.emit("agent_action", {"agent": "sector_news_agent", "action": action})


def on_step(step: dict[str, Any]) -> None:
    bus.emit("pipeline_step", step)


sector_agent = SectorNewsAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=on_status,
    on_action=on_action,
    on_step=on_step,
)

filings_agent = CorporateFilingsAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "corporate_filings_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "corporate_filings_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "corporate_filings_agent"}),
)

macro_agent = MacroPolicyAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "macro_policy_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "macro_policy_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "macro_policy_agent"}),
)

sentiment_agent = SentimentAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "sentiment_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "sentiment_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "sentiment_agent"}),
)

history_agent = HistoricalCorrelationAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "historical_correlation_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "historical_correlation_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "historical_correlation_agent"}),
)

perf_agent = NewsAgentTestingPerformance(
    on_log=on_log,
    on_item=lambda item: bus.emit("news_item", item),
    on_status=lambda s: bus.emit("agent_status", {"agent": "news_agent_testing_performance", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "news_agent_testing_performance", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "news_agent_testing_performance"}),
)

after_hours_agent = AfterHoursAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "after_hours_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "after_hours_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "after_hours_agent"}),
)

social_parent = SocialAgent()

reddit_agent = RedditFlowAgent(
    on_log=on_log,
    on_item=lambda item: _on_reddit_item(item),
    on_status=lambda s: bus.emit("agent_status", {"agent": "reddit_flow_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "reddit_flow_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "reddit_flow_agent"}),
)

music_agent = MusicAgent()

earnings_agent = EarningsSurpriseAgent(
    on_log=on_log,
    on_item=on_item,
    on_status=lambda s: bus.emit("agent_status", {"agent": "earnings_surprise_agent", "status": s}),
    on_action=lambda a: bus.emit("agent_action", {"agent": "earnings_surprise_agent", "action": a}),
    on_step=lambda st: bus.emit("pipeline_step", {**st, "agent": "earnings_surprise_agent"}),
)

_agent_locks: dict[str, asyncio.Lock] = {}
perf_lock = asyncio.Lock()
run_task: asyncio.Task | None = None


def lock_for(name: str) -> asyncio.Lock:
    lock = _agent_locks.get(name)
    if lock is None:
        lock = asyncio.Lock()
        _agent_locks[name] = lock
    return lock


def discover_child_agents() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for child in sorted(NEWS_ROOT.iterdir()):
        if not child.is_dir() or child.name.startswith("_") or child.name.startswith("."):
            continue
        cfg = child / f"{child.name}.config.json"
        if not cfg.exists():
            continue
        data = load_json(cfg)
        live = None
        if child.name == "sector_news_agent":
            live = sector_agent
        elif child.name == "corporate_filings_agent":
            live = filings_agent
        elif child.name == "macro_policy_agent":
            live = macro_agent
        elif child.name == "sentiment_agent":
            live = sentiment_agent
        elif child.name == "historical_correlation_agent":
            live = history_agent
        elif child.name == "news_agent_testing_performance":
            live = perf_agent
        elif child.name == "after_hours_agent":
            live = after_hours_agent
        elif child.name == "earnings_surprise_agent":
            live = earnings_agent
        found.append(
            {
                **data,
                "status": live.status if live else data.get("status", "idle"),
                "current_action": (
                    live.current_action if live else "Folder ready. Logic not wired yet."
                ),
                "item_count": len(live.items) if live else 0,
                "folder": str(child.relative_to(ROOT)),
            }
        )
    return found


def agent_graph() -> list[dict[str, Any]]:
    return [
        {
            "name": "central_orb",
            "display_name": "Central Orb",
            "role": "hub",
            "status": "receiving" if orb.receiving else "online",
            "summary": f"{len(orb.inbox)} packets in inbox",
        },
        {
            "name": "news_agent",
            "display_name": "News Agent",
            "role": "parent",
            "status": "receiving" if sector_agent.status in {"fetching", "processing"} else "online",
            "summary": f"{len(news_parent.inbox)} items routed to orb",
            "connected_to": "central_orb",
        },
        {
            "name": "sector_news_agent",
            "display_name": "Sector News Agent",
            "role": "agent",
            "status": sector_agent.status,
            "summary": sector_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "corporate_filings_agent",
            "display_name": "Corporate Filings Agent",
            "role": "agent",
            "status": filings_agent.status,
            "summary": filings_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "macro_policy_agent",
            "display_name": "Macro/Policy Agent",
            "role": "agent",
            "status": macro_agent.status,
            "summary": macro_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "sentiment_agent",
            "display_name": "Sentiment Agent",
            "role": "agent",
            "status": sentiment_agent.status,
            "summary": sentiment_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "historical_correlation_agent",
            "display_name": "Historical Correlation Agent",
            "role": "agent",
            "status": history_agent.status,
            "summary": history_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "after_hours_agent",
            "display_name": "After-Hours / Weekend Agent",
            "role": "agent",
            "status": after_hours_agent.status,
            "summary": after_hours_agent.current_action,
            "parent": "news_agent",
        },
        {
            "name": "earnings_surprise_agent",
            "display_name": "Earnings Surprise Agent",
            "role": "agent",
            "status": earnings_agent.status,
            "summary": earnings_agent.current_action,
            "parent": "news_agent",
        },
    ]


async def execute_cycle(sectors: list[str] | None = None) -> list[dict[str, Any]]:
    async with lock_for("sector_news_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, lambda: sector_agent.run(sectors))
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(1.2)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "sector_news_agent", "status": sector_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


class RunBody(BaseModel):
    sectors: list[str] | None = None


class ChatBody(BaseModel):
    message: str


@app.get("/api/news-agent/core")
def get_core() -> dict[str, Any]:
    if not news_parent.analysis:
        news_parent.analyze()
    return {
        "status": news_parent.status,
        "current_action": news_parent.current_action,
        "inbox_count": len(news_parent.inbox),
        "analysis": news_parent.analysis,
        "performance": perf_agent.snapshot(),
    }


@app.post("/api/news-agent/core/analyze")
def run_core_analyze() -> dict[str, Any]:
    analysis = news_parent.analyze()
    return {"ok": True, "analysis": analysis, "action": news_parent.current_action}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": utc_now()}


@app.get("/api/orb")
def get_orb() -> dict[str, Any]:
    snap = orb.snapshot()
    snap["agents"] = agent_graph()
    snap["active_count"] = sum(1 for a in snap["agents"] if a["status"] not in {"idle", "offline"})
    return snap


@app.get("/api/news-agent")
def get_news_agent() -> dict[str, Any]:
    cfg = load_json(NEWS_ROOT / "news_agent.config.json")
    return {
        **cfg,
        "status": "receiving" if sector_agent.status in {"fetching", "processing"} else "online",
        "connected_to": "central_orb",
        "inbox_count": len(news_parent.inbox),
        "agents": discover_child_agents(),
        "sub_agents": discover_child_agents(),
        "latest": _mixed_latest(),
        "core": news_parent.analysis,
        "core_action": news_parent.current_action,
    }


@app.get("/api/news-agent/agents")
@app.get("/api/news-agent/sub-agents")
def list_child_agents() -> dict[str, Any]:
    kids = discover_child_agents()
    return {"parent": "news_agent", "agents": kids, "sub_agents": kids}


@app.get("/api/news-agent/agents/{agent_name}")
@app.get("/api/news-agent/sub-agents/{agent_name}")
def get_child_agent(agent_name: str) -> dict[str, Any]:
    folder = NEWS_ROOT / agent_name
    cfg_path = folder / f"{agent_name}.config.json"
    if not cfg_path.exists():
        raise HTTPException(404, "Agent folder not found")
    cfg = load_json(cfg_path)
    live = None
    if agent_name == "sector_news_agent":
        live = sector_agent
    elif agent_name == "corporate_filings_agent":
        live = filings_agent
    elif agent_name == "macro_policy_agent":
        live = macro_agent
    elif agent_name == "sentiment_agent":
        live = sentiment_agent
    elif agent_name == "historical_correlation_agent":
        live = history_agent
    elif agent_name == "news_agent_testing_performance":
        live = perf_agent
    elif agent_name == "after_hours_agent":
        live = after_hours_agent
    elif agent_name == "earnings_surprise_agent":
        live = earnings_agent
    if live is None:
        return {
            **cfg,
            "status": cfg.get("status", "idle"),
            "current_action": "Folder ready. Logic not wired yet.",
            "logs": [],
            "items": [],
            "counts": {},
        }
    counts = dict(getattr(live, "counts", {}) or {})
    payload = {
        **cfg,
        "status": live.status,
        "current_action": live.current_action,
        "logs": live.logs[-80:],
        "items": list(reversed(live.items[-200:])),
        "counts": counts,
        "steps": list(getattr(live, "steps", [])),
        "last_error": getattr(live, "last_error", None),
    }
    if live is perf_agent:
        payload["report"] = dict(getattr(perf_agent, "report", {}) or {})
        payload["days"] = list(getattr(perf_agent, "days", []) or [])
    return payload


def _mixed_latest(limit: int = 5) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in reversed(news_parent.inbox):
        sector = item.get("sector") or ""
        if sector in seen:
            continue
        seen.add(sector)
        out.append(item)
        if len(out) >= limit:
            break
    return out or news_parent.inbox[-limit:][::-1]


def _sector_counts() -> dict[str, int]:
    if getattr(sector_agent, "counts", None):
        return dict(sector_agent.counts)
    counts: dict[str, int] = {}
    for item in sector_agent.items:
        counts[item["sector"]] = counts.get(item["sector"], 0) + 1
    return counts


@app.post("/api/news-agent/agents/sector_news_agent/run")
@app.post("/api/news-agent/sub-agents/sector_news_agent/run")
async def run_sector_agent(body: RunBody | None = None) -> dict[str, Any]:
    global run_task
    if lock_for("sector_news_agent").locked():
        return {"ok": True, "status": sector_agent.status, "message": "Cycle already running"}
    sectors = body.sectors if body else None
    run_task = asyncio.create_task(execute_cycle(sectors))
    return {"ok": True, "status": "fetching", "message": "Sector News Agent started"}


async def execute_filings() -> list[dict[str, Any]]:
    async with lock_for("corporate_filings_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, filings_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "corporate_filings_agent", "status": filings_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/corporate_filings_agent/run")
@app.post("/api/news-agent/sub-agents/corporate_filings_agent/run")
async def run_filings_agent() -> dict[str, Any]:
    global run_task
    if lock_for("corporate_filings_agent").locked():
        return {"ok": True, "status": filings_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_filings())
    return {"ok": True, "status": "fetching", "message": "Corporate Filings Agent started"}


async def execute_macro() -> list[dict[str, Any]]:
    async with lock_for("macro_policy_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, macro_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "macro_policy_agent", "status": macro_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/macro_policy_agent/run")
@app.post("/api/news-agent/sub-agents/macro_policy_agent/run")
async def run_macro_agent() -> dict[str, Any]:
    global run_task
    if lock_for("macro_policy_agent").locked():
        return {"ok": True, "status": macro_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_macro())
    return {"ok": True, "status": "fetching", "message": "Macro Policy Agent started"}


async def execute_sentiment() -> list[dict[str, Any]]:
    async with lock_for("sentiment_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, sentiment_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "sentiment_agent", "status": sentiment_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/sentiment_agent/run")
@app.post("/api/news-agent/sub-agents/sentiment_agent/run")
async def run_sentiment_agent() -> dict[str, Any]:
    global run_task
    if lock_for("sentiment_agent").locked():
        return {"ok": True, "status": sentiment_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_sentiment())
    return {"ok": True, "status": "fetching", "message": "Sentiment Agent started"}


async def execute_history() -> list[dict[str, Any]]:
    async with lock_for("historical_correlation_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, history_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "historical_correlation_agent", "status": history_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/historical_correlation_agent/run")
@app.post("/api/news-agent/sub-agents/historical_correlation_agent/run")
async def run_history_agent() -> dict[str, Any]:
    global run_task
    if lock_for("historical_correlation_agent").locked():
        return {"ok": True, "status": history_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_history())
    return {"ok": True, "status": "fetching", "message": "Historical Correlation Agent started"}


async def execute_perf() -> list[dict[str, Any]]:
    async with perf_lock:
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, perf_agent.run)
        bus.emit("performance_update", perf_agent.snapshot())
        bus.emit("agent_status", {"agent": "news_agent_testing_performance", "status": perf_agent.status})
        return items


@app.get("/api/news-agent/performance")
def get_performance() -> dict[str, Any]:
    return perf_agent.snapshot()


@app.post("/api/news-agent/agents/news_agent_testing_performance/run")
@app.post("/api/news-agent/sub-agents/news_agent_testing_performance/run")
async def run_perf_agent() -> dict[str, Any]:
    if perf_lock.locked():
        return {"ok": True, "status": perf_agent.status, "message": "Walk-forward already running"}
    asyncio.create_task(execute_perf())
    return {"ok": True, "status": "fetching", "message": "News Agent Testing Performance started"}


async def execute_after_hours() -> list[dict[str, Any]]:
    async with lock_for("after_hours_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, after_hours_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "after_hours_agent", "status": after_hours_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/after_hours_agent/run")
@app.post("/api/news-agent/sub-agents/after_hours_agent/run")
async def run_after_hours_agent() -> dict[str, Any]:
    global run_task
    if lock_for("after_hours_agent").locked():
        return {"ok": True, "status": after_hours_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_after_hours())
    return {"ok": True, "status": "fetching", "message": "After-Hours Agent started"}


async def execute_earnings() -> list[dict[str, Any]]:
    async with lock_for("earnings_surprise_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, earnings_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.8)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "earnings_surprise_agent", "status": earnings_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/news-agent/agents/earnings_surprise_agent/run")
@app.post("/api/news-agent/sub-agents/earnings_surprise_agent/run")
async def run_earnings_agent() -> dict[str, Any]:
    global run_task
    if lock_for("earnings_surprise_agent").locked():
        return {"ok": True, "status": earnings_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_earnings())
    return {"ok": True, "status": "fetching", "message": "Earnings Surprise Agent started"}


@app.get("/api/social-agent")
def get_social_agent() -> dict[str, Any]:
    cfg = load_json(SOCIAL_ROOT / "social_agent.config.json")
    return {
        **cfg,
        "status": "online",
        "inbox_count": len(social_parent.inbox),
        "current_action": social_parent.current_action,
        "latest": list(reversed(social_parent.inbox[-8:])),
        "agents": [
            {
                "name": "reddit_flow_agent",
                "display_name": "Reddit Flow Agent",
                "status": reddit_agent.status,
                "item_count": len(reddit_agent.items),
                "current_action": reddit_agent.current_action,
            },
            {
                "name": "twitter_buzz_agent",
                "display_name": "Twitter Buzz Agent",
                "status": "idle",
                "item_count": 0,
                "current_action": "Folder ready. No fake tweets.",
            },
        ],
    }


@app.get("/api/social-agent/agents/reddit_flow_agent")
def get_reddit_agent() -> dict[str, Any]:
    cfg = load_json(REDDIT_ROOT / "reddit_flow_agent.config.json")
    return {
        **cfg,
        "status": reddit_agent.status,
        "current_action": reddit_agent.current_action,
        "logs": reddit_agent.logs[-80:],
        "items": list(reversed(reddit_agent.items[-200:])),
        "counts": dict(reddit_agent.counts),
        "steps": list(reddit_agent.steps),
        "last_error": reddit_agent.last_error,
    }


async def execute_reddit() -> list[dict[str, Any]]:
    async with lock_for("reddit_flow_agent"):
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(None, reddit_agent.run)
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)
        await asyncio.sleep(0.4)
        orb.receiving = False
        bus.emit("agent_status", {"agent": "reddit_flow_agent", "status": reddit_agent.status})
        bus.emit("orb_idle", {"receiving": False})
        return items


@app.post("/api/social-agent/agents/reddit_flow_agent/run")
async def run_reddit_agent() -> dict[str, Any]:
    global run_task
    if lock_for("reddit_flow_agent").locked():
        return {"ok": True, "status": reddit_agent.status, "message": "A cycle is already running"}
    run_task = asyncio.create_task(execute_reddit())
    return {"ok": True, "status": "fetching", "message": "Reddit Flow Agent started"}


@app.get("/api/music-agent")
def get_music_agent() -> dict[str, Any]:
    cfg = load_json(MUSIC_ROOT / "music_agent.config.json")
    return {**cfg, **music_agent.snapshot()}


@app.get("/api/music-agent/search")
async def search_music_agent(q: str, limit: int = 8) -> dict[str, Any]:
    term = (q or "").strip()
    if not term:
        raise HTTPException(400, "Empty search")
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: music_agent.search(term, limit))


@app.get("/api/news")
def list_news(sector: str | None = None, limit: int = 24) -> dict[str, Any]:
    items = list(reversed(sector_agent.items))
    if sector and sector.lower() != "all":
        key = "IT" if sector.lower() == "it" else sector.lower()
        items = [i for i in items if i["sector"].lower() == key.lower()]
    return {"items": items[:limit], "counts": _sector_counts()}


@app.get("/api/stream")
async def stream() -> StreamingResponse:
    q = bus.subscribe()

    async def gen():
        try:
            def _snap(agent):
                return {
                    "status": agent.status,
                    "current_action": agent.current_action,
                    "logs": agent.logs[-40:],
                    "items": list(reversed(agent.items[-40:])),
                    "steps": list(getattr(agent, "steps", [])),
                    "counts": dict(getattr(agent, "counts", {}) or {}),
                }

            snapshot = {
                "event": "snapshot",
                "payload": {
                    "orb": orb.snapshot(),
                    "news_agent": get_news_agent(),
                    "sector": _snap(sector_agent),
                    "filings": _snap(filings_agent),
                    "macro": _snap(macro_agent),
                    "sentiment": _snap(sentiment_agent),
                    "history": _snap(history_agent),
                    "after_hours": _snap(after_hours_agent),
                    "earnings": _snap(earnings_agent),
                    "reddit": _snap(reddit_agent),
                    "performance": perf_agent.snapshot(),
                    "agents": agent_graph(),
                },
                "timestamp": utc_now(),
            }
            yield f"data: {json.dumps(snapshot, ensure_ascii=False)}\n\n"
            while True:
                try:
                    packet = await asyncio.wait_for(q.get(), timeout=15)
                    yield f"data: {json.dumps(packet, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'event': 'ping', 'timestamp': utc_now()})}\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


HINGLISH = re.compile(
    r"(kya|hai|mein|me |kaun|bata|update|sector|news|aaj|latest|samachar|khabar)",
    re.I,
)
DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def _match_score(query: str, item: dict[str, Any]) -> int:
    q = query.lower()
    blob = f"{item.get('sector','')} {item.get('headline','')} {item.get('summary','')}".lower()
    score = 0
    for token in re.findall(r"[a-zA-Z\u0900-\u097F]{3,}", q):
        if token in blob:
            score += 2
    sector_aliases = {
        "sugar": ["sugar", "chini", "ethanol"],
        "it": ["it", "tech", "infosys", "tcs", "wipro", "software"],
        "pharma": ["pharma", "dawai", "drug", "fda"],
        "banking": ["bank", "banking", "rbi", "hdfc", "icici"],
        "auto": ["auto", "car", "ev", "maruti", "vehicle"],
    }
    for sector, words in sector_aliases.items():
        if any(w in q for w in words) and item.get("sector", "").lower() == sector:
            score += 5
    return score


@app.post("/api/chat")
def chat(body: ChatBody) -> dict[str, Any]:
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(400, "Empty message")

    hindi = bool(DEVANAGARI.search(message) or HINGLISH.search(message))
    wanted_sector = None
    qlow = message.lower()
    for sector, words in {
        "sugar": ["sugar", "chini", "ethanol"],
        "IT": ["it sector", "infosys", "tcs", "wipro", "software"],
        "pharma": ["pharma", "dawai", "drug", "fda"],
        "banking": ["bank", "banking", "rbi", "hdfc", "icici"],
        "auto": ["auto", "car", "ev", "maruti", "vehicle"],
    }.items():
        if any(w in qlow for w in words):
            wanted_sector = sector
            break

    pool = sector_agent.items
    if wanted_sector:
        pool = [i for i in sector_agent.items if i.get("sector") == wanted_sector] or pool

    scored = sorted(
        ((_match_score(message, item), item) for item in pool),
        key=lambda x: x[0],
        reverse=True,
    )
    hits = [item for score, item in scored if score > 0]
    hits = sorted(hits, key=lambda i: len(i.get("headline") or ""), reverse=True)[:4]
    if not hits:
        hits = sorted(pool, key=lambda i: len(i.get("headline") or ""), reverse=True)[:4]

    if not sector_agent.items:
        reply = (
            "Abhi Sector News Agent ke paas koi collected news nahi hai. "
            "Pehle agent ko run karo, phir poocho."
            if hindi
            else "The Sector News Agent has no collected items yet. Run a fetch cycle, then ask again."
        )
    elif hits:
        lines = []
        for item in hits[:4]:
            lines.append(f"• [{item['sector']}] {item['headline']}")
        if hindi:
            reply = (
                "News Agent + Sector News Agent ke latest context se:\n"
                + "\n".join(lines)
                + "\n\nYe headlines central orb ko forward ho chuki hain."
            )
        else:
            reply = (
                "From News Agent context (via Sector News Agent):\n"
                + "\n".join(lines)
                + "\n\nThese items have already been forwarded to the central orb."
            )
    else:
        reply = "No matching sector headlines yet."

    return {
        "id": str(uuid4()),
        "role": "assistant",
        "text": reply,
        "sources": [
            {
                "headline": h["headline"],
                "sector": h["sector"],
                "source_url": h.get("source_url"),
                "timestamp": h.get("timestamp"),
            }
            for h in hits[:4]
        ],
        "timestamp": utc_now(),
        "used_agents": ["news_agent", "sector_news_agent"],
    }


def seed_core_from_disk() -> None:
    """Reload last satellite packets so CORE does not show 'no feed yet' after restart."""
    seen = {item.get("id") for item in news_parent.inbox}
    for folder in (SECTOR_ROOT, FILINGS_ROOT, MACRO_ROOT, SENT_ROOT, HIST_ROOT, AFTER_ROOT, EARN_ROOT):
        pack = load_json(folder / "data" / "last_run.json")
        for item in pack.get("items") or []:
            iid = item.get("id")
            if not iid or iid in seen:
                continue
            seen.add(iid)
            news_parent.receive_from_sub_agent(item)
    if news_parent.inbox:
        news_parent.analyze()
        bus.emit("core_update", news_parent.analysis)


DIST = ROOT / "frontend" / "dist"


@app.get("/")
def spa_index():
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"ok": True, "service": "agent-hud-api"}


@app.get("/{full_path:path}")
def spa_assets(full_path: str):
    if full_path.startswith("api/") or full_path == "api":
        raise HTTPException(404, "Not Found")
    candidate = (DIST / full_path).resolve()
    try:
        candidate.relative_to(DIST.resolve())
    except ValueError:
        raise HTTPException(404, "Not Found")
    if candidate.is_file():
        return FileResponse(candidate)
    index = DIST / "index.html"
    if index.exists():
        return FileResponse(index)
    raise HTTPException(404, "Not Found")


@app.on_event("startup")
async def warmup() -> None:
    seed_core_from_disk()
    asyncio.create_task(execute_cycle())
