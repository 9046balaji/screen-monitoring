# DigiWell: Project Full Analysis Report

This comprehensive report details the complete architecture, structure, and underlying logic of the **DigiWell Screen Time Monitoring** application. The system integrates a robust Python backend with Machine Learning capabilities, a React (Vite) frontend, local desktop tracking agents, and browser extensions to promote digital wellness.

---

## 1. Executive Summary
DigiWell is an AI-powered screen time monitoring, productivity enhancement, and mental wellness application. It goes beyond simple tracking by predicting burnout, classifying usage patterns, and intervening when doomscrolling or addictive behaviors are detected. The application combines continuous local telemetry (desktop and browser tracking) with advanced machine learning models (trained on demographic and psychological indicators) to offer a localized, personalized wellness coach.

## 2. Project Structure & Architecture Overview
The workspace is organized into a modular monolith setup:
*   **Root Level:** Contains entry points (`app.py`), setup scripts (`train_models.py`), configuration (`requirements.txt`, `Dockerfile`), and core markdown guides.
*   **`agent/`:** Collection of Python background worker scripts responsible for local telemetry and intervention enforcement.
*   **`browser_extension/`:** A Chrome-compatible extension allowing tracking and intervention injected directly into the user's web browser.
*   **`database/`:** SQLite database schemas, initialization logic, and localized `.db` storage.
*   **`digiwell/`:** The Vite + React single-page frontend application.
*   **`models/` & `data/`:** Machine Learning artifacts (`.pkl` models) and datasets (CSV, JSON) for training and historical logging.

## 3. Tech Stack Summary
*   **Frontend:** React (Vite), JSX, CSS (custom styles in `src/index.css`), Recharts/visualizations, Axios API client
*   **Backend:** Python, Flask, Pydantic, Pandas, scikit-learn, XGBoost
*   **Local Agents:** psutil, pywin32, plyer, reportlab
*   **Data Storage:** SQLite (local), JSON artifacts
*   **Browser Extension:** Manifest V3, background script (Chrome compatible)
*   **Testing/DevOps:** pytest, Docker, GitHub Actions

## 4. Architecture Diagram (ASCII)
```
                              +-------------------+
                              |  Browser Extension|
                              |  (background.js)  |
                              +---------+---------+
                                        |
                                        | HTTP JSON
                                        v
+-------------------+        +----------+----------+        +---------------------+
| Desktop Agents    |        |   Flask API         |        |  React Frontend     |
| tracker/enforcer/ +------->|   app.py            +<------>+  digiwell/src/*     |
| focus/pomodoro    |  DB    |   ML inference      |  HTTP  |  dashboards/charts |
+---------+---------+        +----------+----------+        +----------+----------+
          |                             |                              |
          | SQLite writes               | Model artifacts               | UI state
          v                             v                              v
 +--------+---------+         +---------+---------+           +--------+---------+
 | SQLite db        |         | models/*.pkl     |           | data/mockData.js |
 | database/data/*  |         | model_report.json|           | local fallbacks  |
 +------------------+         +------------------+           +------------------+
```

## 5. Frontend Architecture (React/Vite)
The frontend (`digiwell/`) is built using modern tooling: **React 18+ and Vite** (configured via `vite.config.ts`), with TypeScript definitions but written heavily in JSX. It acts as an interactive dashboard pulling live data from the Flask API via Axios/Fetch wrappers located in `src/api/digiwell.js`.

The UI is heavily componentized, separating complex charting libraries (likely Recharts or Chart.js) and atomic layout components, keeping the page views highly readable and clean.

## 6. Frontend Screens & Pages
The `src/pages/` directory outlines a comprehensive suite of views:
1.  **Dashboard.jsx**: The main hub displaying the current Wellness Score, active limits, and daily summaries.
2.  **AppTracker.jsx**: Detailed views of daily/hourly usage across applications and categories.
3.  **Analytics.jsx & Reports.jsx**: Deep-dive historical data analysis and generated persona reports.
4.  **Coach.jsx & Therapy.jsx**: AI-driven suggestions and wellness tracking features based on inferred moods.
5.  **FocusMode.jsx**: Interaction layer for triggering the backend `focus_mode.py`/`pomodoro.py` engines.
6.  **MoodJournal.jsx**: Integration mapping screen time against self-reported user moods.
7.  **Predictions.jsx**: The visual interface for evaluating burnout predictions and mental health risks.
8.  **DetoxChallenge.jsx**: Gamification tracking consecutive successful adherence to usage bounds.
9.  **WellnessTips.jsx & Profile.jsx**: User settings, demographics inputs (driving ML), report downloads, and daily snapshot widgets.

