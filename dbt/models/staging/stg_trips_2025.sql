SELECT
    ride_id,
    rideable_type,
    CAST(started_at AS TIMESTAMP) as started_at,
    CAST(ended_at AS TIMESTAMP) as ended_at,
    start_station_name,
    start_station_id,
    end_station_name,
    end_station_id,
    start_lat,
    start_lng,
    end_lat,
    end_lng,
    member_casual

FROM {{ source('citibike_raw', 'trips_2025')}}