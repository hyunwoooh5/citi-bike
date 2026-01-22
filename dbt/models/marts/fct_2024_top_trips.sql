{{ config(materialized='table')}}

WITH top_stations AS (
    SELECT station_name FROM {{ ref('int_top_3_stations_2024')}}

)

SELECT *
FROM {{ ref('stg_trips_2024')}}
WHERE start_station_name IN (SELECT station_name FROM top_stations)
    OR end_station_name IN (SELECT station_name FROM top_stations)