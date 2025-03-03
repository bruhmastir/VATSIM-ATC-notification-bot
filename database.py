import sqlite3

def init_db():
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER,
        icao TEXT,
        primary_threshold INTEGER,
        tertiary_threshold INTEGER DEFAULT NULL,
        cooldown INTEGER,
        alert_preference TEXT DEFAULT 'channel',
        support_threshold INTEGER DEFAULT NULL,
        PRIMARY KEY (user_id, icao)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_quiet_hours (
        user_id INTEGER PRIMARY KEY,
        start_time TEXT,
        end_time TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_ratings (
        user_id INTEGER PRIMARY KEY,
        atc_rating TEXT CHECK(atc_rating IN ('S1', 'S2', 'S3', 'C1'))
    )
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
