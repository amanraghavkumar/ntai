import { useEffect, useMemo, useState } from "react";
import NewsWorkspace from "./components/NewsWorkspace.jsx";
import SocialWorkspace from "./components/SocialWorkspace.jsx";
import MusicDeck from "./components/MusicDeck.jsx";
import { getCore, getNewsAgent, getOrb, getPerformance, getRedditAgent, getSubAgent, openStream } from "./api";
import { setMusicLayout } from "./musicEngine";

function Icon({ name, size = 14 }) {
  const s = { width: size, height: size };
  switch (name) {
    case "wifi":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <path d="M5 12.5a9 9 0 0 1 14 0" />
          <path d="M8.5 15.5a5 5 0 0 1 7 0" />
          <circle cx="12" cy="18.5" r="1.2" fill="currentColor" stroke="none" />
        </svg>
      );
    case "battery":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <rect x="3" y="8" width="15" height="8" rx="1.5" />
          <path d="M20 11v2" />
          <rect x="5" y="10" width="9" height="4" fill="currentColor" stroke="none" />
        </svg>
      );
    case "plane":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <path d="M21 12 3 4l2.6 7.2L15 12l-9.4.8L3 20l18-8Z" />
        </svg>
      );
    case "users":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <circle cx="9" cy="8" r="3" />
          <path d="M3.5 19a5.5 5.5 0 0 1 11 0" />
          <circle cx="17" cy="9" r="2.4" />
          <path d="M16 19a4.6 4.6 0 0 0 4.8-4.2" />
        </svg>
      );
    case "mail":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <rect x="3" y="6" width="18" height="12" rx="2" />
          <path d="m4 8 8 6 8-6" />
        </svg>
      );
    case "heart":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <path d="M12 20s-7-4.4-9.2-8.2C1 8.6 2.6 5.5 6 5.2c2-.2 3.5.9 4.2 2 0.7-1.1 2.2-2.2 4.2-2 3.4.3 5 3.4 3.2 6.6C19 15.6 12 20 12 20Z" />
        </svg>
      );
    case "doc":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <path d="M7 3h7l5 5v13H7z" />
          <path d="M14 3v5h5M9 13h6M9 17h6" />
        </svg>
      );
    case "note":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <path d="M9 18V6l10-2v12" />
          <circle cx="7" cy="18" r="2.4" />
          <circle cx="17" cy="16" r="2.4" />
        </svg>
      );
    case "cam":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <rect x="3" y="7" width="13" height="10" rx="2" />
          <path d="m16 10 5-2v8l-5-2z" />
        </svg>
      );
    case "globe":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3c2.6 3 2.6 15 0 18M12 3c-2.6 3-2.6 15 0 18" />
        </svg>
      );
    case "gear":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <circle cx="12" cy="12" r="3" />
          <path d="M12 3v2.2M12 18.8V21M4.9 6.2l1.6 1.6M17.5 16.2l1.6 1.6M3 12h2.2M18.8 12H21M4.9 17.8l1.6-1.6M17.5 7.8l1.6-1.6" />
        </svg>
      );
    case "user":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <circle cx="12" cy="8" r="3.2" />
          <path d="M5 19a7 7 0 0 1 14 0" />
        </svg>
      );
    case "lock":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <rect x="6" y="11" width="12" height="9" rx="2" />
          <path d="M8 11V8a4 4 0 0 1 8 0v3" />
        </svg>
      );
    case "search":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <circle cx="11" cy="11" r="6.5" />
          <path d="m16 16 4 4" />
        </svg>
      );
    case "trend":
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
          <path d="M4 16 10 10l4 4 6-8" />
          <path d="M15 6h5v5" />
        </svg>
      );
    case "play":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <path d="M8 5v14l12-7z" />
        </svg>
      );
    case "pause":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <rect x="6" y="5" width="4" height="14" />
          <rect x="14" y="5" width="4" height="14" />
        </svg>
      );
    case "prev":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <path d="M6 6h2v12H6zM20 6 10 12l10 6z" />
        </svg>
      );
    case "next":
      return (
        <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
          <path d="M16 6h2v12h-2zM4 6l10 6-10 6z" />
        </svg>
      );
    default:
      return null;
  }
}

