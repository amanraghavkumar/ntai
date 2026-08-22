import { createContext, useContext, useEffect, useState } from "react";
import { getMusicAgent, searchMusic } from "./api";
import { bindMusicControls, mountMusicEngine, pauseMusic, setMusicPlaying, showMusic } from "./musicEngine";

const MusicCtx = createContext(null);

export function MusicProvider({ children }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [openHits, setOpenHits] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [hasPlayer, setHasPlayer] = useState(false);
  const [pack, setPack] = useState({
    results: [],
    now_playing: null,
    index: 0,
    status: "idle",
    current_action: "YouTube search ready.",
    last_error: null,
  });

  const tracks = pack.results || [];
  const current = pack.now_playing || tracks[pack.index] || null;
  const idx = current ? Math.max(0, tracks.findIndex((t) => t.video_id === current.video_id)) : 0;

  useEffect(() => {
    mountMusicEngine();
    getMusicAgent()
      .then((snap) => {
        setPack(snap);
        if (snap.query) setQ(snap.query);
      })
      .catch(() => {});
  }, []);

  function pick(track, autoplay = true) {
    setPack((prev) => {
      const index = (prev.results || []).findIndex((t) => t.video_id === track.video_id);
      return {
        ...prev,
        now_playing: track,
        index: index >= 0 ? index : prev.index,
        current_action: track.title,
      };
    });
    setOpenHits(false);
    setPlaying(autoplay);
    setHasPlayer(true);
    showMusic(track, { autoplay });
  }

  function step(dir) {
    if (!tracks.length) return;
    const next = tracks[(idx + dir + tracks.length) % tracks.length];
    pick(next, true);
  }

  function toggle() {
    if (!current) {
      if (tracks[0]) pick(tracks[0], true);
      return;
    }
    if (playing) {
      pauseMusic();
      setPlaying(false);
    } else if (hasPlayer) {
      setMusicPlaying(true);
      setPlaying(true);
    } else {
      pick(current, true);
    }
  }

  useEffect(() => {
    bindMusicControls({
      prev: () => step(-1),
      next: () => step(1),
      toggle,
    });
  });

  async function runSearch(raw) {
    const term = (raw ?? q).trim();
    if (!term) return;
    setBusy(true);
    setOpenHits(true);
    try {
      const snap = await searchMusic(term);
      setPack(snap);
    } catch (err) {
      setPack((prev) => ({
        ...prev,
        status: "error",
        last_error: err.message || "Search failed",
        current_action: "YouTube search fail.",
      }));
    } finally {
      setBusy(false);
    }
  }

  const api = {
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
  };

  return <MusicCtx.Provider value={api}>{children}</MusicCtx.Provider>;
}

export function useMusic() {
  const ctx = useContext(MusicCtx);
  if (!ctx) throw new Error("useMusic outside MusicProvider");
  return ctx;
}
