import pandas as pd
import xgboost as xgb
import numpy as np
import sys
import pickle
import mlflow
from mlflow.tracking import MlflowClient
from sklearn.metrics import mean_squared_error
from pathlib import Path

root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from prefect import task, flow

from src.data_processing import preprocess, remove_outlier, feature_time_series, wide_to_long, feature_engineering


@task(name="Read csv file")
def read_csv(file):
    return pd.read_csv(file)


@task(name="Preprocessing",
      retries=3,
      retry_delay_seconds=5,
      log_prints=True)
def data_preprocessing(df):
    df = preprocess(df)
    df = remove_outlier(df)
    df = feature_time_series(df)
    df = wide_to_long(df)
    df = feature_engineering(df)
    return df


@task(name="Training")
def train(df):
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("citi-bike")

    features = [col for col in df.columns if col != 'target_next_stock']

    X = df[features]
    y = df['target_next_stock']

    split_idx = int(len(X)*0.8)

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    mlflow.xgboost.autolog(log_models=False)
    with mlflow.start_run() as run:
        mlflow.set_tag("model_type", "xgboost")
        mlflow.set_tag("developer", "prefect-pipeline")

        model = xgb.XGBRegressor(random_state=42,
                                 enable_categorical=True,
                                 n_estimators=58,
                                 max_depth=6,
                                 learning_rate=0.2089
                                 )

        model.fit(X_train, y_train)

        preds = model.predict(X_test)
        rmse = np.sqrt(mean_squared_error(y_test, preds))

        mlflow.log_metric("test_rmse", rmse)

        # sklearn flavor
        mlflow.sklearn.log_model(model, name="model")

    mlflow.xgboost.autolog(disable=True)

    return run.info.run_id, rmse


@task(name="Promote Model")
def promote_model(current_run_id, current_rmse):
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    client = MlflowClient()

    experiment_name = "citi-bike"
    model_name = "CitiBike_Predictor"

    experiment = client.get_experiment_by_name(experiment_name)
    best_run = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string="",
        max_results=1,
        order_by=["metrics.test_rmse ASC"]
    )[0]

    best_run_id = best_run.info.run_id
    best_rmse = best_run.data.metrics.get(
        "test_rmse", float('inf'))  # inf: default value if not exist

    print(f"Global Best RMSE: {best_rmse} (Run ID: {best_run_id})")
    print(f"Current Run RMSE: {current_rmse} (Run ID: {current_run_id})")

    if current_run_id == best_run_id:
        print("New model is the best. Promoting to Champion")

        model_uri = f"runs:/{current_run_id}/model"
        model_version = mlflow.register_model(
            model_uri=model_uri, name=model_name)

        client.set_registered_model_alias(
            name=model_name,
            alias="Champion",
            version=model_version.version
        )

        print(f"Model version {model_version.version} aliased as '@champion'.")

        # Saving the model as local file(bin/model.bin)
        loaded_model = mlflow.sklearn.load_model(model_uri)

        with open("bin/model.bin", "wb") as f_out:
            pickle.dump(loaded_model, f_out)

        print("Model saved locally at 'bin/model.bin'")

    else:
        print("Current model is not the best. No promotion.")
        print(f"Keep existing best run ({best_run_id}) as standard.")


@flow(name="Main flow", log_prints=True)
def main(file):
    df = read_csv(file)

    df = data_preprocessing(df)

    run_id, rmse = train(df)

    promote_model(run_id, rmse)


if __name__ == '__main__':
    main(sys.argv[1])

    # Scheduler if needed
    # main.serve(name="weekly-retraining-deployment",
    #            cron = "0 0 * * 0",
    #            tags=["production", "training"],
    #            parameters={"file": "data/2024_top3.csv"}
    # )
