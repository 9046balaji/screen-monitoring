# DigiWell - Screen Time Monitoring

DigiWell is a full-stack digital wellness platform for tracking screen time, analyzing usage behavior, and improving daily focus habits.

This repository includes:
- A Flask backend API with analytics, planner, mood, and AI endpoints
- A React + Vite frontend dashboard (`digiwell/`)
- Background app-usage trackers for desktop/browser activity
- SQLite storage with migrations
- ML training/inference utilities for risk and productivity predictions

## Tech Stack

- Backend: Python, Flask, Flask-CORS, SQLite
- ML/Data: scikit-learn, XGBoost, pandas, numpy, joblib
- Frontend: React 19, Vite, Axios, Recharts, Framer Motion
- Platform tooling: Windows app tracker (`pywin32`, `psutil`), optional Chrome extension, Docker

## Repository Structure

Key folders/files:

- `app.py`: Main Flask API (core routes + service bootstrap)
- `database/`: SQLite initialization and schema migrations
- `services/`: Analytics services (`analytics_service.py`, `weekly_analytics_service.py`)
- `agent/`: Background tracker and focus/pomodoro/blocking helpers
- `monitor/`: Session-based desktop screen monitor (`screen_monitor.py`)
- `ai_service.py`: Mood analysis, relapse prediction, coaching helpers
- `train_models.py`: ML training pipeline and model artifact generation
- `models/`: Trained model artifacts and reports
- `data/`: JSON/CSV data inputs and local runtime state
- `browser_extension/`: Manifest v3 extension for browser activity tracking
- `digiwell/`: Frontend web app
- `tests/`: Backend API and feature tests
- `start_digiwell.bat`: Windows one-click launcher

## Core Features

- Screen-time tracking (desktop and browser)
- Daily/weekly/monthly analytics and reports
- Focus mode, pomodoro, app limits, and interventions
- Mood journal with AI-assisted analysis
- Relapse-risk and anomaly predictions
- Weekly planner, daily tasks, adherence, and streak analytics
- AI coach chat endpoints (local Ollama + heuristic fallbacks)

## Prerequisites

- Python 3.10+
- Node.js 18+
- npm
- Windows recommended for desktop tracker features (`pywin32`)

Optional:
- Ollama running locally for `/api/chat` (`http://localhost:11434`)
- Chrome/Edge for browser extension testing

## Quick Start (Windows)

From repository root:

```bat
start_digiwell.bat
```

This starts:
- App tracker (`agent/tracker.py`)
- Flask backend (`http://localhost:5000`)
- Frontend (`http://localhost:3000`)

## Manual Setup

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Backend runs on `http://localhost:5000`.

### 2. Frontend

```powershell
cd digiwell
npm install
npm run dev
```

Frontend runs on `http://localhost:3000` (configured in `digiwell/package.json`).

If your app expects a specific API host, set in `digiwell/.env`:

```env
VITE_API_BASE_URL=http://localhost:5000/api
VITE_USE_MOCK=false
```

## Database

- SQLite file: `database/data/digiwell.db`
- Startup actions in `app.py`:
  - `init_db()`
  - `apply_migrations()`

You can apply migrations directly:

```powershell
python -m database.migrations apply
```

## ML Models

Train/regenerate model artifacts:

```powershell
python train_models.py
```

Artifacts are written to `models/` and include:
- `usage_classifier.pkl`
- `mental_health_classifier.pkl`
- `productivity_regressor.pkl`
- `user_segmentation.pkl`
- `scaler.pkl`
- `encoders.pkl`
- `model_report.json`
- `persona_map.json`

## API Overview

The backend exposes many endpoints under `/api`, including:

- Health: `/api/health`
- Predictions: `/api/predict/*`, `/api/anomaly`, `/api/predictions/relapse-risk`
- Analytics: `/api/analytics/*`, `/api/reports/*`, `/api/productivity-score`
- Tracking/limits: `/api/tracker/live`, `/api/tracker/browser`, `/api/limits`, `/api/interventions`
- Focus/pomodoro: `/api/focus/*`, `/api/pomodoro/*`
- Mood and coach: `/api/mood`, `/api/mood/analyze-and-save`, `/api/chat`, `/api/coach/chat`
- Planner: `/api/timetable*`, `/api/dailytasks*`, `/api/weekly-plan/*`, `/api/planner/*`

## Testing

Run backend tests:

```powershell
pytest
```

Example tests include:
- `tests/test_app.py`
- `tests/test_relapse_api.py`
- `tests/test_commitments.py`

## Docker

Build and run backend container:

```powershell
docker build -t digiwell-backend .
docker run --rm -p 5000:5000 digiwell-backend
```

## Browser Extension (Optional)

Path: `browser_extension/`

- Manifest v3 extension that sends tab/domain activity to the backend
- Host permission targets `http://localhost:5000/*`

Load unpacked extension in Chrome/Edge for local testing.

## Notes

- Several features rely on local files under `data/` (for limits, focus session, journals, and category maps).
- Desktop active-window tracking is Windows-oriented.
- If AI chat fallback appears, verify Ollama is running locally.

