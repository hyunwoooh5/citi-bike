WITH combined_trips AS(
    SELECT start_station_name AS station_name
    FROM {{ ref('stg_trips_2024') }}
    WHERE start_station_name IS NOT NULL

    UNION ALL

    SELECT end_station_name AS station_name
    FROM {{ ref('stg_trips_2024') }}
    WHERE end_station_name IS NOT NULL
)

SELECT station_name
FROM combined_trips
GROUP BY station_name
ORDER BY COUNT(*) DESC
LIMIT 3