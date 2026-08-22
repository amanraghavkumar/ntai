---
title: Agent HUD
emoji: 🛰️
colorFrom: yellow
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Agent HUD

News CORE + YouTube music. Hugging Face Space = Docker (frontend + FastAPI together).

Local:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000

cd frontend
npm install
npm run dev
```
