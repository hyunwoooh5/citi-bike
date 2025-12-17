-- Make database and table

CREATE DATABASE citibike_db;

DROP TABLE IF EXISTS citibike_trips_2024;

CREATE UNLOGGED TABLE citibike_trips_2024(
    ride_id VARCHAR(60),
    rideable_type VARCHAR(50),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    start_station_name VARCHAR(200),
    start_station_id VARCHAR(100),
    end_station_name VARCHAR(200),
    end_station_id VARCHAR(100),
    start_lat DOUBLE PRECISION,
    start_lng DOUBLE PRECISION,
    end_lat DOUBLE PRECISION,
    end_lng DOUBLE PRECISION,
    member_casual VARCHAR(20)
);


-- Check number of rows

SELECT COUNT(*) FROM citibike_trips_2024;


-- Check duplicates, add key, and add indices

ALTER TABLE citibike_trips_2024 ADD PRIMARY KEY (ride_id);

CREATE INDEX idx_start_station ON citibike_trips_2024(start_station_name);
CREATE INDEX idx_end_station ON citibike_trips_2024(end_station_name);

ALTER TABLE citibike_trips_2024 SET LOGGED;


-- Find top 3 busy stations

SET work_mem= '128MB';

SELECT station_name, COUNT(*) AS total_usage
FROM (
    SELECT start_station_name AS station_name
    FROM citibike_trips_2024
    WHERE start_station_name IS NOT NULL

    UNION ALL

    SELECT end_station_name AS station_name
    FROM citibike_trips_2024
    WHERE end_station_name IS NOT NULL
) AS combined_trips
GROUP BY station_name
ORDER BY total_usage DESC
LIMIT 3;

-- Get table for top 3 busy stations

WITH top_3_stations AS (
    SELECT station_name
    FROM (
        SELECT start_station_name AS station_name FROM citibike_trips_2024 
        WHERE start_station_name IS NOT NULL
        
        UNION ALL
        
        SELECT end_station_name AS station_name FROM citibike_trips_2024 
        WHERE end_station_name IS NOT NULL
    ) AS combined
    GROUP BY station_name
    ORDER BY COUNT(*) DESC
    LIMIT 3
)
SELECT *
FROM citibike_trips_2024
WHERE start_station_name IN (SELECT station_name FROM top_3_stations)
   OR end_station_name IN (SELECT station_name FROM top_3_stations);