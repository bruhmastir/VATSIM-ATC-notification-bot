import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("AVIATIONSTACK_API_KEY")  # Replace with your AviationStack API key 

import sqlite3
import json
import requests

def get_abbr(icao):
    conn = sqlite3.connect("airports.db")
    cursor = conn.cursor()
    cursor.execute("SELECT abbreviations FROM airports WHERE icao = ?", (icao,))
    result = cursor.fetchone()
    
    
    if result and result[0]:
        print(result[0])
        conn.close()
        return tuple(result[0].split(","))  # Convert comma-separated string back to tuple
    cursor.execute("SELECT iata FROM airports WHERE icao = ?", (icao,))
    result = cursor.fetchone()
    conn.close()
    return ()
    # return (icao[:2], result)  # Return empty tuple if no abbreviations exist

# Function to fetch and store a single airport's data from AirportDB
def fetch_and_store_airport(icao):
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
    
    url = f"https://airportdb.io/api/v1/airport/{icao}?apiToken={API_KEY}"
    # headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}  # Ensure proper request format
    
    try:
        response = requests.get(url) #, headers=headers)
        print(response)
        response.raise_for_status()  # Raise error for bad status codes
        data = response.json()
        # print(data)
        
        if "latitude_deg" in data and "longitude_deg" in data:
            cursor.execute("INSERT OR IGNORE INTO airports (icao, iata, latitude, longitude, abbreviations) VALUES (?, ?, ?, ?, ?)",
                           (icao, data["iata_code"], float(data["latitude_deg"]), float(data["longitude_deg"]), f"{icao[:2]},{data["iata_code"]}"))
            conn.commit()
            print(f"Stored {icao} airport in the database.")
    except requests.exceptions.HTTPError as e:
        print(f"API error: HTTP {e.response.status_code} - {e.response.reason}")
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except json.JSONDecodeError:
        print("Error: Unable to decode JSON. Response might not be valid JSON.")
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    conn.close()

# Function to get coordinates from the database, fetching from API if not found
def get_airport_coords(icao):
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
    cursor.execute("SELECT latitude, longitude FROM airports WHERE icao = ?", (icao,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result  # Return existing coordinates
    
    # If not in DB, fetch and store airport data
    print(f"Airport {icao} not found in DB, fetching from API...")
    fetch_and_store_airport(icao)
    
    # Try fetching again after updating the DB
    cursor.execute("SELECT latitude, longitude FROM airports WHERE icao = ?", (icao,))
    result = cursor.fetchone()
    print(result)
    conn.close()
    return result if result else None