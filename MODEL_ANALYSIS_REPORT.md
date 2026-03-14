# MODEL ANALYSIS REPORT

Date: 2026-03-14
Project: Screen Time Monitoring / DigiWell
Auditor Role: Senior ML Engineer, AI Auditor, Data Scientist

## 1. Overview Of AI Models In The System

This repository contains 5 persisted model artifacts under `models/`:
- 4 primary scikit-learn models trained by `train_models.py` and used by Flask inference endpoints.
- 1 relapse artifact (`relapse_model.pkl`) created by `scripts/generate_relapse_model.py`.

Also present:
- Runtime-only anomaly detector (`IsolationForest`) trained at app startup from CSV data (not persisted as a model file).
- Several endpoints labeled "AI" that are heuristic/rule-based, not ML-trained models.

## 2. Model Inventory

### 2.1 Persisted ML/AI Artifacts

| Model Name | File | Type | Serialized Class | Used At Runtime |
| --- | --- | --- | --- | --- |
| Usage Category Classifier | `models/usage_classifier.pkl` | Multi-class classification | `RandomForestClassifier` | Yes |
| Mental Health Risk Classifier | `models/mental_health_classifier.pkl` | Multi-class classification | `GradientBoostingClassifier` | Yes |
| Productivity Regressor | `models/productivity_regressor.pkl` | Regression | `Ridge` | Yes |
| User Segmentation | `models/user_segmentation.pkl` | Clustering | `KMeans` | Yes |
| Relapse Risk Model (mock artifact) | `models/relapse_model.pkl` | Intended risk prediction | `MockModel` | Partially (loaded, but prediction path is mocked/static) |
| Clustering Scaler | `models/scaler.pkl` | Preprocessing | `StandardScaler` | Yes (segmentation endpoint) |
| Label Encoders | `models/encoders.pkl` | Preprocessing metadata | `dict[str, LabelEncoder]` | Yes |
| Model Metrics Report | `models/model_report.json` | Metadata | JSON | Yes |
| Persona Mapping | `models/persona_map.json` | Metadata | JSON | Yes |

### 2.2 Runtime Model (Not Saved As File)

| Model Name | Location | Type | Runtime Status |
| --- | --- | --- | --- |
| Usage Anomaly Detector | `app.py` (`InferenceService.load_models`) | `IsolationForest` | Trained at startup from `data/dummy_data.csv` |

### 2.3 Search Result For Common Model Formats

Repository scan found no `.pt`, `.h5`, `.onnx`, `.sav`, `.joblib` standalone files beyond the `.pkl` artifacts in `models/`.

## 3. Purpose Of Each Model

### 3.1 Usage Category Classifier
- Problem solved: classify user usage as `Healthy`, `Moderate`, `Excessive`.
- Output: class label + confidence.
- Endpoint: `POST /api/predict/usage`.
- Frontend usage: `predictUsageCategory()` in `digiwell/src/api/digiwell.js`, called by `Dashboard.jsx`.
- How output is used: shown in dashboard risk badges and summaries.

### 3.2 Mental Health Risk Classifier
- Problem solved: classify mental health risk level (`Low`, `Medium`, `High`) from social media behavior and self-report scales.
- Output: class label + confidence + `risk_score`.
- Endpoint: `POST /api/predict/mental_health`.
- Frontend usage: `getMentalHealthRisk()` called by `Dashboard.jsx`, `Predictions.jsx`, `WellnessTips.jsx`.
- How output is used: risk UI cards, confidence bar, recommendations context.

### 3.3 Productivity Regressor
- Problem solved: predict exam score (proxy for productivity) from student/lifestyle factors.
- Output: `predicted_exam_score` and normalized `productivity_score`.
- Endpoint: `POST /api/predict/productivity`.
- Frontend usage: `predictProductivity()` called by `Dashboard.jsx`, `WellnessTips.jsx`.
- How output is used: productivity cards and wellness tips messaging.

### 3.4 User Segmentation (KMeans)
- Problem solved: assign user persona cluster for behavioral archetyping.
- Output: `cluster_id`, `persona`, `risk`, description.
- Endpoint: `POST /api/user/segment`.
- Frontend usage: `getUserCluster()` called by `Dashboard.jsx`, `Predictions.jsx`, `WellnessTips.jsx`.
- How output is used: persona-specific recommendations and labels.

