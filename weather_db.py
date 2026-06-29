"""
OpenWeatherMap → SQLite Project
--------------------------------
Fetches current weather for a list of cities and stores
results in a local SQLite database.

Usage:
    python weather_db.py                  # fetch & store weather
    python weather_db.py --query          # print stored records
    python weather_db.py --export         # export to CSV

Requirements:
    pip install requests
"""

import requests
import sqlite3
import csv
import argparse
from datetime import datetime

# ── Config ────────────────────────────────────────────────────
API_KEY  = "9e179a20d5b048eb0b205894d889e6b7"          # replace with your key
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
DB_FILE  = "weather.db"

CITIES = [
    "Nairobi", "Mombasa", "Kisumu",
    "London", "New York", "Tokyo", "Kisii"
]

# ── Database setup ─────────────────────────────────────────────
def init_db(conn):
    """Create the weather table if it doesn't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS weather (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            city        TEXT    NOT NULL,
            country     TEXT,
            temperature REAL,
            feels_like  REAL,
            temp_min    REAL,
            temp_max    REAL,
            humidity    INTEGER,
            pressure    INTEGER,
            wind_speed  REAL,
            wind_deg    INTEGER,
            description TEXT,
            visibility  INTEGER,
            cloudiness  INTEGER,
            sunrise     TEXT,
            sunset      TEXT,
            fetched_at  TEXT    NOT NULL
        )
    """)
    conn.commit()
    print("Database initialised → weather.db")


# ── API fetch ──────────────────────────────────────────────────
def fetch_weather(city):
    """Call OpenWeatherMap current weather endpoint."""
    params = {
        "q":     city,
        "appid": API_KEY,
        "units": "metric"       # Celsius; use 'imperial' for °F
    }
    response = requests.get(BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def parse_weather(data):
    """Extract the fields we care about from the API response."""
    main    = data.get("main", {})
    wind    = data.get("wind", {})
    clouds  = data.get("clouds", {})
    sys     = data.get("sys", {})
    weather = data.get("weather", [{}])[0]

    return {
        "city":        data.get("name"),
        "country":     sys.get("country"),
        "temperature": main.get("temp"),
        "feels_like":  main.get("feels_like"),
        "temp_min":    main.get("temp_min"),
        "temp_max":    main.get("temp_max"),
        "humidity":    main.get("humidity"),
        "pressure":    main.get("pressure"),
        "wind_speed":  wind.get("speed"),
        "wind_deg":    wind.get("deg"),
        "description": weather.get("description"),
        "visibility":  data.get("visibility"),
        "cloudiness":  clouds.get("all"),
        "sunrise":     datetime.utcfromtimestamp(sys.get("sunrise", 0)).strftime("%H:%M UTC"),
        "sunset":      datetime.utcfromtimestamp(sys.get("sunset",  0)).strftime("%H:%M UTC"),
        "fetched_at":  datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ── Database write ─────────────────────────────────────────────
def insert_weather(conn, record):
    """Insert one parsed weather record into the database."""
    conn.execute("""
        INSERT INTO weather (
            city, country, temperature, feels_like, temp_min, temp_max,
            humidity, pressure, wind_speed, wind_deg, description,
            visibility, cloudiness, sunrise, sunset, fetched_at
        ) VALUES (
            :city, :country, :temperature, :feels_like, :temp_min, :temp_max,
            :humidity, :pressure, :wind_speed, :wind_deg, :description,
            :visibility, :cloudiness, :sunrise, :sunset, :fetched_at
        )
    """, record)
    conn.commit()


# ── Query ──────────────────────────────────────────────────────
def query_latest(conn):
    """Print the most recent record for each city."""
    rows = conn.execute("""
        SELECT city, country, temperature, humidity,
               description, wind_speed, fetched_at
        FROM weather
        WHERE id IN (
            SELECT MAX(id) FROM weather GROUP BY city
        )
        ORDER BY city
    """).fetchall()

    print(f"\n{'City':<14} {'Country':<8} {'Temp (°C)':<11} {'Humidity':<10} {'Description':<22} {'Wind m/s':<10} Fetched")
    print("─" * 90)
    for r in rows:
        print(f"{r[0]:<14} {r[1]:<8} {r[2]:<11} {str(r[3])+'%':<10} {r[4]:<22} {r[5]:<10} {r[6]}")


# ── Export ─────────────────────────────────────────────────────
def export_csv(conn, filename="weather_export.csv"):
    """Export all rows to a CSV file."""
    rows = conn.execute("SELECT * FROM weather ORDER BY fetched_at DESC").fetchall()
    cols = [d[0] for d in conn.execute("SELECT * FROM weather LIMIT 0").description]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows → {filename}")


# ── Main ───────────────────────────────────────────────────────
def main(query=False, export=False):
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)

    if query:
        query_latest(conn)
        conn.close()
        return

    if export:
        export_csv(conn)
        conn.close()
        return

    # Fetch & store weather for each city
    print(f"\nFetching weather for {len(CITIES)} cities...\n")
    for city in CITIES:
        try:
            raw    = fetch_weather(city)
            record = parse_weather(raw)
            insert_weather(conn, record)
            print(f"  ✓  {record['city']}, {record['country']} — "
                  f"{record['temperature']}°C, {record['description']}")
        except requests.exceptions.HTTPError as e:
            print(f"  ✗  {city}: HTTP {e.response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"  ✗  {city}: connection failed")
        except Exception as e:
            print(f"  ✗  {city}: {e}")

    print(f"\nDone. Records stored in {DB_FILE}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenWeatherMap → SQLite")
    parser.add_argument("--query",  action="store_true", help="Print latest records")
    parser.add_argument("--export", action="store_true", help="Export all rows to CSV")
    args = parser.parse_args()
    main(query=args.query, export=args.export)
