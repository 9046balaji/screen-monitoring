# DigiWell Planner / Weekly Timetable Demo

This document outlines the demo flow for the newly implemented Weekly Timetable to Daily Tasks features in the DigiWell application.

## How to setup for Demo
Ensure you have run the database migrations and started the backend and frontend:

```bash
# DB migrations
python -m database.migrations apply

# Backend
python app.py

# Frontend
cd digiwell
npm install
npm run dev

# Agent (optional, in a new terminal)
python agent/enforcer.py
```

## Demo Flow

### 1. Create a Weekly Timetable
- Open the application and navigate to `Timetable` on the sidebar.
- Click `New Timetable`.
- Click `Add Slot` to block off time. For example, add a "Deep Work" slot on today's day of the week, with `Auto-Focus Mode` enabled.

### 2. Generate Daily Tasks
- On the Timetable page, click `Generate Today`. You will be redirected to the `Daily Plan`.

### 3. Start a Task with Auto-Focus
- Find your generated "Deep Work" task.
- Click `Start Task`.
- Look at the terminal running `agent/enforcer.py`. You should see the focus session get polled and enforced automatically! (Or wait a moment for the background worker to catch it).
- The task status now shows as `running`. 

### 4. Complete Tasks and See Suggestions
- Complete the running task, and maybe skip another task to simulate uncompleted work.
- The `Daily Adherence` score will immediately calculate based on your real performance vs planned goals.
- If your completion rate is low, watch the `Smart Suggestion` rule-engine trigger, giving you actionable feedback!

### Extras
- To enable LLM powered empathetic suggestions, define `OPENAI_API_KEY` in your environment.
