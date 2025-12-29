import calendar
import datetime
import logging
import pickle
import sys
from pathlib import Path

import pandas as pd
import psycopg2
from evidently import DataDefinition, Dataset, Regression, Report
from evidently.presets import RegressionPreset
from prefect import flow, task

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.data_processing import (  # noqa: E402
    feature_engineering,
    feature_time_series,
    preprocess,
    remove_outlier,
    wide_to_long,
)

logging.basicConfig(
    # Configure basic logging
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s]: %(message)s",
)

# Database connection strings
CONNECTION_STRING = "host=localhost port=5432 user=postgres password=example"
CONNECTION_STRING_DB = CONNECTION_STRING + " dbname=evidently"

# SQL statement to create the metrics tables.
create_table_statement = """
create table if not exists model_performance(
	timestamp TIMESTAMP PRIMARY KEY,
	rmse FLOAT,
	mae FLOAT,
    abs_error_max FLOAT
);
"""

# data
reference_data = pd.read_csv("data/2024_top3.csv")
raw_data = pd.read_csv("data/2025.csv")


num_features = [
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
cat_features = ["station", "rideable_type"]

data_definition = DataDefinition(
    regression=[Regression(target="target_next_stock", prediction="predict")]
)

report = Report(metrics=[RegressionPreset()])


@task(name="Prepare database")
def prep_db():
    """
    Prefect task to set up the database. It creates the 'evidently' database if it
    doesn't exist and then creates the 'dummy_metrics' table.
    """

    conn = psycopg2.connect(CONNECTION_STRING)
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT 1 FROM pg_database WHERE datname='evidently'")
        exists = cursor.fetchone()

        if not exists:
            cursor.execute("CREATE DATABASE evidently;")
            print("Database 'evidently' created successfully.")
    finally:
        cursor.close()
        conn.close()

    with psycopg2.connect(CONNECTION_STRING_DB) as conn:
        with conn.cursor() as cur:
            cur.execute(create_table_statement)
            conn.commit()


DataDefinition()


@task(name="Prepare reference dataset")
def data_preprocessing(df):
    df = preprocess(df)
    df = remove_outlier(df)
    df = feature_time_series(df)
    df = wide_to_long(df)
    df = feature_engineering(df)

    return df


@task(name="Prediction")
def prediction(df):
    with open("bin/model.bin", "rb") as f_in:
        model = pickle.load(f_in)

    features = [col for col in df.columns if col != "target_next_stock"]

    df["predict"] = model.predict(df[features])

    return df


@task(name="Calculate metrics and save it to postgresql")
def run_evidently(ref_data, cur_data, month, i):
    start_ts = pd.to_datetime("2024-01-01").value
    end_ts = pd.to_datetime("2025-01-01").value

    target_date = pd.Timestamp(month + datetime.timedelta(days=i)).normalize()
    target_ts = target_date.value

    scaled_date = (target_ts - start_ts) / (end_ts - start_ts)

    current_data = cur_data[cur_data["date"] == scaled_date]

    current_dataset = Dataset.from_pandas(current_data, data_definition=data_definition)
    ref_dataset = Dataset.from_pandas(ref_data, data_definition=data_definition)

    run = report.run(reference_data=ref_dataset, current_data=current_dataset)

    return run.dict()


@task(name="Save drift metrics to database")
def save_drift_to_db(report_dict, month, i):
    metrics = report_dict["metrics"]

    target_date = month + datetime.timedelta(days=i)

    for metric in metrics:
        val = metric.get("value")

        if "RMSE" in metric["metric_name"]:
            rmse = float(val) if isinstance(val, (float, int)) else float(val)

        elif "MAE" in metric["metric_name"]:
            # MAE는 {'mean': ..., 'std': ...} 구조이므로 mean 추출
            mae = float(val["mean"])

        elif "AbsMaxError" in metric["metric_name"]:
            # np.float64 타입을 일반 float으로 변환
            abs_error_max = float(val)

    with psycopg2.connect(CONNECTION_STRING_DB) as conn:
        with conn.cursor() as cur:
            # Summary insert
            cur.execute(
                "INSERT INTO model_performance (timestamp, rmse, mae, abs_error_max) VALUES (%s, %s, %s, %s) ON CONFLICT (timestamp) DO NOTHING",
                (target_date, rmse, mae, abs_error_max),
            )

            conn.commit()


@flow
def batch_monitoring_backfill():
    prep_db()

    ref_processed = data_preprocessing(reference_data)
    ref_processed = prediction(ref_processed)

    # Only consider validation set as reference
    split_idx = int(len(ref_processed) * 0.8)
    ref_processed = ref_processed.iloc[split_idx:].copy()

    current_processed = data_preprocessing(raw_data)
    current_processed = prediction(current_processed)

    month = datetime.datetime(2025, int(sys.argv[1]), 1, 0, 0)

    _, num_days = calendar.monthrange(
        2025, int(sys.argv[1])
    )  # get the number of days in a month

    for i in range(0, num_days):
        report_dict = run_evidently(ref_processed, current_processed, month, i)
        save_drift_to_db(report_dict, month, i)

        logging.info("data sent")


if __name__ == "__main__":
    batch_monitoring_backfill()