### 3.5 Relapse Risk Artifact
- Intended problem: relapse/doomscroll risk prediction.
- Current output: static `{risk: 0.85, top_features: [...]}` from `ai_service.predict_relapse()`.
- Endpoint: `GET /api/predictions/relapse-risk`.
- Frontend usage: `getRelapseRisk()` in `WellnessTips.jsx`.
- Important finding: persisted `relapse_model.pkl` is loaded, but not actually used to compute live predictions.

### 3.6 Anomaly Detector (Runtime)
- Problem solved: detect unusual `time_spent` values.
- Output: boolean `is_anomaly`, signed score.
- Endpoint: `POST /api/anomaly`.
- Frontend usage: `checkAnomaly()` called by `Dashboard.jsx`.
- Important finding: model is retrained from CSV at startup, not versioned/persisted.

## 4. Training Data Analysis

Training script: `train_models.py`

### 4.1 Dataset: `data/dummy_data.csv`
- Rows: 1000
- Columns: 12
- Key columns: `age`, `gender`, `time_spent`, `platform`, `interests`, `location`, `demographics`, `profession`, `income`, `indebt`, `isHomeOwner`, `Owns_Car`
- Target construction: `usage_category` derived from `time_spent` thresholds.
- Used for:
  - Usage classifier training.
  - Segmentation features.
  - Runtime anomaly detector fitting.

### 4.2 Dataset: `data/smmh.csv`
- Rows: 481
- Columns: 21
- Survey-style columns with long names (questions 1-20 + timestamp).
- Target construction:
  - `mental_health_risk_score` = mean of 5 Likert columns.
  - `mental_health_risk` = quantile bins (`qcut`) into `Low/Medium/High`.
- Used for mental health classifier.

### 4.3 Dataset: `data/StudentPerformanceFactors.csv`
- Rows: 6607
- Columns: 20
- Target: `Exam_Score`
- Used for productivity regressor.

## 5. Feature Engineering

### 5.1 Usage Classifier Features
- Categorical encoding: `LabelEncoder` on `gender`, `platform`, `interests`, `location`, `demographics`, `profession`.
- Scaling: `StandardScaler` on `age`, `income` -> `age_scaled`, `income_scaled`.
- Engineered feature: `platform_risk_score` from platform name.
- Leakage fix explicitly applied: `time_spent` removed from training feature set for classifier.
- Final feature count: 12.

### 5.2 Mental Health Features
- Drop `Timestamp`.
- Map usage text bucket to numeric `usage_hours`.
- Coerce Likert and other survey fields to numeric; fill missing with medians.
- Add numeric `age`.
- Final feature count: 14.

### 5.3 Productivity Features
- Fill numeric nulls with median and categorical nulls with mode.
- Encode all categorical columns with `LabelEncoder` (saved in `encoders.pkl` as `student_*`).
- Use all numeric columns except `Exam_Score` as features.
- Final feature count: 19.

### 5.4 Segmentation Features
- Input features: `time_spent`, `age`, `income`, `platform_risk_score`.
- Standardized with `StandardScaler` (`models/scaler.pkl`).

## 6. Algorithms Used

### 6.1 Final Serialized Algorithms (Verified From Artifacts)
- `usage_classifier.pkl`: `RandomForestClassifier`
  - Key params: `n_estimators=200`, `max_depth=None`, `random_state=42`
- `mental_health_classifier.pkl`: `GradientBoostingClassifier`
  - Key params: `n_estimators=200`, `learning_rate=0.1`, `max_depth=3`, `random_state=42`
- `productivity_regressor.pkl`: `Ridge`
  - Key params: `alpha=10.0`
- `user_segmentation.pkl`: `KMeans`
  - Key params: `n_clusters=5`, `n_init=10`, `random_state=42`

### 6.2 Candidate Algorithms Trained During Model Selection
- Classification candidates: RandomForest, XGBoost, GradientBoosting, LogisticRegression.
- Regression candidates: RandomForestRegressor, XGBRegressor, Ridge.
- Segmentation: KMeans with k in {3,4,5}, choose best silhouette.
- Extra balancing for Model A: SMOTE branch when baseline weighted F1 < 0.80.

