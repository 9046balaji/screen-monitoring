@echo off
echo Starting DigiWell...

echo [1/3] Starting app tracker...
start "DigiWell Tracker" cmd /k "cd agent && python tracker.py"

echo [2/3] Starting Flask backend...
start "DigiWell Backend" cmd /k "python app.py"

echo [3/3] Starting React frontend...
start "DigiWell Frontend" cmd /k "cd digiwell && npm run dev"

echo.
echo DigiWell is running!
echo   Tracker: background (check tracker window)
echo   Backend: http://localhost:5000
echo   Frontend: http://localhost:5173
pause
