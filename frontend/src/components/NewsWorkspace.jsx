import { useEffect, useMemo, useRef, useState } from "react";
import {
  runAfterHoursAgent,
  runCoreAnalyze,
  runEarningsAgent,
  runFilingsAgent,
  runHistoryAgent,
  runMacroAgent,
  runPerformanceAgent,
  runSectorAgent,
  runSentimentAgent,
} from "../api";

const STATUS_LABEL = {
  idle: "Idle",
  fetching: "Fetching",
  processing: "Processing",
  receiving: "Receiving",
  online: "Online",
  done: "Done",
  error: "Error",
};

const RING = [
  {
    name: "sector_news_agent",
    display_name: "Sector News Agent",
    short: "SECTOR",
    feed: "SECTOR FEED IN",
    angle: -90,
    color: "#4af0ff",
    job: "Sector-wise financial headlines — 11 sectors, 100+ tracked names.",
    steps: [
      "Search Google News per sector",
      "Pull Economic Times, Moneycontrol and NSE announcement feeds",
      "Classify each live headline, drop unmatched rows",
      "Forward structured JSON to the News Agent core",
    ],
  },
  {
    name: "corporate_filings_agent",
    display_name: "Corporate Filings Agent",
    short: "FILINGS",
    feed: "FILINGS FEED IN",
    angle: -38.6,
    color: "#ff6b6b",
    job: "NSE/BSE announcements, results, insider trades.",
    steps: ["Watch exchange announcement boards", "Tag results / insider / board notes", "Forward filings pack to News Agent"],
  },
  {
    name: "macro_policy_agent",
    display_name: "Macro / Policy Agent",
    short: "MACRO",
    feed: "POLICY FEED IN",
    angle: 12.9,
    color: "#ffd166",
    job: "RBI, government policy, budget, global events.",
    steps: ["Scan RBI / MoF / global macro wires", "Score policy impact on sectors", "Push brief to News Agent"],
  },
  {
    name: "after_hours_agent",
    display_name: "After-Hours / Weekend Agent",
    short: "AFTER HRS",
    feed: "UNPRICED FEED IN",
    angle: 64.3,
    color: "#c084fc",
    job: "Sirf unpriced tape — NSE close ke baad, weekend, ya Monday open se pehle. Session news drop.",
    steps: [
      "ET / Moneycontrol / Google News se live RSS lao",
      "pubDate IST parse — no date = drop",
      "09:15–15:30 weekday session drop. Weekend / after 15:30 / before 09:15 rakho (72h)",
      "Sirf tracked company-named headlines CORE ko bhejo (unpriced ×2)",
    ],
  },
  {
    name: "historical_correlation_agent",
    display_name: "Historical Correlation Agent",
    short: "HISTORY",
    feed: "HISTORY FEED IN",
    angle: 115.7,
    color: "#ff9f43",
    job: "Aaj ke named stocks pe dekho — last baar similar UP/DOWN news ke baad 5 din mein price kya hua.",
    steps: [
      "Aaj ke live headlines se companies chuno",
      "Moneycontrol se 6-month NSE daily bars lao",
      "Similar UP/DOWN headlines ke baad 5-day move naapo",
      "supports_up / supports_down / mixed tag laga ke CORE-01 ko bhejo",
    ],
  },
  {
    name: "sentiment_agent",
    display_name: "Sentiment Agent",
    short: "SENTIMENT",
    feed: "SENTIMENT FEED IN",
    angle: 167.1,
    color: "#3dffa8",
    job: "Score each headline positive / negative / neutral.",
    steps: ["Read incoming News Agent items", "Classify tone of headline + summary", "Attach sentiment tag and return"],
  },
  {
    name: "earnings_surprise_agent",
    display_name: "Earnings Surprise Agent",
    short: "EARNINGS",
    feed: "RESULTS FEED IN",
    angle: 218.6,
    color: "#60a5fa",
    job: "Live results headlines — beat / miss / inline. EPS number tabhi jab text mein likha ho.",
    steps: [
      "Google News + ET + Moneycontrol se results wires lao",
      "Sirf un headlines ko rakho jisme result/earnings language ho",
      "Beat / miss / inline tabhi tag jab headline khud bole — guess nahi",
      "Named company ke saath CORE-01 ko bhejo (beat +4 / miss −4)",
    ],
  },
];

