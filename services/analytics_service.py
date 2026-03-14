import json
import os
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from database.database import get_db_connection


DEFAULT_CATEGORY_MAP = {
    "chrome": "Browser",
    "msedge": "Browser",
    "firefox": "Browser",
    "code": "Development",
    "code - insiders": "Development",
    "youtube": "Entertainment",
    "spotify": "Entertainment",
    "netflix": "Entertainment",
    "instagram": "Social",
    "whatsapp": "Social",
    "discord": "Social",
    "teams": "Productivity",
    "slack": "Productivity",
    "notion": "Productivity",
    "word": "Office",
    "excel": "Office",
    "powerpoint": "Office",
}

PRODUCTIVE_CATEGORIES = {"development", "productivity", "office", "education", "work", "utility"}
DISTRACTING_CATEGORIES = {"entertainment", "social", "social media", "games", "video"}


class AnalyticsService:
    def __init__(self, categories_path: str = None):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.categories_path = categories_path or os.path.join(root, "data", "app_categories.json")

    def _load_category_map(self) -> Dict[str, str]:
        category_map = dict(DEFAULT_CATEGORY_MAP)
        if os.path.exists(self.categories_path):
            try:
                with open(self.categories_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k, v in data.items():
                            category_map[str(k).lower()] = str(v)
            except Exception:
                pass
        return category_map

    def _normalize_category(self, app_name: str) -> str:
        app_name = (app_name or "").lower().replace(".exe", "")
        category_map = self._load_category_map()
        if app_name in category_map:
            return str(category_map[app_name]).title()

        for key, val in category_map.items():
            if key in app_name or app_name in key:
                return str(val).title()

        return "Other"

    def get_daily_usage(self, user_id: str = "local", target_date: str = None) -> Dict[str, Any]:
        date_str = target_date or datetime.now().strftime("%Y-%m-%d")
        conn = get_db_connection()
        c = conn.cursor()

        c.execute(
            """
            SELECT app_name, SUM(duration_minutes) as total_minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date = ?
            GROUP BY app_name
            ORDER BY total_minutes DESC
            """,
            (user_id, date_str),
        )
        app_rows = c.fetchall()

        apps = []
        total_minutes = 0
        productive_minutes = 0
        distracting_minutes = 0

        for row in app_rows:
            minutes = int(row["total_minutes"] or 0)
            app_name = row["app_name"]
            category = self._normalize_category(app_name)
            cat_norm = category.lower()

            total_minutes += minutes
            if cat_norm in PRODUCTIVE_CATEGORIES:
                productive_minutes += minutes
            if cat_norm in DISTRACTING_CATEGORIES:
                distracting_minutes += minutes

            apps.append(
                {
                    "app": app_name,
                    "minutes": minutes,
                    "hours": round(minutes / 60.0, 2),
                    "category": category,
                }
            )

        summary = {
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60.0, 2),
            "productive_minutes": productive_minutes,
            "distracting_minutes": distracting_minutes,
            "productivity_ratio": round((productive_minutes / total_minutes), 3) if total_minutes else 0.0,
            "top_apps": apps[:5],
        }

        conn.close()
        return {
            "date": date_str,
            "apps": apps,
            "summary": summary,
        }

    def get_weekly_usage(self, user_id: str = "local", days: int = 7) -> Dict[str, Any]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT date, app_name, SUM(duration_minutes) as minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date, app_name
            ORDER BY date ASC, minutes DESC
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        rows = c.fetchall()
        conn.close()

        per_day_apps: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        per_day_total: Dict[str, int] = defaultdict(int)

        for row in rows:
            d = row["date"]
            app_name = row["app_name"]
            minutes = int(row["minutes"] or 0)
            per_day_total[d] += minutes
            per_day_apps[d].append(
                {
                    "app": app_name,
                    "minutes": minutes,
                    "category": self._normalize_category(app_name),
                }
            )

        timeline = []
        by_day = []
        cursor = start_date
        while cursor <= end_date:
            d = cursor.isoformat()
            label = cursor.strftime("%a")
            total_min = per_day_total.get(d, 0)
            timeline.append({"date": d, "day": label, "minutes": total_min, "hours": round(total_min / 60.0, 2)})
            by_day.append(
                {
                    "date": d,
                    "day": label,
                    "total_minutes": total_min,
                    "apps": sorted(per_day_apps.get(d, []), key=lambda x: x["minutes"], reverse=True),
                }
            )
            cursor += timedelta(days=1)

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timeline": timeline,
            "by_day": by_day,
        }

    def get_heatmap(self, user_id: str = "local", days: int = 7) -> List[Dict[str, Any]]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT date, hour, SUM(activity_level) as total_activity
            FROM hourly_activity_table
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY date, hour
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        rows = c.fetchall()
        conn.close()

        intensity_map = {}
        for row in rows:
            key = (row["date"], int(row["hour"]))
            intensity_map[key] = int(row["total_activity"] or 0)

        cells = []
        cursor = start_date
        while cursor <= end_date:
            date_label = cursor.isoformat()
            day = cursor.strftime("%a")
            for hour in range(24):
                val = intensity_map.get((date_label, hour), 0)
                if val >= 20:
                    risk = "Very High"
                elif val >= 12:
                    risk = "High"
                elif val >= 6:
                    risk = "Medium"
                elif val > 0:
                    risk = "Low"
                else:
                    risk = "None"

                cells.append(
                    {
                        "date": date_label,
                        "day": day,
                        "hour": hour,
                        "value": val,
                        "riskLevel": risk,
                    }
                )
            cursor += timedelta(days=1)

        return cells

    def get_top_apps(self, user_id: str = "local", days: int = 7, limit: int = 5) -> List[Dict[str, Any]]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT app_name, SUM(duration_minutes) as total_minutes
            FROM app_usage_logs
            WHERE user_id = ? AND date BETWEEN ? AND ?
            GROUP BY app_name
            ORDER BY total_minutes DESC
            LIMIT ?
            """,
            (user_id, start_date.isoformat(), end_date.isoformat(), limit),
        )
        rows = c.fetchall()
        conn.close()

        ranked = []
        for idx, row in enumerate(rows, start=1):
            app_name = row["app_name"]
            minutes = int(row["total_minutes"] or 0)
            ranked.append(
                {
                    "rank": idx,
                    "app": app_name,
                    "minutes": minutes,
                    "hours": round(minutes / 60.0, 2),
                    "category": self._normalize_category(app_name),
                }
            )
        return ranked

    def _find_peak_productive_hours(self, user_id: str = "local", days: int = 7) -> List[int]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            """
            SELECT l.date, l.app_name, l.duration_minutes, CAST(strftime('%H', l.start_time) AS INTEGER) as hour
            FROM app_usage_logs l
            WHERE l.user_id = ? AND l.date BETWEEN ? AND ?
            """,
            (user_id, start_date.isoformat(), end_date.isoformat()),
        )
        rows = c.fetchall()
        conn.close()

        hour_productive = defaultdict(int)
        for row in rows:
            category = self._normalize_category(row["app_name"]).lower()
            if category in PRODUCTIVE_CATEGORIES:
                hour = row["hour"] if row["hour"] is not None else 0
                hour_productive[int(hour)] += int(row["duration_minutes"] or 0)

        ranked = sorted(hour_productive.items(), key=lambda x: x[1], reverse=True)
        return [h for h, _ in ranked[:3]]

    def get_ai_insights(self, user_id: str = "local") -> Dict[str, Any]:
        daily = self.get_daily_usage(user_id=user_id)
        weekly = self.get_weekly_usage(user_id=user_id)
        top_apps = self.get_top_apps(user_id=user_id)

        total_minutes = daily["summary"]["total_minutes"]
        distracting = daily["summary"]["distracting_minutes"]
        productive = daily["summary"]["productive_minutes"]

        entertainment_pct = round((distracting / total_minutes) * 100, 1) if total_minutes else 0.0
        productive_pct = round((productive / total_minutes) * 100, 1) if total_minutes else 0.0

        peak_hours = self._find_peak_productive_hours(user_id=user_id)
        peak_hours_text = "-"
        if peak_hours:
            peak_hours_text = ", ".join([f"{h:02d}:00" for h in peak_hours])

        youtube_minutes = 0
        social_late_minutes = 0
        late_cutoff = 22

        conn = get_db_connection()
        c = conn.cursor()

        today = datetime.now().strftime("%Y-%m-%d")
        c.execute(
            """
            SELECT SUM(duration_minutes) as mins
            FROM app_usage_logs
            WHERE user_id = ? AND date = ? AND lower(app_name) LIKE '%youtube%'
            """,
            (user_id, today),
        )
        row = c.fetchone()
        youtube_minutes = int((row["mins"] if row and row["mins"] else 0))

        c.execute(
            """
            SELECT app_name, duration_minutes, CAST(strftime('%H', start_time) AS INTEGER) as hour
            FROM app_usage_logs
            WHERE user_id = ? AND date = ?
            """,
            (user_id, today),
        )
        rows = c.fetchall()
        for r in rows:
            hour = int(r["hour"] or 0)
            category = self._normalize_category(r["app_name"]).lower()
            if hour >= late_cutoff and category in DISTRACTING_CATEGORIES:
                social_late_minutes += int(r["duration_minutes"] or 0)

        conn.close()

        insights = [
            f"You spend {entertainment_pct}% of your time on entertainment/social apps today.",
            f"Your most productive hours are around {peak_hours_text}.",
            f"You spent {youtube_minutes} minutes on YouTube today.",
            f"You used social/entertainment apps for {social_late_minutes} minutes after 10PM.",
            f"Your productive share is {productive_pct}% today.",
        ]

        return {
            "insights": insights,
            "top_apps": top_apps,
            "weekly": weekly["timeline"],
        }

    def get_battery_usage_summary(self) -> Dict[str, Any]:
        report_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "battery-report.html")
        cmd = ["powercfg", "/batteryreport", "/output", report_path]

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        except Exception as e:
            return {
                "available": False,
                "error": f"batteryreport not available: {e}",
            }

        if not os.path.exists(report_path):
            return {"available": False, "error": "battery report file was not generated"}

        try:
            with open(report_path, "r", encoding="utf-8", errors="ignore") as f:
                html = f.read()
        except Exception as e:
            return {"available": False, "error": f"failed to read report: {e}"}

        def _extract_time_value(label: str) -> str:
            pattern = rf"{re.escape(label)}</span></td><td><span class=\"value\">([^<]+)"
            m = re.search(pattern, html, flags=re.IGNORECASE)
            return m.group(1).strip() if m else "N/A"

        screen_on = _extract_time_value("SCREEN ON")
        active = _extract_time_value("ACTIVE")
        connected_standby = _extract_time_value("CONNECTED STANDBY")

        # Best-effort extraction for app/device drain rows.
        app_matches = re.findall(r"<tr><td>([^<]+)</td><td><span class=\"value\">([^<]+)</span></td>", html)
        top_energy = []
        for name, value in app_matches[:10]:
            name = name.strip()
            value = value.strip()
            if name and value and name.lower() not in {"active", "screen on", "connected standby"}:
                top_energy.append({"name": name, "value": value})

        return {
            "available": True,
            "report_path": report_path,
            "screen_on_time": screen_on,
            "system_active_time": active,
            "connected_standby": connected_standby,
            "top_energy_consumers": top_energy[:5],
        }
