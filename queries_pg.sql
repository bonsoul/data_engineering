-- ============================================================
-- OpenWeatherMap PostgreSQL — useful queries
-- Connect: psql -d weather_db -f queries_pg.sql
-- ============================================================


-- 1. Latest reading per city (via the view)
SELECT city, country, temperature, humidity, description, fetched_at
FROM latest_weather
ORDER BY temperature DESC;


-- 2. Hourly temperature trend for Nairobi (last 24 hrs)
SELECT
    DATE_TRUNC('hour', fetched_at) AS hour,
    ROUND(AVG(temperature)::NUMERIC, 2) AS avg_temp,
    ROUND(AVG(humidity)::NUMERIC, 1)    AS avg_humidity
FROM weather
WHERE city = 'Nairobi'
  AND fetched_at >= NOW() - INTERVAL '24 hours'
GROUP BY 1
ORDER BY 1;


-- 3. Average, min, max temp per city across all readings
SELECT
    city,
    country,
    ROUND(AVG(temperature)::NUMERIC, 1) AS avg_temp,
    MIN(temperature)                    AS min_temp,
    MAX(temperature)                    AS max_temp,
    COUNT(*)                            AS total_readings
FROM weather
GROUP BY city, country
ORDER BY avg_temp DESC;


-- 4. High humidity alert (> 80%) right now
SELECT city, humidity, temperature, description, fetched_at
FROM latest_weather
WHERE humidity > 80
ORDER BY humidity DESC;


-- 5. Hottest and coldest cities right now
(SELECT 'Hottest' AS rank, city, temperature, description FROM latest_weather ORDER BY temperature DESC LIMIT 1)
UNION ALL
(SELECT 'Coldest', city, temperature, description FROM latest_weather ORDER BY temperature ASC  LIMIT 1);


-- 6. Temperature change between first and latest reading per city
SELECT
    a.city,
    a.temperature                        AS first_temp,
    b.temperature                        AS latest_temp,
    ROUND((b.temperature - a.temperature)::NUMERIC, 2) AS change_c
FROM
    (SELECT DISTINCT ON (city) city, temperature FROM weather ORDER BY city, fetched_at ASC)  a
JOIN
    (SELECT DISTINCT ON (city) city, temperature FROM weather ORDER BY city, fetched_at DESC) b
    ON a.city = b.city
ORDER BY change_c DESC;


-- 7. Number of fetches and date range per city
SELECT
    city,
    COUNT(*)                             AS total_fetches,
    MIN(fetched_at)                      AS first_fetch,
    MAX(fetched_at)                      AS last_fetch,
    EXTRACT(EPOCH FROM (MAX(fetched_at) - MIN(fetched_at)))/3600 AS hours_covered
FROM weather
GROUP BY city
ORDER BY city;


-- 8. Strong wind alert (> 10 m/s)
SELECT city, wind_speed, wind_deg, description, fetched_at
FROM latest_weather
WHERE wind_speed > 10
ORDER BY wind_speed DESC;


-- 9. Auto-delete readings older than 30 days (run as a scheduled job)
DELETE FROM weather
WHERE fetched_at < NOW() - INTERVAL '30 days';


-- 10. Row count and DB size
SELECT
    COUNT(*)                                    AS total_rows,
    pg_size_pretty(pg_total_relation_size('weather')) AS table_size
FROM weather;
