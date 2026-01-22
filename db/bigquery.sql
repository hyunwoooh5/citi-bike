-- 2024 data

LOAD DATA OVERWRITE `citibike_raw.trips_2024`
(
    ride_id STRING,
    rideable_type STRING,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    start_station_name STRING,
    start_station_id STRING, 
    end_station_name STRING,
    end_station_id STRING,  
    start_lat FLOAT64,
    start_lng FLOAT64,
    end_lat FLOAT64,
    end_lng FLOAT64,
    member_casual STRING
)
FROM FILES (
  format = 'CSV',
  uris = ['gs://citibike-project-2425/raw_data/2024*.csv'], 
  skip_leading_rows = 1  
);


-- 2025 data

LOAD DATA OVERWRITE `citibike_raw.trips_2025`
(
    ride_id STRING,
    rideable_type STRING,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    start_station_name STRING,
    start_station_id STRING,
    end_station_name STRING,
    end_station_id STRING,
    start_lat FLOAT64,
    start_lng FLOAT64,
    end_lat FLOAT64,
    end_lng FLOAT64,
    member_casual STRING
)
FROM FILES (
  format = 'CSV',
  uris = ['gs://citibike-project-2425/raw_data/2025*.csv'], 
  skip_leading_rows = 1  
);