import pandas as pd
import pytest

from src import data_processing


@pytest.fixture
def sample_raw_df():
    data = {
        "ride_id": ["A", "B", "C"],
        "rideable_type": ["classic_bike", "electric_bike", "classic_bike"],
        "started_at": [
            "2024-01-01 08:00:00",
            "2024-01-01 09:00:00",
            "2024-01-01 10:00:00",
        ],
        "ended_at": [
            "2024-01-01 08:10:00",
            "2024-01-01 09:15:00",
            "2024-01-01 10:20:00",
        ],
        "start_station_name": ["St1", "St1", "St2"],
        "end_station_name": ["St2", "St2", "St1"],
        "start_station_id": [1, 1, 2],
        "end_station_id": [2, 2, 1],
        "start_lat": [40.1, 40.1, 40.2],
        "start_lng": [-73.1, -73.1, -73.2],
        "end_lat": [40.2, 40.2, 40.1],
        "end_lng": [-73.2, -73.2, -73.1],
        "member_casual": ["member", "casual", "member"],
    }
    return pd.DataFrame(data)


def test_preprocess(sample_raw_df):
    expected_columns = set(
        [
            "rideable_type",
            "started_at",
            "ended_at",
            "start_station_name",
            "end_station_name",
        ]
    )

    actual_columns = set(data_processing.preprocess(sample_raw_df).columns.tolist())

    assert actual_columns == expected_columns


def test_remove_outlier(sample_raw_df):
    expected_columns = set(
        [
            "rideable_type",
            "started_at",
            "ended_at",
            "start_station_name",
            "end_station_name",
            "start_time",
            "end_time",
            "duration",
        ]
    )

    df_out = data_processing.preprocess(sample_raw_df)
    df_out = data_processing.remove_outlier(df_out)

    actual_columns = set(df_out.columns.tolist())

    assert df_out.iloc[0]["duration"] == 10.0
    assert df_out.iloc[1]["duration"] == 15.0
    assert df_out.iloc[2]["duration"] == 20.0
    assert actual_columns == expected_columns


def test_feature_time_series(sample_raw_df):
    expected_columns = set(
        [
            ("St1", "classic_bike"),
            ("St2", "classic_bike"),
            ("St1", "electric_bike"),
            ("St2", "electric_bike"),
        ]
    )

    df_out = data_processing.preprocess(sample_raw_df)
    df_out = data_processing.remove_outlier(df_out)
    df_out = data_processing.feature_time_series(df_out)

    actual_columns = set(df_out.columns.tolist())

    assert actual_columns == expected_columns


def test_wide_to_long(sample_raw_df):
    expected_columns = set(["time", "station", "rideable_type", "stock"])

    df_out = data_processing.preprocess(sample_raw_df)
    df_out = data_processing.remove_outlier(df_out)
    df_out = data_processing.feature_time_series(df_out)
    df_out = data_processing.wide_to_long(df_out)

    actual_columns = set(df_out.columns.tolist())

    assert actual_columns == expected_columns


def test_feature_engineering(sample_raw_df):
    expected_columns = set(
        [
            "station",
            "rideable_type",
            "stock",
            "hour",
            "dayofweek",
            "is_rush_hour",
            "lag_15m_stock",
            "lag_30m_stock",
            "lag_45m_stock",
            "lag_60m_stock",
            "target_next_stock",
            "date",
        ]
    )

    df_out = data_processing.preprocess(sample_raw_df)
    df_out = data_processing.remove_outlier(df_out)
    df_out = data_processing.feature_time_series(df_out)
    df_out = data_processing.wide_to_long(df_out)
    df_out = data_processing.feature_engineering(df_out)

    actual_columns = set(df_out.columns.tolist())

    assert actual_columns == expected_columns
