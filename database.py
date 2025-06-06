import logging
import sqlite3

def init_db():
    conn = sqlite3.connect("vatsim_bot.db")
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id INTEGER,
        icao TEXT,
        primary_threshold INTEGER,
        staff_up_threshold INTEGER DEFAULT NULL,
        cooldown INTEGER,
        alert_preference TEXT DEFAULT 'channel',
        support_threshold INTEGER DEFAULT NULL,
        PRIMARY KEY (user_id, icao)
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_observe_hours (
            user_id INTEGER PRIMARY KEY,
            start_time TEXT,
            end_time TEXT,
            FOREIGN KEY (user_id) REFERENCES user_training(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS temp_observe (
            user_id INTEGER PRIMARY KEY,
            start_date_time TEXT,
            end_date_time TEXT,
            FOREIGN KEY (user_id) REFERENCES user_training(user_id)
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_opt_outs (
            user_id INTEGER,
            icao TEXT,
            position TEXT,
            PRIMARY KEY (user_id, icao, position),
            FOREIGN KEY (user_id) REFERENCES user_ratings(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_cooldowns (
            user_id INTEGER,
            icao TEXT,
            last_alert TIMESTAMP,
            PRIMARY KEY (user_id, icao),
            FOREIGN KEY (user_id) REFERENCES user_ratings(user_id)
        )
    """)

    
    conn.commit()
    conn.close()


    conn = sqlite3.connect("airports.db")
    cursor = conn.cursor()
    
    # Ensure the airports table exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS airports (
        icao TEXT PRIMARY KEY,
        iata TEXT,
        latitude REAL,
        longitude REAL,
        abbreviations TEXT
    )
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    logging.info("Databases initialized.")
