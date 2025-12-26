import datetime
import logging
import psycopg2
import calendar
import pandas as pd

from prefect import task, flow

from evidently import Report, DataDefinition, Dataset
from evidently.presets import DataDriftPreset

import sys
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from src.data_processing import preprocess, remove_outlier, feature_time_series, wide_to_long, feature_engineering



logging.basicConfig(
    # Configure basic logging
    level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s"
)

# Database connection strings
CONNECTION_STRING = "host=localhost port=5432 user=postgres password=example"
CONNECTION_STRING_DB = CONNECTION_STRING + " dbname=evidently"

# SQL statement to create the metrics tables.
create_table_statement = """
create table if not exists column_drift(
	timestamp TIMESTAMP,
	column_name TEXT,
	drift_score FLOAT,
    is_drift BOOLEAN,
    PRIMARY KEY (timestamp, column_name)
);

create table if not exists dataset_summary(
    timestamp TIMESTAMP PRIMARY KEY,
    number_of_drifted_columns INTEGER,
    share_of_drifted_columns FLOAT,
    dataset_drift BOOLEAN
);
"""

# data
reference_data = pd.read_csv("data/2024_top3.csv")
raw_data = pd.read_csv("data/2025.csv")


num_features = [
    'stock', 'hour',  'dayofweek',  'is_rush_hour', 'lag_15m_stock', 'lag_30m_stock',
    'lag_45m_stock', 'lag_60m_stock', 'target_next_stock', 'date'
]
cat_features = ['station', 'rideable_type']

data_definition = DataDefinition(
    numerical_columns=num_features, categorical_columns=cat_features
)

report = Report(metrics=[DataDriftPreset()])


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


@task(name="Prepare reference dataset")
def data_preprocessing(df):
    df = preprocess(df)
    df = remove_outlier(df)
    df = feature_time_series(df)
    df = wide_to_long(df)
    df = feature_engineering(df)
    return df


@task(name="Calculate metrics and save it to postgresql")
def run_evidently(ref_data, cur_data, month, i):

    start_ts = pd.to_datetime('2024-01-01').value
    end_ts = pd.to_datetime('2025-01-01').value

    target_date = pd.Timestamp(month+datetime.timedelta(days=i)).normalize()
    target_ts = target_date.value

    scaled_date = (target_ts-start_ts)/(end_ts - start_ts)

    current_data = cur_data[cur_data['date'] == scaled_date]

    current_dataset = Dataset.from_pandas(
        current_data, data_definition=data_definition)
    ref_dataset = Dataset.from_pandas(
        ref_data, data_definition=data_definition)

    run = report.run(reference_data=ref_dataset, current_data=current_dataset)

    return run.dict()


@task(name="Save drift metrics to database")
def save_drift_to_db(report_dict, month, i):

    metrics = report_dict['metrics']
    target_date = month + datetime.timedelta(days=i)

    # Data set Summary
    summary_data = metrics[0]['value']
    n_drifted = int(summary_data['count'])
    share_drifted = float(summary_data['share'])
    dataset_drift = share_drifted > 0.5

    # Column Drift
    column_results = []
    threshold = 0.1

    for metric in metrics[1:]:
        col_name = metric['config']['column']

        drift_score = float(metric['value'])
        is_drifted = drift_score > threshold

        column_results.append((target_date, col_name, drift_score, is_drifted))

    with psycopg2.connect(CONNECTION_STRING_DB) as conn:
        with conn.cursor() as cur:
            # Summary insert
            cur.execute(
                "INSERT INTO dataset_summary (timestamp, number_of_drifted_columns, share_of_drifted_columns, dataset_drift) VALUES (%s, %s, %s, %s) ON CONFLICT (timestamp) DO UPDATE SET number_of_drifted_columns = EXCLUDED.number_of_drifted_columns",
                (target_date, n_drifted, share_drifted, dataset_drift)
            )

            # Column drift insert
            cur.executemany(
                "INSERT INTO column_drift (timestamp, column_name, drift_score, is_drift) VALUES (%s, %s, %s, %s) ON CONFLICT (timestamp, column_name) DO NOTHING",
                column_results
            )
            conn.commit()


@flow
def batch_monitoring_backfill():
    prep_db()

    ref_processed = data_preprocessing(reference_data)
    current_processed = data_preprocessing(raw_data)

    month = datetime.datetime(2025, int(sys.argv[1]), 1, 0, 0)

    _, num_days = calendar.monthrange(2025, int(sys.argv[1])) # get the number of days in a month

    for i in range(0, num_days):
        report_dict = run_evidently(ref_processed, current_processed, month, i)
        save_drift_to_db(report_dict, month, i)

        
        logging.info("data sent")


if __name__ == "__main__":
    batch_monitoring_backfill()
