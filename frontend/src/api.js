export async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const getOrb = () => api("/api/orb");
export const getNewsAgent = () => api("/api/news-agent");
export const getSubAgent = (name) => api(`/api/news-agent/sub-agents/${name}`);
export const getNews = (sector) =>
  api(`/api/news${sector ? `?sector=${encodeURIComponent(sector)}` : ""}`);
export const runSectorAgent = (sectors) =>
  api("/api/news-agent/sub-agents/sector_news_agent/run", {
    method: "POST",
    body: JSON.stringify({ sectors: sectors || null }),
  });
export const runFilingsAgent = () =>
  api("/api/news-agent/agents/corporate_filings_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runMacroAgent = () =>
  api("/api/news-agent/agents/macro_policy_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runSentimentAgent = () =>
  api("/api/news-agent/agents/sentiment_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runHistoryAgent = () =>
  api("/api/news-agent/agents/historical_correlation_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runAfterHoursAgent = () =>
  api("/api/news-agent/agents/after_hours_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runEarningsAgent = () =>
  api("/api/news-agent/agents/earnings_surprise_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const getPerformance = () => api("/api/news-agent/performance");
export const runPerformanceAgent = () =>
  api("/api/news-agent/agents/news_agent_testing_performance/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const runRedditAgent = () =>
  api("/api/social-agent/agents/reddit_flow_agent/run", {
    method: "POST",
    body: JSON.stringify({}),
  });
export const getSocialAgent = () => api("/api/social-agent");
export const getRedditAgent = () => api("/api/social-agent/agents/reddit_flow_agent");
export const getMusicAgent = () => api("/api/music-agent");
export const searchMusic = (q) => api(`/api/music-agent/search?q=${encodeURIComponent(q)}`);
export const getCore = () => api("/api/news-agent/core");
export const runCoreAnalyze = () =>
  api("/api/news-agent/core/analyze", { method: "POST", body: JSON.stringify({}) });
export const sendChat = (message) =>
  api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message }),
  });

export function openStream(onEvent) {
  const es = new EventSource("/api/stream");
  es.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data));
    } catch {
      /* ignore malformed frames */
    }
  };
  return () => es.close();
}
