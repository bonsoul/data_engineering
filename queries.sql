-- ============================================================
-- OpenWeatherMap SQLite — useful queries
-- Run with: sqlite3 weather.db < queries.sql
--       or open weather.db in DB Browser for SQLite
-- ============================================================


-- 1. All records (newest first)
SELECT * FROM weather ORDER BY fetched_at DESC;


-- 2. Latest reading per city
SELECT city, country, temperature, humidity, description, fetched_at
FROM weather
WHERE id IN (SELECT MAX(id) FROM weather GROUP BY city)
ORDER BY temperature DESC;


-- 3. Hottest city right now
SELECT city, country, temperature, description
FROM weather
WHERE id IN (SELECT MAX(id) FROM weather GROUP BY city)
ORDER BY temperature DESC
LIMIT 1;


-- 4. Cities above 25°C
SELECT city, temperature, description
FROM weather
WHERE id IN (SELECT MAX(id) FROM weather GROUP BY city)
  AND temperature > 25
ORDER BY temperature DESC;


-- 5. Average temperature per city across all fetches
SELECT city, country,
       ROUND(AVG(temperature), 1)  AS avg_temp,
       ROUND(MIN(temperature), 1)  AS min_temp,
       ROUND(MAX(temperature), 1)  AS max_temp,
       COUNT(*)                    AS readings
FROM weather
GROUP BY city
ORDER BY avg_temp DESC;


-- 6. High humidity alert (> 80%)
SELECT city, humidity, temperature, description, fetched_at
FROM weather
WHERE id IN (SELECT MAX(id) FROM weather GROUP BY city)
  AND humidity > 80
ORDER BY humidity DESC;


-- 7. Strongest winds
SELECT city, wind_speed, wind_deg, description
FROM weather
WHERE id IN (SELECT MAX(id) FROM weather GROUP BY city)
ORDER BY wind_speed DESC;


-- 8. How many fetches per city
SELECT city, COUNT(*) AS total_fetches,
       MIN(fetched_at) AS first_fetch,
       MAX(fetched_at) AS last_fetch
FROM weather
GROUP BY city
ORDER BY city;


-- 9. Temperature trend for a specific city (change 'Nairobi' as needed)
SELECT fetched_at, temperature, humidity, description
FROM weather
WHERE city = 'Nairobi'
ORDER BY fetched_at;


-- 10. Delete records older than 7 days
DELETE FROM weather
WHERE fetched_at < datetime('now', '-7 days');
