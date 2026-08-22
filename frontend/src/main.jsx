import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { MusicProvider } from "./MusicContext.jsx";
import "./index.css";
import "./constellation.css";

createRoot(document.getElementById("root")).render(
  <MusicProvider>
    <App />
  </MusicProvider>
);
