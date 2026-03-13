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