### 6.3 Training Configuration
- Splits: `train_test_split(..., test_size=0.2, random_state=42)`.
- Stratification: enabled for classifiers.
- Hyperparameter tuning: `GridSearchCV` (`cv=5`, weighted F1 for classifiers, R2 for regressor, `n_jobs=-1`).

## 7. Prediction Pipelines

### 7.1 Usage Classifier Pipeline
Frontend (`Dashboard.jsx`) -> `predictUsageCategory()` -> `POST /api/predict/usage` -> `inference_service.usage_clf.predict/predict_proba` -> label decode via `encoders['usage_category']` -> JSON response.

### 7.2 Mental Health Pipeline
Frontend (`Dashboard.jsx`, `Predictions.jsx`, `WellnessTips.jsx`) -> `getMentalHealthRisk()` -> `POST /api/predict/mental_health` -> `inference_service.mental_clf.predict/predict_proba` -> decode via `encoders['mental_health_risk']`.

### 7.3 Segmentation Pipeline
Frontend -> `getUserCluster()` -> `POST /api/user/segment` -> scale using `models/scaler.pkl` -> `KMeans.predict` -> persona via `persona_map.json`.

### 7.4 Productivity Pipeline
Frontend -> `predictProductivity()` -> `POST /api/predict/productivity` -> `inference_service.productivity_reg.predict` -> normalized productivity output.

### 7.5 Relapse Pipeline (Current)
Frontend (`WellnessTips.jsx`) -> `getRelapseRisk()` -> `GET /api/predictions/relapse-risk` -> `ai_service.predict_relapse(features_json)` -> static response (does not pass computed feature vector into model inference).

### 7.6 Anomaly Pipeline
Frontend (`Dashboard.jsx`) -> `checkAnomaly(timeSpent)` -> `POST /api/anomaly` -> startup-trained `IsolationForest.predict([[time_spent]])`.

## 8. Model Outputs (Input/Output Meaning)

Representative runtime calls were executed via Flask test client.

### 8.1 Usage Classifier Example
- Input example:
  - `age_scaled=0.5`, `income_scaled=0.3`, encoded categorical fields, `platform_risk_score=3`
- Output example:
  - `prediction: "Healthy"`, `confidence: 0.405`, `model_used: "RandomForest"`
- Meaning:
  - User predicted in low-usage-risk class with moderate confidence.

### 8.2 Mental Health Classifier Example
- Input example:
  - Likert/self-report values plus `avg_daily_usage=5.2`, `age=24`
- Output example:
  - `prediction: "Medium"`, `confidence: 0.992`, `risk_score: 99`
- Meaning:
  - Model strongly favors medium mental health risk class for provided survey profile.

### 8.3 Segmentation Example
- Input example:
  - `time_spent=6.3`, `age=24`, `income=35000`, `platform_risk_score=3`
- Output example:
  - `cluster_id: 0`, `persona: "Weekend Binger"`, `risk: "Medium"`
- Meaning:
  - User behavior mapped to a predefined persona cluster used for recommendation strategy.

### 8.4 Productivity Regressor Example
- Input example:
  - student/lifestyle encoded fields, `hours_studied=12`, `attendance=85`, etc.
- Output example:
  - `predicted_exam_score: 65.3`, `productivity_score: 0.65`, `model_used: "Ridge+GridSearch"`
- Meaning:
  - Predicted exam score is used as a productivity proxy (scaled to 0-1).

### 8.5 Relapse Endpoint Example
- Input style:
  - endpoint receives user id (query param), internally builds minimal feature JSON.
- Output example:
  - `risk: 0.85`, `top_features: ["Late night (pm)", ...]`
- Meaning:
  - Currently static, not personalized model scoring.

### 8.6 Anomaly Endpoint Example
- Input example:
  - `time_spent=9.0`
- Output example:
  - `is_anomaly: false`, `score: 1`
- Meaning:
  - Value considered normal by startup-fitted one-feature detector.

## 9. Model Performance

### 9.1 Available Metrics (Persisted)
From `models/model_report.json`:
- Usage classifier: weighted F1 = 0.3654, accuracy = 0.3650
- Mental health classifier: weighted F1 = 0.9071, accuracy = 0.9072
- Productivity regressor: R2 = 0.6888, RMSE = 2.10
- Segmentation: silhouette = 0.2185, k = 5

