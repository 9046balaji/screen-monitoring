import sqlite3
import os
import sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'digiwell.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

MIGRATIONS = [
    {
        "name": "migrate_001_create_commitments_and_focus_sessions",
        "sql": """
        CREATE TABLE IF NOT EXISTS commitments (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          challenge_id TEXT,
          title TEXT NOT NULL,
          description TEXT,
          start_ts DATETIME NOT NULL,
          end_ts DATETIME,
          expected_duration_minutes INT,
          auto_start_focus BOOLEAN DEFAULT 0,
          reminder_interval_minutes INT,
          status TEXT DEFAULT 'active',
          metadata JSON,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS focus_sessions (
          id TEXT PRIMARY KEY,
          commitment_id TEXT,
          start_ts DATETIME,
          duration_minutes INT,
          status TEXT DEFAULT 'scheduled'
        );
        """
    },
    {
        "name": "migrate_002_add_ai_fields_mood_journal",
        "sql": """
        CREATE TABLE IF NOT EXISTS mood_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT NOT NULL,
            entry TEXT NOT NULL,
            mood_score INTEGER NOT NULL,
            polarity REAL
        );
        ALTER TABLE mood_journal ADD COLUMN ai_primary_emotion TEXT;
        ALTER TABLE mood_journal ADD COLUMN ai_distortion TEXT;
        ALTER TABLE mood_journal ADD COLUMN ai_reframe TEXT;
        ALTER TABLE mood_journal ADD COLUMN ai_microtask JSON;
        """
    },
    {
        "name": "migrate_003_create_relapse_predictions",
        "sql": """
        CREATE TABLE IF NOT EXISTS relapse_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            risk REAL,
            features JSON
        );
        """
    },
    {
        "name": "migrate_004_create_therapy_sessions",
        "sql": """
        CREATE TABLE IF NOT EXISTS therapy_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            messages JSON,
            outcome JSON
        );
        """
    },
    {
        "name": "migrate_005_create_screen_usage",
        "sql": """
        CREATE TABLE IF NOT EXISTS screen_usage (
            id TEXT PRIMARY KEY,
            timestamp DATETIME,
            app_name TEXT,
            window_title TEXT,
            cpu_usage FLOAT,
            memory_usage FLOAT,
            duration_seconds INTEGER,
            category TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_screen_usage_timestamp ON screen_usage(timestamp);
        CREATE INDEX IF NOT EXISTS idx_screen_usage_app_name ON screen_usage(app_name);
        """
    },
    {
        "name": "migrate_006_create_weekly_timetable",
        "sql": """
        CREATE TABLE IF NOT EXISTS weekly_timetable (
          id TEXT PRIMARY KEY,
          user_id TEXT DEFAULT 'local',
          name TEXT,
          timezone TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS weekly_timetable_slots (
          id TEXT PRIMARY KEY,
          timetable_id TEXT REFERENCES weekly_timetable(id),
          day_of_week INTEGER,
          start_time TEXT,
          end_time TEXT,
          title TEXT,
          description TEXT,
          category TEXT,
          focus_mode BOOLEAN DEFAULT 0,
          recurrence JSON,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    },
    {
        "name": "migrate_007_create_daily_tasks_and_logs",
        "sql": """
        CREATE TABLE IF NOT EXISTS daily_tasks (
          id TEXT PRIMARY KEY,
          user_id TEXT DEFAULT 'local',
          date DATE NOT NULL,
          slot_id TEXT,
          planned_start DATETIME,
          planned_end DATETIME,
          title TEXT,
          description TEXT,
          category TEXT,
          status TEXT DEFAULT 'scheduled',
          actual_start DATETIME,
          actual_end DATETIME,
          duration_planned_minutes INTEGER,
          duration_actual_minutes INTEGER,
          metadata JSON,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_daily_tasks_date ON daily_tasks(date);
        """
    },
    {
        "name": "migrate_008_create_adherence_reports",
        "sql": """
        CREATE TABLE IF NOT EXISTS adherence_reports (
          id TEXT PRIMARY KEY,
          user_id TEXT DEFAULT 'local',
          date DATE NOT NULL,
          planned_total_minutes INTEGER,
          actual_total_minutes INTEGER,
          completed_tasks INTEGER,
          scheduled_tasks INTEGER,
          adherence_score FLOAT,
          details JSON,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        },
        {
                "name": "migrate_009_create_weekly_tasks_and_daily_status",
                "sql": """
                CREATE TABLE IF NOT EXISTS weekly_tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT DEFAULT 'local',
                    day_of_week INTEGER NOT NULL,
                    task_title TEXT NOT NULL,
                    task_description TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    category TEXT DEFAULT 'Work',
                    priority TEXT DEFAULT 'Medium',
                    sort_order INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS daily_task_status (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_task_status_task_date
                    ON daily_task_status(task_id, date);
                CREATE INDEX IF NOT EXISTS idx_weekly_tasks_day
                    ON weekly_tasks(day_of_week);
                """
    },
    {
        "name": "migrate_010_create_app_usage_analytics_tables",
        "sql": """
        CREATE TABLE IF NOT EXISTS app_usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'local',
            app_name TEXT NOT NULL,
            window_title TEXT,
            process_name TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            date TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_app_usage_logs_user_date
            ON app_usage_logs(user_id, date);

        CREATE INDEX IF NOT EXISTS idx_app_usage_logs_app
            ON app_usage_logs(app_name);

        CREATE TABLE IF NOT EXISTS hourly_activity_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL DEFAULT 'local',
            date TEXT NOT NULL,
            hour INTEGER NOT NULL,
            activity_level INTEGER NOT NULL,
            UNIQUE(user_id, date, hour)
        );

        CREATE INDEX IF NOT EXISTS idx_hourly_activity_user_date
            ON hourly_activity_table(user_id, date);
        """
    }
]

def apply_migrations():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create migrations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    for migration in MIGRATIONS:
        # Check if applied
        c.execute('SELECT 1 FROM schema_migrations WHERE name = ?', (migration['name'],))
        if not c.fetchone():
            print(f"Applying migration: {migration['name']}")
            try:
                # Some statements like ALTER TABLE cannot be batched easily in standard executescript safely if ignoring errors
                # so we might do them individually or wrap them
                for statement in migration['sql'].split(';'):
                    statement = statement.strip()
                    if statement:
                        try:
                            c.execute(statement)
                        except sqlite3.OperationalError as e:
                            # Ignore "duplicate column name" if alter table fails on re-run
                            if "duplicate column name" not in str(e).lower():
                                raise e

                c.execute('INSERT INTO schema_migrations (name) VALUES (?)', (migration['name'],))
                conn.commit()
                print(f"Success: {migration['name']}")
            except Exception as e:
                conn.rollback()
                print(f"Failed to apply {migration['name']}: {e}")
                sys.exit(1)
        else:
            print(f"Already applied: {migration['name']}")
            
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "apply":
        apply_migrations()
    else:
        print("Usage: python -m database.migrations apply")
