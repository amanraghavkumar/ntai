import { useEffect, useRef } from "react";
import { useMusic } from "../MusicContext.jsx";
import { placeMusic } from "../musicEngine";

function Ico({ name, size = 13 }) {
  const s = { width: size, height: size };
  if (name === "play") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
        <path d="M8 5v14l12-7z" />
      </svg>
    );
  }
  if (name === "pause") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
        <rect x="6" y="5" width="4" height="14" />
        <rect x="14" y="5" width="4" height="14" />
      </svg>
    );
  }
  if (name === "prev") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
        <path d="M6 6h2v12H6zM20 6 10 12l10 6z" />
      </svg>
    );
  }
  if (name === "next") {
    return (
      <svg viewBox="0 0 24 24" fill="currentColor" style={s}>
        <path d="M16 6h2v12h-2zM4 6l10 6-10 6z" />
      </svg>
    );
  }
  if (name === "search") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
        <circle cx="11" cy="11" r="6.5" />
        <path d="m16 16 4 4" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={s}>
      <path d="M9 18V6l10-2v12" />
      <circle cx="7" cy="18" r="2.4" />
      <circle cx="17" cy="16" r="2.4" />
    </svg>
  );
}

export default function MusicDeck() {
  const {
    q,
    setQ,
    busy,
    openHits,
    setOpenHits,
    playing,
    hasPlayer,
    pack,
    tracks,
    current,
    idx,
    runSearch,
    pick,
    step,
    toggle,
  } = useMusic();
  const boxRef = useRef(null);

  useEffect(() => {
    function onDoc(e) {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpenHits(false);
    }
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [setOpenHits]);

  useEffect(() => {
    placeMusic();
  }, [playing, hasPlayer, current]);

  return (
    <div className="music-deck" ref={boxRef} onClick={(e) => e.stopPropagation()}>
      <form
        className="music-search"
        onSubmit={(e) => {
          e.preventDefault();
          runSearch();
        }}
      >
        <Ico name="search" size={11} />
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onFocus={() => tracks.length && setOpenHits(true)}
          placeholder="Search YouTube…"
          aria-label="Search YouTube music"
        />
        <button type="submit" disabled={busy || !q.trim()}>
          {busy ? "…" : "GO"}
        </button>
      </form>

      <div className="music">
        <div className={`album album-slot ${playing || hasPlayer ? "is-on" : ""}`}>
          {!(playing || hasPlayer) &&
            (current?.thumbnail ? <img src={current.thumbnail} alt="" /> : <Ico name="note" size={18} />)}
        </div>
        <div className="music-meta">
          <h3 title={current?.title}>{current ? current.title : "YouTube se gaana chuno"}</h3>
          <p>
            {current
              ? `${current.channel}${current.duration ? ` · ${current.duration}` : ""}`
              : "Live search · no fake tracks"}
          </p>
          <div className="controls">
            <button type="button" onClick={() => step(-1)} disabled={!tracks.length} aria-label="Previous">
              <Ico name="prev" />
            </button>
            <button type="button" className="play" onClick={toggle} aria-label="Play">
              <Ico name={playing ? "pause" : "play"} />
            </button>
            <button type="button" onClick={() => step(1)} disabled={!tracks.length} aria-label="Next">
              <Ico name="next" />
            </button>
            {tracks.length > 0 && (
              <span className="music-count">
                {idx + 1}/{tracks.length}
              </span>
            )}
          </div>
        </div>
      </div>

      {openHits && (tracks.length > 0 || pack.last_error) && (
        <ul className="music-hits">
          {pack.last_error && <li className="music-miss">{pack.last_error}</li>}
          {tracks.map((t) => (
            <li key={t.video_id}>
              <button
                type="button"
                className={current?.video_id === t.video_id ? "on" : ""}
                onClick={() => pick(t, true)}
              >
                <img src={t.thumbnail} alt="" />
                <span>
                  <b>{t.title}</b>
                  <em>
                    {t.channel}
                    {t.duration ? ` · ${t.duration}` : ""}
                  </em>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