function Panel({ area, title, icons, children, onClick, clickable, pulse }) {
  return (
    <section
      className={`panel area-${area} ${clickable ? "is-clickable" : ""} ${pulse ? "is-live" : ""}`}
      onClick={onClick}
      role={clickable ? "button" : undefined}
    >
      <header className="panel-title">
        <h2>{title}</h2>
        <div className="icons">{icons}</div>
      </header>
      <div className="panel-body">{children}</div>
    </section>
  );
}

function FaceReticle({ onClick, receiving }) {
  return (
    <div className={`area-face is-orb ${receiving ? "orb-hot" : ""}`}>
      <button className="orb-hit" onClick={onClick} aria-label="Open central orb" />
      <span className="crosshair-v" />
      <span className="crosshair-h" />
      <div className="reticle">
        <svg viewBox="0 0 200 200">
          <circle cx="100" cy="100" r="34" fill="none" stroke="#4af0ff" strokeWidth="1.2" opacity="0.55" />
          <circle cx="100" cy="100" r="52" fill="none" stroke="#4af0ff" strokeWidth="1.4" strokeDasharray="8 10" opacity="0.75" className="spin-rev" />
          <g className="spin-slow">
            <path
              d="M48 100 A52 52 0 0 1 100 48"
              fill="none"
              stroke="#4af0ff"
              strokeWidth="5"
              strokeLinecap="round"
              opacity="0.95"
            />
            <path
              d="M152 100 A52 52 0 0 1 100 152"
              fill="none"
              stroke="#4af0ff"
              strokeWidth="5"
              strokeLinecap="round"
              opacity="0.95"
            />
            <path
              d="M70 38 A78 78 0 0 1 162 70"
              fill="none"
              stroke="#4af0ff"
              strokeWidth="2"
              opacity="0.7"
            />
            <path
              d="M130 162 A78 78 0 0 1 38 130"
              fill="none"
              stroke="#4af0ff"
              strokeWidth="2"
              opacity="0.7"
            />
          </g>
          <circle cx="100" cy="100" r="78" fill="none" stroke="#4af0ff" strokeWidth="1" opacity="0.28" />
          {[0, 90, 180, 270].map((deg) => (
            <line
              key={deg}
              x1="100"
              y1="16"
              x2="100"
              y2="28"
              stroke="#4af0ff"
              strokeWidth="2"
              transform={`rotate(${deg} 100 100)`}
            />
          ))}
        </svg>
      </div>
    </div>
  );
}

