import { useEffect } from "react";
import { runRedditAgent } from "../api";

const STATUS_LABEL = {
  idle: "Idle",
  fetching: "Fetching",
  processing: "Processing",
  done: "Done",
  error: "Error",
  online: "Online",
};

const RING = [
  {
    name: "reddit_flow_agent",
    display_name: "Reddit Flow Agent",
    short: "REDDIT",
    feed: "REDDIT BUZZ IN",
    angle: -90,
    color: "#ff7a45",
    live: true,
    job: "India market subs se live RSS — IndiaInvestments, IndianStreetBets, IndianStockMarket.",
    steps: [
      "Public Reddit RSS lao (429 se bachne ke liye gap)",
      "Tracked company naam nikaalo — nahi to buzz-only",
      "Named posts News CORE ke NEWS FLOW mein jaate hain, NEXT SESSION mein nahi",
    ],
  },
  {
    name: "twitter_buzz_agent",
    display_name: "Twitter Buzz Agent",
    short: "TWITTER",
    feed: "NOT WIRED",
    angle: 90,
    color: "#7dd3fc",
    live: false,
    job: "Folder ready. Official X API paid / blocked — koi fake tweet nahi.",
    steps: ["Public source milne par yahi node live hoga"],
  },
];

export default function SocialWorkspace({ view, setView, onClose, reddit }) {
  const open = RING.find((n) => view === n.name);
  const pack = reddit || { items: [], logs: [], counts: {}, status: "idle", current_action: "Standing by." };

  async function onRun() {
    try {
      await runRedditAgent();
    } catch (err) {
      console.error(err);
    }
  }

  return (
    <div className="workspace constellation">
      <div className="ws-top">
        <div className="ws-crumbs">
          <button onClick={() => setView("social-agent")}>SOCIAL AGENT</button>
          {open && (
            <>
              <span>/</span>
              <b>{open.display_name.toUpperCase()}</b>
            </>
          )}
        </div>
        <button className="ws-close" onClick={onClose}>
          CLOSE
        </button>
      </div>
      {open ? (
        <SocialAgentPage meta={open} pack={pack} onRun={onRun} onBack={() => setView("social-agent")} />
      ) : (
        <SocialRing nodes={RING.map((n) => ({ ...n, status: n.live ? pack.status : "idle" }))} onOpen={(name) => setView(name)} />
      )}
    </div>
  );
}

function SocialRing({ nodes, onOpen }) {
  const cx = 50;
  const cy = 50;
  const r = 28;
  return (
    <div className="ring-stage">
      <div className="core-wrap" style={{ pointerEvents: "none" }}>
        <div className="core-spin" />
        <div className="core-ball" style={{ background: "radial-gradient(circle at 38% 32%, #ffd4c2, #ff7a45 42%, #7a2408 78%)" }}>
          <span className="core-kicker">SOCIAL</span>
          <b>BUZZ</b>
          <small>REDDIT LIVE · TWITTER STUB</small>
        </div>
      </div>
      {nodes.map((n) => {
        const rad = (n.angle * Math.PI) / 180;
        return (
          <button
            key={n.name}
            className="sat-node"
            style={{ left: `${50 + r * Math.cos(rad)}%`, top: `${50 + r * Math.sin(rad)}%`, "--sat": n.color }}
            onClick={() => onOpen(n.name)}
          >
            <span className="sat-ring" />
            <span className="sat-label">{n.short}</span>
            <span className="sat-feed">{n.feed}</span>
            <span className={`sat-st st-${n.status || "idle"}`}>{STATUS_LABEL[n.status] || "Idle"}</span>
          </button>
        );
      })}
      <p className="ring-hint">Click REDDIT for live posts. Twitter is a stub on purpose.</p>
    </div>
  );
}

function SocialAgentPage({ meta, pack, onRun, onBack }) {
  const status = meta.live ? pack.status : "idle";
  useEffect(() => {
    if (!meta.live) return;
    if (["fetching", "processing"].includes(pack.status)) return;
    if ((pack.items || []).length > 0) return;
    onRun();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta.name]);

  return (
    <section className="agent-page glass">
      <header className="ws-head">
        <div>
          <p className="kicker" style={{ color: meta.color }}>
            SOCIAL AGENT · {meta.name}
          </p>
          <h3>{meta.display_name}</h3>
        </div>
        <div className="head-actions">
          <span className={`pill pill-${status}`}>{STATUS_LABEL[status] || "Idle"}</span>
          {meta.live && (
            <button className="run-btn" onClick={onRun} disabled={["fetching", "processing"].includes(status)}>
              RUN CYCLE
            </button>
          )}
          <button className="run-btn" onClick={onBack}>
            BACK
          </button>
        </div>
      </header>
      <p className="ws-copy">{meta.job}</p>
      <div className="live-line">
        <span className="pulse-dot" />
        {meta.live ? pack.current_action : "Not wired. No fake tweets."}
      </div>
      <div className="howto">
        <p className="kicker">HOW THIS AGENT WORKS</p>
        <ol>
          {(meta.steps || []).map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      </div>
      {meta.live ? (
        <div className="detail-split">
          <div className="log-pane">
            <p className="kicker">ACTIVITY LOG</p>
            <ul className="log-list">
              {(pack.logs || [])
                .slice()
                .reverse()
                .map((l, i) => (
                  <li key={`${l.timestamp}-${i}`}>
                    <time>{(l.timestamp || "").slice(11, 19)}</time>
                    <span>{l.message}</span>
                  </li>
                ))}
            </ul>
          </div>
          <div className="news-pane">
            <ul className="item-list">
              {(pack.items || []).map((n) => (
                <li key={n.id}>
                  <div className="item-top">
                    <em>r/{n.subreddit}</em>
                    <span className="mini">{n.named ? "named" : "buzz"}</span>
                  </div>
                  {n.source_url ? (
                    <a href={n.source_url} target="_blank" rel="noreferrer">
                      {n.headline}
                    </a>
                  ) : (
                    <b>{n.headline}</b>
                  )}
                  {n.companies?.length > 0 && <p>{n.companies.join(", ")}</p>}
                </li>
              ))}
              {(pack.items || []).length === 0 && <li className="empty">No posts yet.</li>}
            </ul>
          </div>
        </div>
      ) : (
        <div className="empty-board">
          <p>Twitter / X official API yahan nahi hai.</p>
          <p>Jab koi public source chalega, ye node live hoga. Abhi koi scripted tweet nahi.</p>
        </div>
      )}
    </section>
  );
}