## 7. Frontend Components & Hooks
To support the extensive pages, the frontend employs domain-specific hooks and components:
*   **Hooks:**
    *   `use2020Timer.js`: Implements the 20-20-20 rule (every 20 minutes, look 20 feet away for 20 seconds) directly in the browser.
    *   `useDopamineDetector.js`: Client-side heuristic or ML-caller that detects erratic scrolling/tab-switching, triggering interventions.
*   **Components:**
    *   **Cards**: `AddictionRiskCard`, `MentalHealthCard`, `WellnessScoreCard` synthesize backend predictions.
    *   **Charts**: Extensive charting representations (`AddictionHeatmap`, `AppDonutChart`, `FeatureImportanceChart`, `HourlyBarChart`).
    *   **UI Controls**: `InterventionPopup` (disrupts screen during high-risk activity), `Timer2020`, `RiskBadge`.

## 8. Backend Architecture (Python/Flask)
The core backend is driven by **Flask** (`app.py`), wrapped with PyDantic for rigid schema validation (e.g., `UsagePredictSchema`, `ProductivityPredictSchema`). The server exposes REST API endpoints consumed by the frontend and browser extension.
*   **InferenceService**: ML models are abstracted into an `InferenceService` singleton upon boot. This prevents model reloading latency, ensuring high-throughput inference for real-time requests.
*   **CORS Configuration**: Allows local dev frontends (`http://localhost:5173`, `http://localhost:3000`).
*   Data parsing leans heavily on Pandas to transform incoming JSON payloads into structures compatible with the scikit-learn preprocessing pipelines.

## 9. Agents & Background Services
A defining feature of DigiWell is its local background processes in `agent/`:
*   `tracker.py`: Continually polls system APIs to log the active window title and executable name, storing this in the SQLite database.
*   `enforcer.py`: Acts on the predictions. If the backend classifies a session as "doomscrolling," the enforcer intercepts the system processes (killing or overlaying a block screen).
*   `pomodoro.py` & `focus_mode.py`: Manage strict state constraints, pausing trackers or adjusting limits to zero tolerance during focused study/work.
*   `reporter.py`: Compiles end-of-day/end-of-week summaries.

## 10. Machine Learning Models & Logic
The ML training pipeline (`train_models.py`) uses `scikit-learn` and `xgboost` over multiple datasets (Dummy Data, SMMH - Social Media Mental Health, Student Performance).
The application employs multiple models:
*   **Usage Classifier** (RandomForest/XGBoost): Predicts if usage is 'Healthy', 'Moderate', or 'Excessive'. Fixed for data leakage by removing `time_spent` from input features.
*   **Mental Health Classifier**: Assesses risk utilizing inputs like distraction scores, sleep issues, and validation seeking.
*   **Productivity Regressor**: Predicts focus grades based on environment and study conditions.
*   **User Segmentation** (KMeans): Groups users into "Personas" allowing customized interventions.
*   **Anomaly Detector** (IsolationForest): Instantiated live in `app.py` to catch extreme deviations in screen time duration compared to a baseline user profile.

### Datasets Used by `train_models.py`
*   `data/dummy_data.csv` (synthetic): Demographics and usage time. Columns include `age`, `gender`, `time_spent`, `platform`, `interests`, `location`, `demographics`, `profession`, `income`, `indebt`, `isHomeOwner`, `Owns_Car`.
*   `data/smmh.csv` (social media mental health): Survey responses on usage and well-being. Columns include age, gender, relationship/occupation, platform list, daily time, distraction/validation metrics, and sleep issues (questions 1-20).
*   `data/StudentPerformanceFactors.csv` (education factors): Study behavior and outcomes. Columns include `Hours_Studied`, `Attendance`, `Parental_Involvement`, `Access_to_Resources`, `Extracurricular_Activities`, `Sleep_Hours`, `Previous_Scores`, `Motivation_Level`, `Internet_Access`, `Tutoring_Sessions`, `Family_Income`, `Teacher_Quality`, `School_Type`, `Peer_Influence`, `Physical_Activity`, `Learning_Disabilities`, `Parental_Education_Level`, `Distance_from_Home`, `Gender`, `Exam_Score`.

### Model Artifacts
*   `models/model_report.json`: Training metrics, including classifier scores and KMeans silhouette score.
*   `models/persona_map.json`: Cluster id to persona name mapping.

## 11. Database & Schema Design
The application utilizes **SQLite** for lightweight, localized telemetry aggregation in `database/data/digiwell.db`.
Key tables established in `database.py`:
*   `usage_logs`: Tracks daily application usage, storing `process_name`, `category`, and sum of `seconds`.
*   `hourly_logs`: Granular time-series data for the heatmaps.
*   `interventions`: Audits when the system blocked an app or prompted the user.
*   `doom_events`: Logs anomalous risks triggering immediate interventions.
*   `wellness_score` & `detox_challenge`: Historical tracking of gamified wellness metrics and consecutive achievements.