function StatusDot({ status }) {
  return <i className={`st-dot st-${status || "idle"}`} />;
}

function fmtPct(v) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  return `${n > 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export default function NewsWorkspace({
  view,
  setView,
  onClose,
  newsAgent,
  sector,
  filings,
  macro,
  sentiment,
  history,
  performance,
  afterHours,
  earnings,
  core,
}) {
  const [filter, setFilter] = useState("all");

  const kickedAll = useRef(false);
  useEffect(() => {
    if (view !== "news-agent") return;
    if (kickedAll.current) return;
    kickedAll.current = true;
    runSectorAgent().catch(() => {});
    runFilingsAgent().catch(() => {});
    runMacroAgent().catch(() => {});
    runSentimentAgent().catch(() => {});
    runHistoryAgent().catch(() => {});
    runAfterHoursAgent().catch(() => {});
    runEarningsAgent().catch(() => {});
  }, [view]);

  const liveMap = useMemo(() => {
    const map = {};
    for (const a of newsAgent.agents || newsAgent.sub_agents || []) {
      map[a.name] = a;
    }
    return map;
  }, [newsAgent]);

  const nodes = RING.map((n) => ({ ...n, ...(liveMap[n.name] || {}) }));
  const open = RING.find((n) => view === n.name);
  const livePack =
    view === "corporate_filings_agent"
      ? filings
      : view === "macro_policy_agent"
        ? macro
        : view === "sentiment_agent"
          ? sentiment
          : view === "historical_correlation_agent"
            ? history
            : view === "after_hours_agent"
              ? afterHours
              : view === "earnings_surprise_agent"
                ? earnings
                : sector;
  const items = useMemo(() => {
    const list = livePack?.items || [];
    if (filter === "all") return list;
    return list.filter((i) =>
      [i.sector, i.filing_type, i.alignment, i.sentiment, i.window].some(
        (k) => String(k || "").toLowerCase() === filter.toLowerCase()
      )
    );
  }, [livePack, filter]);

  async function onRun() {
    try {
      if (view === "corporate_filings_agent") await runFilingsAgent();
      else if (view === "macro_policy_agent") await runMacroAgent();
      else if (view === "sentiment_agent") await runSentimentAgent();
      else if (view === "historical_correlation_agent") await runHistoryAgent();
      else if (view === "after_hours_agent") await runAfterHoursAgent();
      else if (view === "earnings_surprise_agent") await runEarningsAgent();
      else await runSectorAgent();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="workspace constellation">
      <div className="ws-top">
        <div className="ws-crumbs">
          <button onClick={() => setView("news-agent")}>NEWS AGENT</button>
          {open && (
            <>
              <span>/</span>
              <b>{open.display_name.toUpperCase()}</b>
            </>
          )}
          {view === "core" && (
            <>
              <span>/</span>
              <b>CORE-01 ANALYSIS</b>
            </>
          )}
        </div>
        <button className="ws-close" onClick={onClose}>
          CLOSE
        </button>
      </div>

      {view === "core" ? (
        <CorePage core={core} performance={performance} onBack={() => setView("news-agent")} />
      ) : open ? (
        <AgentPage
          meta={open}
          live={liveMap[open.name]}
          sector={livePack || sector}
          filter={filter}
          setFilter={setFilter}
          items={items}
          onRun={onRun}
          onBack={() => setView("news-agent")}
        />
      ) : (
        <RingView nodes={nodes} onOpen={(name) => setView(name)} onCore={() => setView("core")} newsAgent={newsAgent} />
      )}
    </div>
  );
}

function RingView({ nodes, onOpen, onCore, newsAgent }) {
  const cx = 50;
  const cy = 50;
  const r = 36;

  return (
    <div className="ring-stage">
      <svg className="ring-svg" viewBox="0 0 100 100" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id="coreglow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffe9a8" stopOpacity="0.9" />
            <stop offset="45%" stopColor="#ffbf3c" stopOpacity="0.35" />
            <stop offset="100%" stopColor="#ffbf3c" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx={cx} cy={cy} r="22" fill="url(#coreglow)" />
        {nodes.map((n, i) => {
          const rad = (n.angle * Math.PI) / 180;
          const x = cx + r * Math.cos(rad);
          const y = cy + r * Math.sin(rad);
          return (
            <g key={n.name}>
              <line
                x1={x}
                y1={y}
                x2={cx}
                y2={cy}
                className="feed-line"
                stroke={n.color}
                style={{ animationDelay: `${i * 0.18}s` }}
              />
            </g>
          );
        })}
      </svg>

      <button className="core-wrap" onClick={onCore} title="Open CORE-01 analysis">
        <div className="core-spin" />
        <div className="core-spin rev" />
        <div className="core-ball">
          <span className="core-kicker">CORE-01</span>
          <b>NEWS</b>
          <small>CLICK · ANALYZE SATELLITE DATA</small>
        </div>
      </button>

      {nodes.map((n) => {
        const rad = (n.angle * Math.PI) / 180;
        const left = 50 + r * Math.cos(rad);
        const top = 50 + r * Math.sin(rad);
        return (
          <button
            key={n.name}
            className="sat-node"
            style={{
              left: `${left}%`,
              top: `${top}%`,
              "--sat": n.color,
            }}
            onClick={() => onOpen(n.name)}
          >
            <span className="sat-ring" />
            <span className="sat-label">{n.short}</span>
            <span className="sat-feed">{n.feed}</span>
            <span className={`sat-st st-${n.status || "idle"}`}>{STATUS_LABEL[n.status] || "Idle"}</span>
          </button>
        );
      })}

      <p className="ring-hint">
        {newsAgent.status === "receiving" ? "Nodes pushing packets into News Agent" : "Click a node to open its page"}
      </p>
    </div>
  );
}

function AgentPage({ meta, live, sector, filter, setFilter, items, onRun, onBack }) {
  const isLive = RING.some((n) => n.name === meta.name);
  const isFilings = meta.name === "corporate_filings_agent";
  const isMacro = meta.name === "macro_policy_agent";
  const isSent = meta.name === "sentiment_agent";
  const isHist = meta.name === "historical_correlation_agent";
  const isAfter = meta.name === "after_hours_agent";
  const isEarn = meta.name === "earnings_surprise_agent";
  const status = isLive ? sector.status : live?.status || "idle";
  const action = isLive
    ? sector.current_action
    : "No live pipeline yet. Folder is ready — analysis will appear here once this agent is wired.";
  const chips = isFilings
    ? ["all", "financial_results", "insider_trade", "board_meeting", "dividend", "merger_acquisition", "other_disclosure"]
    : isMacro
      ? ["all", "monetary", "fiscal", "trade", "energy", "global", "regulation"]
      : isSent
        ? ["all", "positive", "negative", "neutral"]
        : isHist
          ? ["all", "supports_up", "supports_down", "mixed"]
          : isAfter
            ? ["all", "weekend", "after_close", "pre_open"]
            : isEarn
              ? ["all", "beat", "miss", "inline", "results_only"]
              : ["all", "sugar", "IT", "pharma", "banking", "auto", "energy", "metals", "fmcg", "telecom", "finance", "infra"];

  const kicked = useRef("");
  useEffect(() => {
    if (!isLive) return;
    if (["fetching", "processing"].includes(sector.status)) return;
    if (kicked.current === meta.name) return;
    kicked.current = meta.name;
    onRun();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLive, meta.name]);

  return (
    <section className="agent-page glass">
      <header className="ws-head">
        <div>
          <p className="kicker" style={{ color: meta.color }}>
            NEWS AGENT · {meta.name}
          </p>
          <h3>{meta.display_name}</h3>
        </div>
        <div className="head-actions">
          <span className={`pill pill-${status}`}>
            <StatusDot status={status} />
            {STATUS_LABEL[status] || "Idle"}
          </span>
          {isLive && (
            <button className="run-btn" onClick={onRun} disabled={["fetching", "processing"].includes(status)}>
              RUN CYCLE
            </button>
          )}
          <button className="run-btn" onClick={onBack}>
            BACK TO RING
          </button>
        </div>
      </header>

      <p className="ws-copy">{meta.job}</p>
      <div className="live-line">
        <span className="pulse-dot" />
        {action}
      </div>

      <div className="howto">
        <p className="kicker">HOW THIS AGENT WORKS</p>
        <ol>
          {(meta.steps || []).map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </div>

      {isLive ? (
        <div className="detail-split">
          <div className="log-pane">
            <p className="kicker">ACTIVITY LOG</p>
            <ul className="log-list">
              {(sector.logs || [])
                .slice()
                .reverse()
                .map((l, i) => (
                  <li key={`${l.timestamp}-${i}`}>
                    <time>{formatStamp(l.timestamp)}</time>
                    <span className={l.level}>{l.message}</span>
                  </li>
                ))}
              {(sector.logs || []).length === 0 && <li className="empty">No activity yet.</li>}
            </ul>
          </div>
          <div className="news-pane">
            <div className="filter-row">
              {chips.map((s) => (
                <button key={s} className={filter === s ? "on" : ""} onClick={() => setFilter(s)}>
                  {s.replaceAll("_", " ")}
                  {s !== "all" && sector.counts?.[s] ? ` ${sector.counts[s]}` : ""}
                </button>
              ))}
            </div>
            <ul className="item-list">
              {items.map((n) => (
                <li key={n.id}>
                  <div className="item-top">
                    <em className={isHist ? `align-${n.alignment || "mixed"}` : ""}>
                      {isEarn
                        ? (n.surprise || n.sector || "").replaceAll("_", " ")
                        : isAfter
                          ? (n.window || n.sector || "").replaceAll("_", " ")
                          : isHist
                            ? (n.alignment || n.sector || "").replaceAll("_", " ")
                            : n.sector}
                    </em>
                    <span className={`mini ${n.status}`}>{n.source || n.status}</span>
                  </div>
                  {n.source_url ? (
                    <a href={n.source_url} target="_blank" rel="noreferrer">
                      {n.headline}
                    </a>
                  ) : (
                    <b>{n.headline}</b>
                  )}
                  {n.summary && n.summary !== n.headline && <p>{n.summary}</p>}
                  {isAfter && n.companies && <p>{(n.companies || []).join(", ")}</p>}
                  {isHist && (
                    <div className="hist-metrics">
                      {n.last != null && <span>last {n.last}</span>}
                      {n.ret_1d != null && <span>1d {fmtPct(n.ret_1d)}</span>}
                      {n.ret_5d != null && <span>5d {fmtPct(n.ret_5d)}</span>}
                      {n.ret_20d != null && <span>20d {fmtPct(n.ret_20d)}</span>}
                    </div>
                  )}
                </li>
              ))}
              {items.length === 0 && <li className="empty">No collected items yet.</li>}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-board">
          <p>This agent has no live source yet.</p>
        </div>
      )}
    </section>
  );
}

function PerfBadge({ perf, onRun }) {
  const report = perf?.report || {};
  const running = ["fetching", "processing"].includes(perf?.status);
  const rate = report.hit_rate;
  return (
    <button
      className={`perf-badge ${rate == null ? "is-empty" : rate >= 55 ? "is-ok" : "is-mid"}`}
      onClick={onRun}
      disabled={running}
      title={report.protocol || "Walk-forward hit-rate. Click to re-run."}
    >
      <span className="perf-kicker">WALK-FORWARD TOP-2</span>
      <strong>{running ? "…" : rate != null ? `${rate}%` : "—"}</strong>
      <em>
        {running
          ? perf.current_action || "testing…"
          : report.decided
            ? `${report.hits}/${report.decided} hit · ${report.days || 0} days`
            : "click to test"}
      </em>
      {!running && rate != null && (
        <span className="perf-split">
          this window TOP-2 {rate}% · top5 {report.top5?.hit_rate ?? "—"}%
          {report.holdout?.top2?.hit_rate != null ? ` · holdout TOP-2 ${report.holdout.top2.hit_rate}%` : ""}
        </span>
      )}
    </button>
  );
}

function CorePage({ core, performance, onBack }) {
  const [busy, setBusy] = useState(false);
  const a = core?.analysis || {};
  const nsUp = (a.next_session_up || []).slice(0, 5);
  const nsDown = (a.next_session_down || []).slice(0, 5);
  const flowUp = (a.news_flow_up || a.companies_up || []).slice(0, 8);
  const flowDown = (a.news_flow_down || a.companies_down || []).slice(0, 8);
  const sectors = a.sectors || [];
  const contrib = a.contributions || {};
  const steps = a.steps || [];
  const evidence = a.evidence || [];
  const afterHours = a.after_hours || [];
  const perf = performance || core?.performance || {};
  const report = perf.report || {};
  const days = perf.days || [];
  const agentRows = [
    ["sector_news_agent", "SECTOR"],
    ["corporate_filings_agent", "FILINGS"],
    ["macro_policy_agent", "MACRO"],
    ["after_hours_agent", "AFTER HRS"],
    ["earnings_surprise_agent", "EARNINGS"],
    ["sentiment_agent", "SENTIMENT"],
    ["historical_correlation_agent", "HISTORY"],
  ];

  useEffect(() => {
    if (["fetching", "processing"].includes(perf.status)) return;
    if (report.hit_rate != null || (days || []).length > 0) return;
    runPerformanceAgent().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perf.status]);

  async function refresh() {
    setBusy(true);
    try {
      await runCoreAnalyze();
    } catch (err) {
      console.error(err);
    } finally {
      setBusy(false);
    }
  }

  async function rerunPerf() {
    try {
      await runPerformanceAgent();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <section className="agent-page glass">
      <header className="ws-head">
        <div>
          <p className="kicker" style={{ color: "#ffc44a" }}>
            CORE-01 · NEWS FLOW ANALYZER
          </p>
          <h3>Two boards · news vs next session</h3>
        </div>
        <div className="head-actions">
          <PerfBadge perf={perf} onRun={rerunPerf} />
          <button className="run-btn" onClick={refresh} disabled={busy}>
            {busy ? "SCORING…" : "RE-ANALYZE"}
          </button>
          <button className="run-btn" onClick={onBack}>
            BACK TO RING
          </button>
        </div>
      </header>

      <div className="core-stack">
      <section className="core-card">
        <p className="kicker">NEXT SESSION · UNPRICED LEAN</p>
        <div className="core-cols">
        <div>
          <p className="kicker">UP</p>
          <ul className="co-list">
            {nsUp.map((c, i) => (
              <li key={`ns-up-${c.name}`}>
                <div className="co-top">
                  <b>
                    #{i + 1} {c.name}
                  </b>
                  <em className="up-tilt">{c.chance_up ?? "—"}%</em>
                </div>
                <div className="chance-bar">
                  <span className="up-fill" style={{ width: `${c.chance_up || 0}%` }} />
                </div>
                <span>
                  {c.sector} · unpriced lean
                  {c.after_hours ? ` · ${c.after_hours}` : ""}
                  {c.earnings ? ` · ${c.earnings}` : ""}
                </span>
              </li>
            ))}
            {nsUp.length === 0 && <li className="empty">No unpriced up lean yet.</li>}
          </ul>
        </div>
        <div>
          <p className="kicker">DOWN</p>
          <ul className="co-list">
            {nsDown.map((c, i) => (
              <li key={`ns-down-${c.name}`}>
                <div className="co-top">
                  <b>
                    #{i + 1} {c.name}
                  </b>
                  <em className="down-tilt">{c.chance_down ?? "—"}%</em>
                </div>
                <div className="chance-bar">
                  <span className="down-fill" style={{ width: `${c.chance_down || 0}%` }} />
                </div>
                <span>
                  {c.sector} · unpriced lean
                  {c.after_hours ? ` · ${c.after_hours}` : ""}
                  {c.earnings ? ` · ${c.earnings}` : ""}
                </span>
              </li>
            ))}
            {nsDown.length === 0 && <li className="empty">No unpriced down lean yet.</li>}
          </ul>
        </div>
        </div>
      </section>

      <section className="core-card">
        <p className="kicker">NEWS FLOW · HEADLINES ONLY · NO TOMORROW %</p>
        <div className="core-cols">
        <div>
          <p className="kicker">IN HEADLINES</p>
          <ul className="co-list">
            {flowUp.map((c, i) => (
              <li key={`flow-up-${c.name}`}>
                <div className="co-top">
                  <b>
                    #{i + 1} {c.name}
                  </b>
                  <em className="up-tilt">{c.mentions} hits</em>
                </div>
                <span>{c.sector} · mentioned today · not a tomorrow %</span>
              </li>
            ))}
            {flowUp.length === 0 && <li className="empty">No named up-flow yet.</li>}
          </ul>
        </div>
        <div>
          <p className="kicker">DOWN LANGUAGE</p>
          <ul className="co-list">
            {flowDown.map((c, i) => (
              <li key={`flow-down-${c.name}`}>
                <div className="co-top">
                  <b>
                    #{i + 1} {c.name}
                  </b>
                  <em className="down-tilt">{c.mentions} hits</em>
                </div>
                <span>{c.sector} · mentioned today · not a tomorrow %</span>
              </li>
            ))}
            {flowDown.length === 0 && <li className="empty">No named down-flow yet.</li>}
          </ul>
        </div>
        </div>
      </section>
      </div>

      {afterHours.length > 0 && (
        <div className="perf-days">
          <p className="kicker">UNPRICED · AFTER 15:30 / WEEKEND / PRE-OPEN</p>
          <ul>
            {afterHours.map((c) => (
              <li key={c.name}>
                <b>{c.name}</b>
                <em className={c.tilt === "up" ? "up-tilt" : c.tilt === "down" ? "down-tilt" : ""}>{c.tilt}</em>
                <span>
                  {c.after_hours} headlines · {(c.headlines || [])[0] || ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {days.length > 0 && (
        <div className="perf-days">
          <p className="kicker">DAY-WISE TEST · NEWS D, PRICE D+1 · NO LEAKAGE</p>
          <ul>
            {days.map((d) => (
              <li key={d.news_date}>
                <b>
                  {d.news_date} → {d.check_date}
                </b>
                <em className={d.hit_rate >= 55 ? "up-tilt" : d.hit_rate == null ? "" : "down-tilt"}>
                  {d.hit_rate != null ? `${d.hit_rate}%` : "—"}
                </em>
                <span>
                  {d.hits}/{d.decided || 0} · UP {(d.up_names || []).slice(0, 3).join(", ") || "—"} · DOWN{" "}
                  {(d.down_names || []).slice(0, 3).join(", ") || "—"}
                </span>
              </li>
            ))}
          </ul>
          <p className="disclaimer">{report.protocol}</p>
        </div>
      )}

      <div className="howto method-box">
        <p className="kicker">HOW CORE DECIDED UP vs DOWN</p>
        <ol>
          <li>Do board: NEWS FLOW = kaunsi company aaj headlines mein (kal % nahi).</li>
          <li>NEXT SESSION = sirf after 15:30 / weekend / pre-open + headline-stated beat/miss.</li>
          <li>Session-hour “aaj rally/crash” next-session book mein nahi jaati — pehle se priced.</li>
          <li>Lean % unpriced-news strength hai, Monday close ka vaada nahi. Holdout pe top-2 ~52% tha.</li>
        </ol>
      </div>

      <p className="kicker">DATA FROM AGENTS</p>
      <div className="contrib">
        {agentRows.map(([key, label]) => (
          <div key={key} className={`contrib-chip ${contrib[key] ? "has" : ""}`}>
            <b>{label}</b>
            <span>{contrib[key] ? `${contrib[key]} packets` : "no feed yet"}</span>
          </div>
        ))}
      </div>
      <ul className="item-list agent-feed">
        {evidence.slice(0, 16).map((e, i) => (
          <li key={`${e.headline}-${i}`}>
            <div className="item-top">
              <em>{e.agent_name || "agent"}</em>
              <span className="mini">{e.sector}</span>
            </div>
            {e.source_url ? (
              <a href={e.source_url} target="_blank" rel="noreferrer">
                {e.headline}
              </a>
            ) : (
              <b>{e.headline}</b>
            )}
            <p>
              {(e.companies || []).join(", ")} · tone {e.tone > 0 ? `+${e.tone}` : e.tone}
            </p>
          </li>
        ))}
        {evidence.length === 0 && <li className="empty">Named-company packets abhi nahi aaye. Agents ko RUN CYCLE do.</li>}
      </ul>

      <div className="howto">
        <p className="kicker">WHAT CORE-01 DID</p>
        <ul className="pipe-list">
          {steps.map((s) => (
            <li key={s.key} className={`pipe-${s.status || "done"}`}>
              <b>{s.label}</b>
              <span>{s.detail}</span>
            </li>
          ))}
        </ul>
      </div>

      <p className="kicker">SECTOR TILT</p>
      <ul className="co-list">
        {sectors.map((s) => (
          <li key={s.sector}>
            <div className="co-top">
              <b>{s.sector}</b>
              <em className={s.tilt === "up" ? "up-tilt" : s.tilt === "down" ? "down-tilt" : ""}>
                {s.tilt} {s.score}
              </em>
            </div>
            <span>
              {s.mentions} items · {s.up} up-language · {s.down} down-language
            </span>
          </li>
        ))}
      </ul>
      <p className="disclaimer">{a.disclaimer}</p>
    </section>
  );
}

function formatStamp(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return iso;
  }
}