function Sun() {
  return (
    <svg className="sun" viewBox="0 0 64 64">
      <defs>
        <radialGradient id="sg" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#fff4b0" />
          <stop offset="55%" stopColor="#ffd14a" />
          <stop offset="100%" stopColor="#ff9d1a" />
        </radialGradient>
      </defs>
      {Array.from({ length: 12 }).map((_, i) => (
        <line
          key={i}
          x1="32"
          y1="4"
          x2="32"
          y2="12"
          stroke="#ffd24a"
          strokeWidth="3"
          strokeLinecap="round"
          transform={`rotate(${i * 30} 32 32)`}
        />
      ))}
      <circle cx="32" cy="32" r="14" fill="url(#sg)" />
    </svg>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [setting, setSetting] = useState(null);
  const [privacy, setPrivacy] = useState(true);
  const [lang, setLang] = useState("English");
  const [now, setNow] = useState(new Date());
  const [bpm, setBpm] = useState(72);
  const [view, setView] = useState(null);
  const [transmitting, setTransmitting] = useState(false);
  const [newsAgent, setNewsAgent] = useState({ status: "online", sub_agents: [], latest: [] });
  const [sector, setSector] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [orb, setOrb] = useState({ receiving: false, inbox_count: 0, agents: [] });
  const [core, setCore] = useState({ analysis: null, current_action: "Listening." });
  const [filings, setFilings] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [macro, setMacro] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [sentiment, setSentiment] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [history, setHistory] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [performance, setPerformance] = useState({
    status: "idle",
    current_action: "Standing by.",
    report: {},
    days: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [afterHours, setAfterHours] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [earnings, setEarnings] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });
  const [reddit, setReddit] = useState({
    status: "idle",
    current_action: "Standing by.",
    logs: [],
    items: [],
    counts: {},
    steps: [],
  });

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    setMusicLayout(view ? "dock" : "hud");
  }, [view]);

  useEffect(() => {
    let stop = () => {};
    (async () => {
      try {
        const [o, n, s, c, f, m, sent, h, p, ah, ea, rd] = await Promise.all([
          getOrb(),
          getNewsAgent(),
          getSubAgent("sector_news_agent"),
          getCore(),
          getSubAgent("corporate_filings_agent"),
          getSubAgent("macro_policy_agent"),
          getSubAgent("sentiment_agent"),
          getSubAgent("historical_correlation_agent"),
          getPerformance(),
          getSubAgent("after_hours_agent"),
          getSubAgent("earnings_surprise_agent"),
          getRedditAgent(),
        ]);
        setOrb(o);
        setNewsAgent(n);
        setSector(s);
        setCore(c);
        setFilings(f);
        setMacro(m);
        setSentiment(sent);
        setHistory(h);
        setPerformance(p);
        setAfterHours(ah);
        setEarnings(ea);
        setReddit(rd);
      } catch {
        /* backend may still be booting */
      }
      stop = openStream((frame) => {
        const { event, payload } = frame;
        if (event === "snapshot") {
          if (payload.orb) setOrb((prev) => ({ ...prev, ...payload.orb, agents: payload.agents || prev.agents }));
          if (payload.news_agent) setNewsAgent(payload.news_agent);
          if (payload.sector) setSector((prev) => ({ ...prev, ...payload.sector }));
          if (payload.filings) setFilings((prev) => ({ ...prev, ...payload.filings }));
          if (payload.macro) setMacro((prev) => ({ ...prev, ...payload.macro }));
          if (payload.sentiment) setSentiment((prev) => ({ ...prev, ...payload.sentiment }));
          if (payload.history) setHistory((prev) => ({ ...prev, ...payload.history }));
          if (payload.after_hours) setAfterHours((prev) => ({ ...prev, ...payload.after_hours }));
          if (payload.earnings) setEarnings((prev) => ({ ...prev, ...payload.earnings }));
          if (payload.reddit) setReddit((prev) => ({ ...prev, ...payload.reddit }));
          if (payload.performance) setPerformance((prev) => ({ ...prev, ...payload.performance }));
        }
        if (event === "performance_update") {
          setPerformance((prev) => ({ ...prev, ...payload }));
        }
        if (event === "agent_status") {
          const bump = (prev) => ({ ...prev, status: payload.status });
          if (payload.agent === "corporate_filings_agent") setFilings(bump);
          else if (payload.agent === "macro_policy_agent") setMacro(bump);
          else if (payload.agent === "sentiment_agent") setSentiment(bump);
          else if (payload.agent === "historical_correlation_agent") setHistory(bump);
          else if (payload.agent === "news_agent_testing_performance") setPerformance(bump);
          else if (payload.agent === "after_hours_agent") setAfterHours(bump);
          else if (payload.agent === "earnings_surprise_agent") setEarnings(bump);
          else if (payload.agent === "reddit_flow_agent") setReddit(bump);
          else if (payload.agent === "sector_news_agent") setSector(bump);
        }
        if (event === "agent_action") {
          const bump = (prev) => ({ ...prev, current_action: payload.action });
          if (payload.agent === "corporate_filings_agent") setFilings(bump);
          else if (payload.agent === "macro_policy_agent") setMacro(bump);
          else if (payload.agent === "sentiment_agent") setSentiment(bump);
          else if (payload.agent === "historical_correlation_agent") setHistory(bump);
          else if (payload.agent === "news_agent_testing_performance") setPerformance(bump);
          else if (payload.agent === "after_hours_agent") setAfterHours(bump);
          else if (payload.agent === "earnings_surprise_agent") setEarnings(bump);
          else if (payload.agent === "reddit_flow_agent") setReddit(bump);
          else if (payload.agent === "sector_news_agent") setSector(bump);
        }
        if (event === "pipeline_step") {
          const apply = (prev) => {
            const steps = [...(prev.steps || [])];
            const idx = steps.findIndex((s) => s.key === payload.key);
            if (idx >= 0) steps[idx] = payload;
            else steps.push(payload);
            return { ...prev, steps };
          };
          if (payload.agent === "corporate_filings_agent") setFilings(apply);
          else if (payload.agent === "macro_policy_agent") setMacro(apply);
          else if (payload.agent === "sentiment_agent") setSentiment(apply);
          else if (payload.agent === "historical_correlation_agent") setHistory(apply);
          else if (payload.agent === "after_hours_agent") setAfterHours(apply);
          else if (payload.agent === "earnings_surprise_agent") setEarnings(apply);
          else if (payload.agent === "reddit_flow_agent") setReddit(apply);
          else setSector(apply);
        }
        if (event === "log") {
          const bump = (prev) => ({ ...prev, logs: [...(prev.logs || []), payload].slice(-120) });
          if (payload.agent_name === "corporate_filings_agent") setFilings(bump);
          else if (payload.agent_name === "macro_policy_agent") setMacro(bump);
          else if (payload.agent_name === "sentiment_agent") setSentiment(bump);
          else if (payload.agent_name === "historical_correlation_agent") setHistory(bump);
          else if (payload.agent_name === "after_hours_agent") setAfterHours(bump);
          else if (payload.agent_name === "earnings_surprise_agent") setEarnings(bump);
          else if (payload.agent_name === "reddit_flow_agent") setReddit(bump);
          else if (payload.agent_name === "sector_news_agent") setSector(bump);
        }
        if (event === "news_item") {
          const apply = (prev, key) => {
            const items = prev.items || [];
            const idx = items.findIndex((i) => i.id === payload.id);
            const next = idx >= 0 ? items.map((i) => (i.id === payload.id ? payload : i)) : [payload, ...items];
            const counts = { ...(prev.counts || {}) };
            if (payload.status === "completed") {
              counts[payload[key] || payload.sector] =
                (counts[payload[key] || payload.sector] || 0) + (idx >= 0 ? 0 : 1);
            }
            return { ...prev, items: next.slice(0, 80), counts };
          };
          if (payload.agent_name === "corporate_filings_agent") setFilings((p) => apply(p, "filing_type"));
          else if (payload.agent_name === "macro_policy_agent") setMacro((p) => apply(p, "sector"));
          else if (payload.agent_name === "sentiment_agent") setSentiment((p) => apply(p, "sentiment"));
          else if (payload.agent_name === "historical_correlation_agent") setHistory((p) => apply(p, "alignment"));
          else if (payload.agent_name === "after_hours_agent") setAfterHours((p) => apply(p, "window"));
          else if (payload.agent_name === "earnings_surprise_agent") setEarnings((p) => apply(p, "surprise"));
          else if (payload.agent_name === "reddit_flow_agent") setReddit((p) => apply(p, "subreddit"));
          else if (payload.agent_name === "sector_news_agent") setSector((p) => apply(p, "sector"));
          if (payload.status === "completed") {
            setNewsAgent((prev) => ({
              ...prev,
              latest: [payload, ...(prev.latest || [])].slice(0, 8),
            }));
          }
        }
        if (event === "core_update") {
          setCore({ analysis: payload, current_action: payload?.brief || "Briefing ready." });
        }
        if (event === "transmit" || event === "orb_receive") {
          setTransmitting(true);
          setOrb((prev) => ({
            ...prev,
            receiving: true,
            inbox_count: (prev.inbox_count || 0) + 1,
          }));
        }
        if (event === "orb_idle") {
          setTransmitting(false);
          setOrb((prev) => ({ ...prev, receiving: false }));
        }
      });
    })();
    return () => stop();
  }, []);

  useEffect(() => {
    const t = setInterval(() => {
      setBpm((v) => {
        const next = v + (Math.random() > 0.5 ? 1 : -1);
        return Math.min(78, Math.max(66, next));
      });
    }, 1600);
    return () => clearInterval(t);
  }, []);

  const timeLabel = useMemo(
    () =>
      now.toLocaleTimeString("en-IN", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      }),
    [now]
  );

  const contacts = [
    { id: 1, name: "Barian Manan", initials: "BM" },
    { id: 2, name: "Saran Staipson", initials: "SS" },
    { id: 3, name: "Aamy Deth", initials: "AD" },
  ];

  const messages = [
    { name: "Aanya Kapoor", text: "Standby confirmed for 15:00.", time: "1 hr ago" },
    { name: "Dev Mehta", text: "Route lock looks clean.", time: "38 min" },
    { name: "Rhea Sen", text: "Sending the brief now.", time: "3 min ago" },
  ];

  const stocks = [
    { name: "Apple", price: "150.23", change: "+1.2%" },
    { name: "Market", price: "50.23", change: "+1.2%" },
    { name: "Low", price: "150.23", change: "+3.6%" },
  ];

  const news = (newsAgent.latest || []).slice(0, 4);
  const fallbackNews = [
    "News Agent standing by — click to open Sector News.",
    "Waiting for first fetch cycle from market RSS.",
    "Central orb listening for routed packets.",
    "Ask the orb about sugar, IT, pharma, banking, auto.",
  ];

  const bars = [42, 58, 70, 52, 80, 64, 88, 74, 96];

  return (
    <div className={`stage ${view ? "no-photo" : ""}`}>
      <div className="scanlines" />
      <div className="scan-beam" />

      <main className="hud">
        <Panel
          area="status"
          title="AGENT STATUS"
          icons={
            <>
              <Icon name="wifi" />
              <Icon name="battery" />
            </>
          }
        >
          <div className="status-grid">
            <div>
              <div className="sys-label">SYSTEM CHECK</div>
              <div className="bars">
                <div className="bar">
                  <span style={{ width: "86%" }} />
                </div>
                <div className="bar">
                  <span style={{ width: "64%" }} />
                </div>
                <div className="bar">
                  <span style={{ width: "94%" }} />
                </div>
              </div>
            </div>
            <div>
              <div className="sig-label">SIGNAL STRENGTH</div>
              <div className="signals">
                {[12, 20, 28, 36, 44].map((h, i) => (
                  <i key={i} style={{ height: h, animationDelay: `${i * 0.08}s` }} />
                ))}
              </div>
            </div>
          </div>
        </Panel>

        <Panel area="weather" title="AGENT WEATHER">
          <div className="weather">
            <div>
              <div className="temp">
                24<small>°C</small>
              </div>
              <div className="weather-meta">
                <strong>Delhi</strong>
                Partly sunny
              </div>
            </div>
            <Sun />
          </div>
        </Panel>

        <FaceReticle onClick={() => setView("orb")} receiving={transmitting || orb.receiving} />
        {(transmitting || orb.receiving) && <div className="data-beam" aria-hidden />}

        <Panel
          area="maps"
          title="AGENT MAPS"
          icons={<Icon name="plane" />}
        >
          <div className="map-wrap">
            <img src="/map.jpg" alt="City map" />
            <span className="pin" />
          </div>
        </Panel>

        <Panel
          area="contacts"
          title="AGENT CONTACTS"
          icons={<Icon name="users" />}
        >
          <div className="online-label">ONLINE FRIENDS</div>
          {contacts.map((c) => (
            <div className="contact" key={c.id}>
              <div className="avatar online">{c.initials}</div>
              <div>
                <b>{c.name}</b>
                <span>Online</span>
              </div>
            </div>
          ))}
        </Panel>

        <Panel
          area="messages"
          title="AGENT MESSAGES"
          icons={<Icon name="mail" />}
        >
          {messages.map((m) => (
            <div className="msg" key={m.name}>
              <div className="msg-ico">
                <Icon name="user" size={12} />
              </div>
              <div>
                <b>{m.name}</b>
                <p>{m.text}</p>
              </div>
              <time>{m.time}</time>
            </div>
          ))}
        </Panel>

        <Panel area="health" title="AGENT HEALTH">
          <div className="health">
            <div className="metric">
              <span className="heart">
                <Icon name="heart" size={22} />
              </span>
              <div>
                <div className="num">{bpm}</div>
                <div className="unit">BPM</div>
              </div>
            </div>
            <div className="metric">
              <svg className="steps-ring" viewBox="0 0 42 42">
                <circle cx="21" cy="21" r="16" fill="none" stroke="rgba(74,240,255,0.15)" strokeWidth="4" />
                <circle
                  cx="21"
                  cy="21"
                  r="16"
                  fill="none"
                  stroke="#4af0ff"
                  strokeWidth="4"
                  strokeDasharray="80 100"
                  strokeLinecap="round"
                  transform="rotate(-90 21 21)"
                />
                <text x="21" y="23" textAnchor="middle" fontSize="8" fill="#e7fbff">
                  8k
                </text>
              </svg>
              <div>
                <div className="num" style={{ fontSize: 16 }}>
                  8000
                </div>
                <div className="unit">STEPS</div>
              </div>
            </div>
            <div className="level">
              <div className="level-row">
                <span>8000</span>
                <div className="bar">
                  <span style={{ width: "80%" }} />
                </div>
              </div>
              <div className="level-row">
                <span>Level</span>
                <div className="bar">
                  <span style={{ width: "62%" }} />
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel area="calendar" title="AGENT CALENDAR">
          <div className="cal-event">
            <h3>Meeting at 3 PM</h3>
            <time>15:00 · Today</time>
          </div>
          <div className="cal-event" style={{ marginTop: 8, opacity: 0.85 }}>
            <h3 style={{ fontSize: 13 }}>Night sync</h3>
            <time>{timeLabel} live</time>
          </div>
        </Panel>

        <Panel
          area="stock"
          title="AGENT STOCK"
          icons={<Icon name="trend" />}
        >
          {stocks.map((s) => (
            <div className="stock-row" key={s.name}>
              <span>{s.name}</span>
              <span>{s.price}</span>
              <span className="up">{s.change}</span>
            </div>
          ))}
        </Panel>

        <Panel
          area="news"
          title="AGENT NEWS"
          icons={<Icon name="doc" />}
          clickable
          pulse={["fetching", "processing"].includes(sector.status)}
          onClick={() => setView("news-agent")}
        >
          <div className="news-status">
            <span className={`mini ${sector.status || "idle"}`}>{sector.status || "idle"}</span>
            <span>sector_news_agent</span>
          </div>
          {(news.length ? news : fallbackNews).map((n) => (
            <p className="news-line" key={typeof n === "string" ? n : n.id}>
              {typeof n === "string" ? n : `[${n.sector}] ${n.headline}`}
            </p>
          ))}
        </Panel>

        <Panel
          area="social"
          title="AGENT SOCIAL"
          icons={<Icon name="heart" size={13} />}
          clickable
          pulse={["fetching", "processing"].includes(reddit.status)}
          onClick={() => setView("social-agent")}
        >
          <div className="news-status">
            <span className={`mini ${reddit.status || "idle"}`}>{reddit.status || "idle"}</span>
            <span>reddit_flow_agent</span>
          </div>
          {(reddit.items || []).slice(0, 4).map((n) => (
            <p className="news-line" key={n.id}>
              [r/{n.subreddit}] {n.headline}
            </p>
          ))}
          {!(reddit.items || []).length && (
            <>
              <p className="news-line">Click to open Social Agent — live Reddit buzz.</p>
              <p className="news-line">Twitter node is a stub. No fake posts.</p>
            </>
          )}
        </Panel>

        <Panel area="music" title="AGENT MUSIC" icons={<Icon name="note" />}>
          <MusicDeck />
        </Panel>

        <Panel
          area="camera"
          title="AGENT CAMERA"
          icons={<Icon name="cam" />}
        >
          <div className="cam">
            <img src="/person.jpg" alt="Live camera" />
            <div className="rec">
              <i /> REC
            </div>
          </div>
        </Panel>

        <Panel
          area="mail"
          title="AGENT MAIL"
          icons={<Icon name="mail" />}
        >
          <div className="mail-row">
            <div className="mail-ico">
              <Icon name="mail" size={14} />
              <span className="badge" />
            </div>
            <div>
              <b>Unread email</b>
              <p>Briefing pack for 15:00 sync</p>
            </div>
            <span className="mail-count">23</span>
          </div>
          <div className="mail-row">
            <div className="mail-ico">
              <Icon name="mail" size={14} />
            </div>
            <div>
              <b>Subject line</b>
              <p>You will receive the subject</p>
            </div>
            <time>Thursday</time>
          </div>
        </Panel>

        <Panel
          area="browser"
          title="AGENT BROWSER"
          icons={<Icon name="globe" />}
        >
          <div className="search">
            <Icon name="search" size={13} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search the grid..."
            />
          </div>
          <div className="tabs">
            {[1, 2, 3].map((n) => (
              <div className="tab" key={n}>
                <div className="tab-bar">
                  <i />
                  <i />
                  <i />
                </div>
                <div className="tab-body">
                  <span style={{ width: "80%" }} />
                  <span style={{ width: "60%" }} />
                  <span style={{ width: "70%" }} />
                </div>
              </div>
            ))}
          </div>
        </Panel>

        <Panel area="fitness" title="AGENT FITNESS">
          <div className="fitness">
            <div className="chart">
              <div className="axis">
                <span>250</span>
                <span>200</span>
                <span>150</span>
                <span>100</span>
                <span>50</span>
              </div>
              {bars.map((h, i) => (
                <div
                  key={i}
                  className="col"
                  style={{ height: `${h}%`, animationDelay: `${i * 0.06}s` }}
                />
              ))}
            </div>
            <div className="fit-stats">
              <div>
                Distance covered
                <b>50.6 km</b>
              </div>
              <div>
                24 h workout progress
                <div className="bar" style={{ marginTop: 5 }}>
                  <span style={{ width: "74%" }} />
                </div>
              </div>
            </div>
          </div>
        </Panel>

        <Panel
          area="settings"
          title="AGENT SETTINGS"
          icons={<Icon name="gear" />}
        >
          <div className="settings">
            <button className="set-btn" onClick={() => setSetting("profile")}>
              <span className="set-ico">
                <Icon name="user" size={16} />
              </span>
              Profile
            </button>
            <button className="set-btn" onClick={() => setSetting("privacy")}>
              <span className="set-ico">
                <Icon name="lock" size={16} />
              </span>
              Privacy
            </button>
            <button className="set-btn" onClick={() => setSetting("language")}>
              <span className="set-ico">
                <Icon name="globe" size={16} />
              </span>
              Language
            </button>
          </div>
        </Panel>
      </main>

      {view && view.startsWith("social") ? (
        <SocialWorkspace view={view} setView={setView} onClose={() => setView(null)} reddit={reddit} />
      ) : view ? (
        <NewsWorkspace
          view={view}
          setView={setView}
          onClose={() => setView(null)}
          newsAgent={newsAgent}
          sector={sector}
          filings={filings}
          macro={macro}
          sentiment={sentiment}
          history={history}
          performance={performance}
          afterHours={afterHours}
          earnings={earnings}
          core={core}
          orb={orb}
          transmitting={transmitting || orb.receiving}
        />
      ) : null}

      {setting && (
        <div className="modal-back" onClick={() => setSetting(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>AGENT {setting.toUpperCase()}</h3>
            {setting === "profile" && (
              <p>
                Operative: Aryan Vale
                <br />
                Clearance: Level 4
                <br />
                Node: Delhi / live overlay
                <br />
                Session uptime: {timeLabel}
              </p>
            )}
            {setting === "privacy" && (
              <div className="row">
                <label>Face lock + telemetry shield</label>
                <div
                  className={`toggle ${privacy ? "on" : ""}`}
                  onClick={() => setPrivacy((v) => !v)}
                >
                  <i />
                </div>
              </div>
            )}
            {setting === "language" && (
              <div className="row">
                <label>Interface language</label>
                <button
                  className="close"
                  style={{ marginTop: 0 }}
                  onClick={() => setLang((l) => (l === "English" ? "Hindi" : "English"))}
                >
                  {lang}
                </button>
              </div>
            )}
            <button className="close" onClick={() => setSetting(null)}>
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
