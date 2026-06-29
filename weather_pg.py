"""
OpenWeatherMap → PostgreSQL Project
-------------------------------------
Production-grade upgrade from SQLite.

Setup:
    1. Install PostgreSQL on your machine
    2. Create the database:  createdb weather_db
    3. Copy .env.example → .env and fill in your credentials
    4. pip install requests psycopg2-binary python-dotenv

Usage:
    python weather_pg.py                  # fetch & store
    python weather_pg.py --query          # print latest per city
    python weather_pg.py --export         # export to CSV
    python weather_pg.py --migrate        # migrate data from SQLite
"""

import os
import requests
import psycopg2
import psycopg2.extras
import csv
import argparse
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────
API_KEY  = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY_HERE")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

CITIES = [
    "Nairobi", "Mombasa", "Kisumu", "Kisii",
    "Nakuru", "Eldoret", "Garissa",
    "London", "New York", "Tokyo", "Lagos"
]

# ── DB connection ───────────────────────────────────────────────
def get_conn():
    """Return a psycopg2 connection using .env credentials."""
    return psycopg2.connect(
        host     = os.getenv("DB_HOST",     "localhost"),
        port     = int(os.getenv("DB_PORT", "5432")),
        dbname   = os.getenv("DB_NAME",     "weather_db"),
        user     = os.getenv("DB_USER",     "postgres"),
        password = os.getenv("DB_PASSWORD", ""),
    )


# ── Schema ──────────────────────────────────────────────────────
def init_db(conn):
    """Create tables if they don't exist."""
    with conn.cursor() as cur:

        # Main weather readings table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weather (
                id          SERIAL PRIMARY KEY,
                city        TEXT    NOT NULL,
                country     TEXT,
                temperature NUMERIC(5,2),
                feels_like  NUMERIC(5,2),
                temp_min    NUMERIC(5,2),
                temp_max    NUMERIC(5,2),
                humidity    INTEGER,
                pressure    INTEGER,
                wind_speed  NUMERIC(5,2),
                wind_deg    INTEGER,
                description TEXT,
                visibility  INTEGER,
                cloudiness  INTEGER,
                sunrise     TEXT,
                sunset      TEXT,
                fetched_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        # Index for fast city + time queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_weather_city
            ON weather (city, fetched_at DESC)
        """)

        # Materialised latest-per-city view
        cur.execute("""
            CREATE OR REPLACE VIEW latest_weather AS
            SELECT DISTINCT ON (city)
                id, city, country, temperature, feels_like,
                humidity, pressure, wind_speed, description,
                sunrise, sunset, fetched_at
            FROM weather
            ORDER BY city, fetched_at DESC
        """)

    conn.commit()
    print("Schema ready — table, index, and view created.")


# ── API fetch ───────────────────────────────────────────────────
def fetch_weather(city):
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    r = requests.get(BASE_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def parse_weather(data):
    main    = data.get("main",    {})
    wind    = data.get("wind",    {})
    clouds  = data.get("clouds",  {})
    sys     = data.get("sys",     {})
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
        "sunrise":     datetime.utcfromtimestamp(
                           sys.get("sunrise", 0)).strftime("%H:%M UTC"),
        "sunset":      datetime.utcfromtimestamp(
                           sys.get("sunset",  0)).strftime("%H:%M UTC"),
        "fetched_at":  datetime.utcnow(),
    }


# ── Insert ──────────────────────────────────────────────────────
def insert_weather(conn, record):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO weather (
                city, country, temperature, feels_like, temp_min, temp_max,
                humidity, pressure, wind_speed, wind_deg, description,
                visibility, cloudiness, sunrise, sunset, fetched_at
            ) VALUES (
                %(city)s, %(country)s, %(temperature)s, %(feels_like)s,
                %(temp_min)s, %(temp_max)s, %(humidity)s, %(pressure)s,
                %(wind_speed)s, %(wind_deg)s, %(description)s,
                %(visibility)s, %(cloudiness)s, %(sunrise)s,
                %(sunset)s, %(fetched_at)s
            )
        """, record)
    conn.commit()


# ── Query ───────────────────────────────────────────────────────
def query_latest(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""
            SELECT city, country, temperature, humidity,
                   description, wind_speed, fetched_at
            FROM latest_weather
            ORDER BY temperature DESC
        """)
        rows = cur.fetchall()

    print(f"\n{'City':<14} {'Country':<9} {'Temp °C':<10} "
          f"{'Humidity':<10} {'Description':<22} {'Wind m/s':<10} Fetched")
    print("─" * 92)
    for r in rows:
        print(f"{r['city']:<14} {r['country']:<9} {r['temperature']:<10} "
              f"{str(r['humidity'])+'%':<10} {r['description']:<22} "
              f"{r['wind_speed']:<10} {r['fetched_at'].strftime('%Y-%m-%d %H:%M')}")


# ── Export ──────────────────────────────────────────────────────
def export_csv(conn, filename="weather_export.csv"):
    with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT * FROM weather ORDER BY fetched_at DESC")
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(cols)
        writer.writerows(rows)

    print(f"Exported {len(rows)} rows → {filename}")


# ── Migrate from SQLite ─────────────────────────────────────────
def migrate_from_sqlite(conn, sqlite_path="weather.db"):
    """Copy all rows from the old SQLite database into PostgreSQL."""
    if not os.path.exists(sqlite_path):
        print(f"SQLite file not found: {sqlite_path}")
        return

    sq = sqlite3.connect(sqlite_path)
    sq.row_factory = sqlite3.Row
    rows = sq.execute("SELECT * FROM weather").fetchall()
    sq.close()

    if not rows:
        print("No rows found in SQLite database.")
        return

    migrated = 0
    with conn.cursor() as cur:
        for r in rows:
            cur.execute("""
                INSERT INTO weather (
                    city, country, temperature, feels_like, temp_min, temp_max,
                    humidity, pressure, wind_speed, wind_deg, description,
                    visibility, cloudiness, sunrise, sunset, fetched_at
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                r["city"], r["country"], r["temperature"], r["feels_like"],
                r["temp_min"], r["temp_max"], r["humidity"], r["pressure"],
                r["wind_speed"], r["wind_deg"], r["description"],
                r["visibility"], r["cloudiness"], r["sunrise"],
                r["sunset"], r["fetched_at"]
            ))
            migrated += 1

    conn.commit()
    print(f"Migration complete — {migrated} rows moved to PostgreSQL.")


# ── Main ────────────────────────────────────────────────────────
def main(query=False, export=False, migrate=False):
    try:
        conn = get_conn()
        print("Connected to PostgreSQL ✓")
    except psycopg2.OperationalError as e:
        print(f"Connection failed: {e}")
        print("Check your .env credentials and that PostgreSQL is running.")
        return

    init_db(conn)

    if migrate:
        migrate_from_sqlite(conn)
        conn.close()
        return

    if query:
        query_latest(conn)
        conn.close()
        return

    if export:
        export_csv(conn)
        conn.close()
        return

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

    print(f"\nDone. Records stored in PostgreSQL.")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenWeatherMap → PostgreSQL")
    parser.add_argument("--query",   action="store_true", help="Print latest per city")
    parser.add_argument("--export",  action="store_true", help="Export all rows to CSV")
    parser.add_argument("--migrate", action="store_true", help="Migrate from SQLite")
    args = parser.parse_args()
    main(query=args.query, export=args.export, migrate=args.migrate)
