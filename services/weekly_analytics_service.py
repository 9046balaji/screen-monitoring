import json
import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from database.database import get_db_connection


class WeeklyAnalyticsService:
    def __init__(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_categories_path = os.path.join(root, "config", "app_categories.json")
        self.data_categories_path = os.path.join(root, "data", "app_categories.json")

    def _load_category_map(self) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        for path in [self.config_categories_path, self.data_categories_path]:
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    for k, v in payload.items():
                        merged[str(k).lower()] = str(v)
            except Exception:
                continue
        return merged

    @staticmethod
    def _canonical_key(app_name: str) -> str:
        key = (app_name or "").lower().replace(".exe", "").strip()
        aliases = {
            "microsoft edge": "msedge",
            "edge": "msedge",
            "visual studio code": "code",
            "vs code": "code",
            "file explorer": "explorer",
        }
        return aliases.get(key, key)

    def _classify(self, app_name: str, category_map: Dict[str, str]) -> str:
        key = self._canonical_key(app_name)
        if key in category_map:
            return category_map[key].title()

        for mapped, category in category_map.items():
            if mapped in key or key in mapped:
                return category.title()

        return "Other"

    @staticmethod
    def _norm_app_name(app_name: str) -> str:
        raw = (app_name or "").strip()
        low = raw.lower().replace('.exe', '')

        aliases = {
            'code': 'VS Code',
            'code - insiders': 'VS Code Insiders',
            'msedge': 'Microsoft Edge',
            'chrome': 'Google Chrome',
            'firefox': 'Firefox',
            'explorer': 'File Explorer',
            'windowsterminal': 'Windows Terminal',
            'windowsterminal.exe': 'Windows Terminal',
            'taskmgr': 'Task Manager',
        }

        if low in aliases:
            return aliases[low]

        # Handle values like WhatsApp.Root while preserving human readability.
        if '.' in raw and raw.lower().endswith('.root'):
            raw = raw.split('.', 1)[0]

        return raw

    @staticmethod
    def _week_range(today: date = None) -> Dict[str, date]:
        end = today or datetime.now().date()
        start = end - timedelta(days=6)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=6)
        return {
            "start": start,
            "end": end,
            "prev_start": prev_start,
            "prev_end": prev_end,
        }

    def get_weekly_app_usage_report(self, user_id: str = "local") -> Dict[str, Any]:
        ranges = self._week_range()
        category_map = self._load_category_map()

        conn = get_db_connection()
        c = conn.cursor()

        # Previous week for week-over-week comparisons
        c.execute(
            """
            SELECT app_name, SUM(duration_minutes) AS total_minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY app_name
            ORDER BY total_minutes DESC
            """,
            (user_id, ranges["prev_start"].isoformat(), ranges["prev_end"].isoformat()),
        )
        prev_rows = c.fetchall()

        c.execute(
            """
            SELECT app_name, SUM(duration_minutes) AS total_minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY app_name
            ORDER BY total_minutes DESC
            """,
            (user_id, ranges["start"].isoformat(), ranges["end"].isoformat()),
        )
        app_rows = c.fetchall()

        # Per-day totals by source for daily series.
        c.execute(
            """
            SELECT date, SUM(duration_minutes) AS total_minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date
            ORDER BY date ASC
            """,
            (user_id, ranges["start"].isoformat(), ranges["end"].isoformat()),
        )
        day_rows = c.fetchall()

        conn.close()

        total_weekly = sum(float(r["total_minutes"] or 0) for r in app_rows)
        total_prev = sum(float(r["total_minutes"] or 0) for r in prev_rows)

        app_data: List[Dict[str, Any]] = []
        category_totals = defaultdict(int)

        for r in app_rows:
            app_name = self._norm_app_name(r["app_name"])
            minutes = int(round(float(r["total_minutes"] or 0)))
            if minutes <= 0:
                continue
            category = self._classify(app_name, category_map)
            category_totals[category] += minutes
            pct = round((minutes / total_weekly) * 100, 2) if total_weekly else 0.0
            app_data.append(
                {
                    "app": app_name,
                    "minutes": minutes,
                    "hours": round(minutes / 60.0, 2),
                    "percentage": pct,
                    "category": category,
                }
            )

        categories = []
        for category, minutes in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
            categories.append(
                {
                    "category": category,
                    "minutes": minutes,
                    "hours": round(minutes / 60.0, 2),
                    "percentage": round((minutes / total_weekly) * 100, 2) if total_weekly else 0.0,
                }
            )

        daily_map = {r["date"]: float(r["total_minutes"] or 0) for r in day_rows}
        daily_series = []
        cursor = ranges["start"]
        while cursor <= ranges["end"]:
            key = cursor.isoformat()
            day_total = daily_map.get(key, 0.0)
            daily_series.append(
                {
                    "date": key,
                    "day": cursor.strftime("%a"),
                    "minutes": int(round(day_total)),
                }
            )
            cursor += timedelta(days=1)

        avg_daily = round(total_weekly / 7.0, 2)
        top_apps = app_data[:5]
        primary_category = categories[0]["category"] if categories else "Other"
        primary_category_pct = categories[0]["percentage"] if categories else 0

        youtube_current = 0
        youtube_previous = 0
        for r in app_data:
            if "youtube" in (r["app"] or "").lower():
                youtube_current += int(r["minutes"] or 0)
        for r in prev_rows:
            if "youtube" in (r["app_name"] or "").lower():
                youtube_previous += int(round(float(r["total_minutes"] or 0)))

        youtube_delta_pct = 0.0
        if youtube_previous > 0:
            youtube_delta_pct = round(((youtube_current - youtube_previous) / youtube_previous) * 100, 1)

        # Best productivity window from current week.
        productive_labels = {"Development", "Work", "Study"}
        # For this summary we use a lightweight estimate from start_time hour in weekly logs.
        hour_bucket = defaultdict(int)
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT app_name, duration_minutes, CAST(strftime('%H', start_time) AS INTEGER) AS hour
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            """,
            (user_id, ranges["start"].isoformat(), ranges["end"].isoformat()),
        )
        for row in c.fetchall():
            app_name = row["app_name"]
            cat = self._classify(app_name, category_map)
            if cat in productive_labels:
                hour_bucket[int(row["hour"] or 0)] += int(row["duration_minutes"] or 0)

        conn.close()

        best_hours = sorted(hour_bucket.items(), key=lambda x: x[1], reverse=True)[:3]
        best_window = ", ".join([f"{h:02d}:00" for h, _ in best_hours]) if best_hours else "09:00, 10:00, 11:00"

        wow_pct = round(((total_weekly - total_prev) / total_prev) * 100, 1) if total_prev > 0 else 0.0

        insights = [
            f"You spent {round(total_weekly / 60.0, 2)} hours on your computer this week.",
            f"{primary_category} apps accounted for {primary_category_pct}% of your weekly usage.",
            f"YouTube usage changed by {youtube_delta_pct}% compared to last week.",
            f"You are most productive around {best_window}.",
            f"Week-over-week total screen time changed by {wow_pct}%.",
        ]

        return {
            "period": {
                "start_date": ranges["start"].isoformat(),
                "end_date": ranges["end"].isoformat(),
            },
            "total_screen_time": int(round(total_weekly)),
            "total_screen_time_hours": round(total_weekly / 60.0, 2),
            "average_daily_usage": avg_daily,
            "average_daily_usage_hours": round(avg_daily / 60.0, 2),
            "apps": app_data,
            "categories": categories,
            "top_apps": top_apps,
            "daily_series": daily_series,
            "insights": insights,
        }
