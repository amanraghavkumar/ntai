/** YouTube plays inside AGENT MUSIC only. Auto-next when a track ends. */

const ROOT_ID = "yt-persist-root";
let handlers = { prev: () => {}, next: () => {}, toggle: () => {} };
let listening = false;
let lastEnded = 0;

function embedUrl(videoId, autoplay) {
  const origin = typeof window !== "undefined" ? window.location.origin : "";
  return `https://www.youtube.com/embed/${videoId}?enablejsapi=1&autoplay=${
    autoplay ? 1 : 0
  }&rel=0&modestbranding=1&playsinline=1&fs=0&controls=0&disablekb=1&iv_load_policy=3&origin=${encodeURIComponent(
    origin
  )}`;
}

function frame() {
  return document.querySelector("#yt-persist-frame");
}

function ytCmd(el, func, args = []) {
  try {
    el?.contentWindow?.postMessage(JSON.stringify({ event: "command", func, args }), "*");
  } catch {
    /* ignore */
  }
}

function armPlayer(el) {
  if (!el?.contentWindow) return;
  try {
    el.contentWindow.postMessage(JSON.stringify({ event: "listening", id: 1 }), "*");
    ytCmd(el, "addEventListener", ["onStateChange"]);
    ytCmd(el, "addEventListener", ["onReady"]);
  } catch {
    /* ignore */
  }
}

function onYtMessage(ev) {
  const data = ev.data;
  let payload = data;
  if (typeof data === "string") {
    if (!data.startsWith("{") && !data.startsWith("[")) return;
    try {
      payload = JSON.parse(data);
    } catch {
      return;
    }
  }
  if (!payload || typeof payload !== "object") return;

  if (payload.event === "onReady" || payload.event === "initialDelivery") {
    armPlayer(frame());
    return;
  }

  let state = null;
  if (payload.event === "onStateChange") state = payload.info;
  else if (payload.info && typeof payload.info.playerState === "number") state = payload.info.playerState;
  if (state !== 0) return;

  const now = Date.now();
  if (now - lastEnded < 1200) return;
  lastEnded = now;
  handlers.next();
}

function ensureListen() {
  if (listening || typeof window === "undefined") return;
  listening = true;
  window.addEventListener("message", onYtMessage);
}

export function bindMusicControls(next) {
  handlers = { ...handlers, ...next };
}

export function mountMusicEngine() {
  if (typeof document === "undefined") return null;
  ensureListen();
  let root = document.getElementById(ROOT_ID);
  if (root) return root;
  root = document.createElement("div");
  root.id = ROOT_ID;
  root.className = "yt-embed";
  root.innerHTML = `<iframe id="yt-persist-frame" title="YouTube" allow="autoplay; encrypted-media"></iframe>`;
  const el = root.querySelector("iframe");
  el?.addEventListener("load", () => {
    setTimeout(() => armPlayer(el), 250);
  });
  return root;
}

export function placeMusic() {
  const root = mountMusicEngine();
  const slot = document.querySelector(".album-slot");
  if (!root || !slot) return;
  if (root.parentElement !== slot) slot.appendChild(root);
  Object.assign(root.style, {
    position: "absolute",
    inset: "0",
    width: "100%",
    height: "100%",
    left: "0",
    top: "0",
    right: "0",
    bottom: "0",
  });
}

export function setMusicLayout() {
  placeMusic();
}

export function showMusic(track, { autoplay = true } = {}) {
  const root = mountMusicEngine();
  if (!root || !track?.video_id) return;
  root.classList.add("is-on");
  const el = root.querySelector("#yt-persist-frame");
  if (el) el.src = embedUrl(track.video_id, autoplay);
  setMusicPlaying(autoplay);
  requestAnimationFrame(placeMusic);
}

export function setMusicPlaying(playing) {
  const root = document.getElementById(ROOT_ID);
  const el = root?.querySelector("#yt-persist-frame");
  if (playing) {
    root?.classList.add("is-on");
    ytCmd(el, "playVideo");
    requestAnimationFrame(placeMusic);
  } else {
    ytCmd(el, "pauseVideo");
  }
}

export function pauseMusic() {
  setMusicPlaying(false);
}