### 9.2 Metrics Missing / Not Persisted
- Precision, recall, per-class metrics are printed in training but not stored as artifacts.
- Confusion matrices are printed during training only, not exported.
- No explicit holdout validation artifact beyond train/test split + CV search.
- No calibration analysis, drift checks, or fairness diagnostics.
- Relapse model has no real evaluation; currently static output path.
- Anomaly detector has no persisted evaluation metrics.

## 10. Real Data vs Mock Data Usage

### 10.1 Backend Data Sources
- Real data paths exist (SQLite logs and JSON files), especially for analytics and usage endpoints.
- ML prediction endpoints accept payloads from frontend and run real model inference.

### 10.2 Frontend Mock Coupling Findings
- Environment file `digiwell/.env` sets `VITE_USE_MOCK=false`.
- Even with mock mode disabled, multiple pages still send many hardcoded/mock-derived fields:
  - `Dashboard.jsx`, `Predictions.jsx`, `WellnessTips.jsx` use `currentUser`, `mockMental*`, `mockProductivity` for several model inputs.
- Practical impact:
  - Predictions are often computed by real backend models but with partially synthetic feature values.
- Specific fallback behavior:
  - `getNextHourPrediction()` always returns mock data; no backend LSTM endpoint exists.
  - Several API methods return mock defaults on request failure.

## 11. Unused / Broken / Partially Implemented Models

### 11.1 Relapse Model Is Partially Implemented
- `models/relapse_model.pkl` is loaded in `ai_service.py`.
- `predict_relapse()` checks `RELAPSE_MODEL` but does not extract/use features to call the model for live scoring.
- Returned risk and top features are static constants.
- Conclusion: artifact is present and loaded, but effective inference path is mock/stub.

### 11.2 Next-Hour Prediction Model Is Missing
- Frontend note in `digiwell/src/api/digiwell.js`: "No LSTM endpoint exists yet - return mock data as fallback".
- Conclusion: feature is UI-backed by static mock data, no deployed model.

### 11.3 Anomaly Detector Is Ephemeral
- IsolationForest retrained from `data/dummy_data.csv` at each startup.
- No versioned artifact, no reproducible training pipeline, no persisted metrics.
- Conclusion: operational but weakly governed model lifecycle.

## 11. Architecture Diagram

```text
Data Sources
  |- SQLite usage logs (app_usage_logs, usage_logs, hourly_logs)
  |- CSV datasets for training (dummy_data, smmh, StudentPerformanceFactors)
  |- JSON metadata (persona_map, model_report)

Offline Training (train_models.py)
  -> preprocessing/encoding/scaling
  -> model selection + GridSearchCV
  -> save artifacts to models/*.pkl + JSON reports

Runtime Inference (Flask app.py)
  -> InferenceService loads .pkl models + encoders/scaler + reports
  -> API endpoints (/api/predict/*, /api/user/segment, /api/anomaly)
  -> frontend consumes outputs in Dashboard/Predictions/WellnessTips

Relapse Path (current state)
  -> ai_service loads relapse_model.pkl
  -> predict_relapse returns static response (stub behavior)
```

## 12. Recommendations For Improvement

1. Replace relapse stub with true feature extraction + model inference.
2. Remove frontend hardcoded input surrogates and source all model features from real telemetry/user profile data.
3. Persist preprocessing pipeline objects per model (or use sklearn Pipeline) to prevent train/serve feature mismatch.
4. Export full evaluation bundle per model: precision/recall/F1 per class, confusion matrix, and CV summary.
5. Add model cards/versioning metadata (dataset hash, train timestamp, hyperparameters, feature schema).
6. Improve usage classifier quality (F1=0.3654 is weak) with feature redesign and better labels.
7. Reassess segmentation quality (silhouette=0.2185 indicates weak cluster separation).
8. Persist anomaly detector artifact and establish evaluation protocol for anomaly thresholds.
9. Add integration tests for all core prediction endpoints (`usage`, `mental_health`, `productivity`, `segment`, `relapse`) with stable fixtures.
10. Build/ship real next-hour forecasting model endpoint or remove mock-only UI dependency.
