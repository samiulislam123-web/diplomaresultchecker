# BTEB Result Search — Full Calculator + Result Search

This package keeps the full existing calculator frontend and serves it from the same FastAPI app as `/api/result`.

## Local

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000/`.

## API

`/api/result?probidhan=2022&roll=208325`

## Render Free

Push the repository root to GitHub, then create a Render Blueprint using `render.yaml`.

Important: the current SQLite database is bundled with the deployment. Render Free's filesystem is not persistent, so use a persistent external database for long-term live imports/updates.
