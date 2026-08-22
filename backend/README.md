# Agent HUD backend

FastAPI hub for the News Agent graph.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Then start the frontend (`cd frontend && npm run dev`). The Vite dev server proxies `/api` here.