## 12. Data Flow & State Management
1.  **Data Capture:** `tracker.py` and `background.js` capture system/web events.
2.  **Telemetry Ingestion:** Agents write raw telemetry to the SQLite db.
3.  **Inference Loop:** `app.py` computes aggregated metrics (e.g., Deep Work vs Distracted Ratios). High-risk metrics trigger an IsolationForest prediction or XGBoost classification.
4.  **Intervention Dispatch:** If flagged, `app.py` writes to `doom_events` or triggers `enforcer.py` locally and websockets/HTTP pushes the `InterventionPopup` to the React UI and extension.
5.  **Reporting:** `React` views retrieve aggregated trends from the API to populate `AddictionRiskCard` and historical graphs.

## 13. Browser Extension Integration
Located in `browser_extension/`, the `manifest.json` and `background.js` construct a Chromium/WebExtension standard tool. It operates adjacently to the desktop agent, capable of tracking fine-grained URL visits and directly injecting DOM overlays to prevent doomscrolling on specific domains (e.g., social media feeds), reporting telemetry directly to the Flask `/api` endpoints.

## 14. Security, Testing & Deployment
*   **Containerization**: Handled gracefully via `Dockerfile`, allowing reproducible deployment of the Python backend and database layer setup.
*   **Testing**: Basic assertions and endpoint validations exist inside `tests/test_app.py`, mapping Pytest logic to the Flask endpoints.
*   **Safety**: Validations heavily rely on `PyDantic`. Since ML inferences fail hard if anomalous numeric types are passed, strict typing ensures service continuity. CORS configuration prevents external web pages from accessing local telemetry APIs.

## 15. Backend API Surface (Selected)
The Flask API is extensive; below are the major grouped routes consumed by the UI, agents, and extension:
*   **Health/Meta:** `/api/health`, `/api/model/report`
*   **Usage + Analytics:** `/api/tracker/live`, `/api/analytics/weekly`, `/api/addiction-heatmap`, `/api/productivity-score`
*   **Predictions:** `/api/predict/usage`, `/api/predict/mental_health`, `/api/predict/productivity`, `/api/predict/burnout`, `/api/predict/realtime`, `/api/predict/simulation`, `/api/anomaly`
*   **Interventions:** `/api/interventions`, `/api/interventions/<id>`, `/api/focus/recommend`
*   **Focus + Pomodoro:** `/api/focus/start`, `/api/focus/stop`, `/api/focus/status`, `/api/pomodoro/start`, `/api/pomodoro/stop`, `/api/pomodoro/state`
*   **Wellness + Journal:** `/api/wellness-score`, `/api/mood`, `/api/daily-reflection`, `/api/dopamine-loop`
*   **Reports + Coach:** `/api/reports/daily`, `/api/reports/weekly`, `/api/chat`, `/api/coach/chat`, `/api/therapy/plan`
*   **Tracker Ingestion:** `/api/tracker/browser`

## 16. Feature Summary Table
| Area | Feature | Primary Components | Notes |
| --- | --- | --- | --- |
| Tracking | Desktop activity logging | `agent/tracker.py`, `database.py` | Foreground window capture, app category logging |
| Tracking | Browser tab tracking | `browser_extension/background.js`, `/api/tracker/browser` | Sends domain usage to backend |
| Analytics | Heatmaps and trends | `AddictionHeatmap`, `HeatmapChart`, `/api/addiction-heatmap` | Hourly patterns and weekly usage |
| ML | Usage + risk prediction | `train_models.py`, `InferenceService` | Usage class, mental health risk, productivity |
| Interventions | Doomscroll detection | `enforcer.py`, `/api/doom-detection` | Blocking overlays and event logs |
| Focus | Pomodoro + focus mode | `pomodoro.py`, `focus_mode.py` | Session timers and enforced blocking |
| Wellness | Mood journal + tips | `MoodJournal.jsx`, `/api/mood-journal` | User self-reporting and insights |
| Reporting | PDF reports + snapshot widgets | `reporter.py`, `/api/reports/daily`, `/api/reports/weekly`, `Profile.jsx` | Daily/weekly exports and in-profile snapshot |

## 17. Conclusion & Future Enhancements
DigiWell is a remarkably thorough monolithic project combining standard application tracking with advanced predictive heuristics. 
**Future Enhancements could include:**
*   Migrating SQLite to a specialized Timeseries Database (like InfluxDB or TimescaleDB) to handle tracking granularity better.
*   Integrating a local LLM or robust NLP to assess chat logs or typing speeds as secondary heuristic indicators of mood.
*   Deploying the React frontend via Electron/Tauri to bundle the entire Python backend and desktop background agents into a single cross-platform `.exe` or `.dmg` executable.
