# NYC Citi Bike Stock Prediction Service

**Machine Learning powered service to predict bike availability for NYC's top stations.**


## Overview

This project builds and deploys a machine learning model to predict the **stock (bike availability) 15 minutes into the future** for the top 3 most popular Citi Bike stations in NYC.


Beyond model training, this repository implements a production-ready infrastructure that includes:

* **Model Serving:** An **XGBoost Regressor** served via **FastAPI** and containerized for serverless deployment on **AWS Lambda**.
* **Orchestration:** Automated training and monitoring workflows managed by **Prefect**.
* **Observability:** Continuous tracking of **Data Drift** and **Model Performance** using **Evidently AI**, with metrics stored in **PostgreSQL** and visualized in **Grafana**.
* **Automation & Quality**: Task automation via **Make**, code quality enforcement with **Ruff**, and unit testing with **pytest**.
* **CI/CD**: Automated integration and deployment pipeline using **GitHub Actions**.


-----

## Quick Start (Automation with Make)

This project uses a `Makefile` to simplify common tasks. To see all available commands, run:

```bash
make help
```

### 1. Environment Setup

We use **[uv](https://github.com/astral-sh/uv)** for extremely fast Python package management.

```bash
make setup
```

### 2. Code Quality & Testing

Before committing, ensure your code follows standards and passes tests:

```bash
make check  # Run Ruff linter and formatter checks
make fix    # Automatically fix linting issues and reformat code
make test   # Run unit tests using pytest
```


-----

## CI/CD & Deployment

This project leverages **GitHub Actions** for automated quality assurance and **AWS Lambda** for scalable, serverless inference.

### 1. Infrastructure Setup (One-time)

Before any deployment, the AWS environment must be prepared. These commands create the necessary IAM Role that allows Lambda to execute and log to CloudWatch.

```bash
# 1. Create Trust Policy
echo '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}' > trust-policy.json

# 2. Create the IAM Role
aws iam create-role --role-name lambda-basic-execution-role --assume-role-policy-document file://trust-policy.json

# 3. Attach Execution Policy
aws iam attach-role-policy --role-name lambda-basic-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```


### 2. Deployment Options

#### Option A: Automated Deployment (Recommended)

Managed by GitHub Actions. Every time a version tag is pushed, the pipeline runs tests and updates the Lambda function.

**Prerequisites:** Add these to GitHub Secrets (**Settings > Secrets > Actions**):

* `AWS_ACCESS_KEY_ID`
* `AWS_SECRET_ACCESS_KEY`

**Trigger:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

#### Option B: Manual Deployment (Optional)

Useful for local testing or emergency updates without pushing to GitHub.

**Prerequisites:** Ensure your local AWS CLI is configured (`aws configure`).

**Execution:**

```bash
# This command runs deploy_lambda.sh via Makefile
make deploy-lambda

```



### 3. CI/CD Workflow Summary

* **Continuous Integration**: On every push to `main`, `ruff` (linting) and `pytest` (unit tests) are executed to maintain code quality.
* **Continuous Deployment**: Triggered by tags (`v*`). It builds a Docker image (`linux/amd64`), pushes it to **Amazon ECR**, and updates the **Lambda** function code and configuration (60s timeout, 256MB memory).




-----

## Problem Statement & Object


### Why is this important? (Business Value)

In bike-sharing systems like Citi Bike, **Rebalancing** is a critical operational challenge.

* **Empty Stations:** If a station has no bikes, customers cannot start their trips, leading to **lost revenue** and churn.
* **Full Stations:** If a station is full, users cannot return their bikes, leading to **customer dissatisfaction** and potential overtime fees.


### The Objective

This project aims to solve the rebalancing problem by building a machine learning model that **predicts stock levels 15 minutes into the future and when the station becomes empty**.

**Key Assumption & Real-World Implementation:**
The model relies on recent historical data (previous stock levels) to calculate lag features and make accurate predictions. In a real-world business scenario, this is achieved by **continuously collecting data every 15 minutes via the Citi Bike API**. This ensures the system always has the most recent sequence of data required to predict the next time step.



-----

## Dataset & Features

The data is sourced from the [NYC Citi Bike System Data](https://citibikenyc.com/system-data).

* **Training Data:** 2024 records (via `data/download_data.sh` and `db/2024_citibike_top3_stations.sql`).
* **Test Data:** 2025 records (via `data/2025_citibike_top3_stations.sql`).
* **Preprocessing:** Handled by `src/data.py`. 

### Key Data Assumption: Daily Rebalancing

For the purpose of this project, a specific initialization rule was applied to the dataset:

> **At 00:00 (midnight) every day, every station is assumed to be rebalanced.**
> The stock is reset to **10 classic bikes** and **10 electric bikes** for each station. This provides a consistent baseline for the model to begin predictions for the new day.

### Feature Descriptions

The model uses temporal features and lag features to capture trends.


| Feature | Description |
| :--- | :--- |
| **time** | Timestamp of the record |
| **station** | Top 3 popular bike stations: `W 21 St & 6 Ave`, `University Pl & E 14 St`, `8 Ave & W 31 St` |
| **rideable_type** | Type of bike (`classic_bike` or `electric_bike`) |
| **stock** | Current bike stock at the station |
| **hour** | Time of day represented as a float (e.g., 14:30 = 14.5) |
| **dayofweek** | Day of the week (0 = Monday, 6 = Sunday) |
| **is_rush_hour** | Binary indicator for peak hours (1 if 8≤hour≤10 or 17≤hour≤19, otherwise 0) |
| **lag_{15,30,45,60}m_stock** | Stocks 15, 30, 45, and 60 minutes before |
| **target_next_stock** | **(Target)** The actual stock level 15 minutes later |
| **date**| The calendar date of the record (YYYY-MM-DD) |

-----




## Project Workflow


### 1. Data Collection and Preprocessing

The original dataset is sourced from [NYC Citi Bike data](https://citibikenyc.com/system-data). The data pipeline is managed as follows:

* **Training Data:** Downloaded and prepared using [`data/download_data.sh`](data/download_data.sh) and the SQL script [`db/2024_citibike_top3_stations.sql`](db/2024_citibike_top3_stations.sql).
* **Test Data:** The 2025 dataset is generated and converted to CSV using [`db/2025_citibike_top3_stations.sql`](db/2025_citibike_top3_stations.sql).

### 2. Exploratory Data Analysis (EDA)

Performed in [`notebooks/data_eda.ipynb`](notebooks/data_eda.ipynb):

* Analyzed summary statistics and distributions.
* Imputed missing values using mean and mode strategies.
* Visualized variable correlations and time-series patterns.

### 3. Model Selection & Experiment Tracking (MLflow)

Three different model architectures were trained, and all experiments were tracked using **MLflow**.

* **Tracking URI:** Local SQLite database (`sqlite:///mlflow.db`)
* **Metric:** Experiments were evaluated based on **Root Mean Squared Error (RMSE)** on the test set.

| Model | Description | MSE (Test) |
| --- | --- | --- |
| **VAR (Vector AutoRegression)** | Multivariate time-series statistical model | 2.5062 | Arhived |
| **LSTM (Neural Network)** | 2-Layer LSTM with hidden size 64 | 12.9794 | Archived |
| **XGBoost Regressor** | **Gradient Boosting Decision Tree** | **2.0787** 🏆 | **Registered** |





### 4. Model Registry & Management

The best performing model (XGBoost) was automatically selected and registered to the **MLflow Model Registry**.

* **Automatic Registration:** The pipeline searches for the run with the lowest `test_rmse` and registers it as `CitiBike_Predictor`.
* **Alias Management:** The best model version is assigned the **`@champion`** alias.
* **Metadata:** Detailed descriptions (Markdown) for the model and versions are updated via the `MlflowClient`.



### 5. Workflow Orchestration (Prefect)

The entire training process is automated using **Prefect**, ensuring reproducibility and robust model management.

* **Flow:** [`flows/train_flow.py`](flows/train_flow.py) orchestrates the end-to-end pipeline.
* **Logic:**
    1.  **Read & Preprocess:** Ingests data and generates lag features.
    2.  **Train:** Fits an XGBoost model and logs parameters/metrics to MLflow.
    3.  **Evaluate & Promote:** * Compares the new model's RMSE with the global best run.
        * **Automatic Promotion:** If the new model wins, it is registered as `@champion` in MLflow.
        * **Artifact Update:** The winning model is automatically serialized to `bin/model.bin` (using `sklearn` flavor) for immediate deployment.



### 6. Final Model Deployment

The **XGBoost Regressor** is served via MLflow using the `champion` alias.

* **Hyperparameters:** `n_estimators=58`, `max_depth=6`, `learning_rate=0.2089`
* **Loading Strategy:**
To support Pandas `category` data types natively used by XGBoost, the model is loaded using the `sklearn` flavor (bypassing the strict PyFunc schema enforcement).
```python
import mlflow
model = mlflow.sklearn.load_model("models:/CitiBike_Predictor@champion")
```


* **Inference:** The model accepts categorical inputs directly without one-hot encoding, preserving the training schema.



### 7. Monitoring & Observability (Evidently & Grafana)

This project implements a comprehensive monitoring suite to track model performance and data health using **Evidently**, **PostgreSQL**, and **Grafana**.


#### Monitoring Infrastructure

The monitoring stack is containerized and managed via Docker Compose:

* **PostgreSQL**: Serves as the metadata store for drift metrics and model performance.
* **Grafana**: Provides real-time visualization with pre-configured data sources and dashboards.
* **Adminer**: A lightweight database management tool for manual SQL inspection.



#### Automated Monitoring Flows

The monitoring logic is orchestrated through **Prefect** flows to enable consistent backfilling and scheduled checks:

1. **Data Drift Monitoring** ([`flows/monitoring_data_flow.py`](flows/monitoring_data_flow.py)):
* Uses Evidently's `DataDriftPreset` to compare current production data against the reference dataset.
* Calculates drift scores for numerical and categorical features (e.g., `stock`, `is_rush_hour`, `station`).
* Stores results in `column_drift` and `dataset_summary` tables.


2. **Model Performance Monitoring** ([`flows/monitoring_performance_flow.py`](flows/monitoring_performance_flow.py)):
* Uses Evidently's `RegressionPreset` to evaluate model accuracy.
* Tracks key regression metrics: **RMSE**, **MAE**, and **Max Absolute Error**.
* Saves daily performance snapshots into the `model_performance` table.



#### How to Run Monitoring

1. **Start the Infrastructure**:
```bash
docker-compose up -d
```


* **Grafana**: Access at [http://localhost:3000](http://localhost:3000) (Data source is automatically provisioned).
* **Adminer**: Access at [http://localhost:8080](http://localhost:8080) to query the `evidently` database.


2. **Run Backfill Flows**:
Execute the monitoring flows by providing the month as a command-line argument:
```bash
# Run data drift analysis for March
uv run python flows/monitoring_data_flow.py 3

# Run performance analysis for March
uv run python flows/monitoring_performance_flow.py 3
```


#### Sample Grafana Queries

Use the following SQL queries to create visualizations in your Grafana dashboards:

**Feature Drift (e.g., Stock Column)**

```sql
SELECT
  timestamp AS "time",
  drift_score,
  column_name
FROM column_drift
WHERE column_name = 'stock'
ORDER BY 1;
```

**Model Error Metrics (RMSE & MAE)**

```sql
SELECT
  timestamp AS "time",
  rmse,
  mae
FROM model_performance
ORDER BY 1;
```

-----




## Alternative Deployment Options

### Option 1: Local FastAPI Server

Run the API locally using `uv`:

```bash
make run-local
```

Open [http://localhost:9696/docs](http://localhost:9696/docs) to use the Swagger UI.



### Options 2: Kubernetes (Kind & HPA)

#### 1. Deploy Application


Deploy to a local Kind cluster with **Horizontal Pod Autoscaling**.

```bash
make k8s-up
```

* This command builds the image, creates the cluster, installs the Metrics Server (patched for Kind), and applies the manifests in `k8s/`.


#### 2. Access the Service

Port-forward the service to your local machine.

```bash
kubectl port-forward service/citi-bike-service 8080:80
```

Access the API at: [http://localhost:8080/docs](http://localhost:8080/docs)


#### 3. Test Autoscaling (HPA)

Simulate traffic to trigger autoscaling (Scale out from 1 to 5 pods).

**Open a new terminal and run:**

```bash
while true; do curl -X POST "http://localhost:8080/predict" \
-H "Content-Type: application/json" \
-d '{"station": "W 21 St & 6 Ave", "rideable_type": "classic_bike", "target_date": "2025-03-01"}'; \
echo; done
```

**Monitor HPA in another terminal:**

```bash
kubectl get hpa -w
```

*Note: Scaling down (cooldown) takes approximately 5 minutes after traffic stops.*


#### Cleanup


To stop the application and clean up resources:

```bash
make k8s-down docker-rmi
```


### Retraining the Model

To retrain the model and automatically update the deployment artifact (`bin/model.bin`) using the Prefect pipeline:

1. **Install workflow dependencies:**
```bash
uv sync --extra workflows
```

2. **Run the training flow:**
```bash
uv run python flows/train_flow.py "data/2024_top3.csv"
```

*Note: The `bin/model.bin` file will only be overwritten if the new model achieves a lower RMSE than the current best record.*


-----




## Project structure


```plaintext
├── bin/
│   └── model.bin                      # Trained model artifact
├── data/
│   ├── download_data.sh               # Script to download raw data
│   └── *.csv                          # Processed datasets
├── db/
│   └── *.sql                          # SQL scripts for data extraction
├── flows/
│   ├── monitoring_data_flow.py        # Prefect pipeline for data drift
│   ├── monitoring_performance_flow.py # Prefect pipeline for performance metrics
│   └── train_flow.py                  # Prefect pipeline for training & promotion
├── grafana/
│   ├── grafana_dashboards.yaml        # Grafana dashboard provisioning config
│   └── grafana_datasources.yaml       # Grafana PostgreSQL data source config
├── notebooks/
│   ├── data_eda.ipynb                 # Data collection and preprocessing
│   └── modeling.ipynb                 # Model experimentation
├── src/
│   ├── data_collection.py             # Add data to SQL database script
│   ├── data_preprocessing.py          # Feature engineering logic
│   ├── train.py                       # Model training script
│   ├── predict.py                     # Prediction logic
│   ├── serve.py                       # FastAPI server (Local)
│   ├── lambda_function.py             # AWS Lambda handler
│   └── invoke.py                      # Script to test Lambda invocation
├── tests/
│   └── data_processing_test.py        # Pytest unit tests
├── Dockerfile                         # Docker config for FastAPI
├── Dockerfile-lambda                  # Docker config for AWS Lambda
├── deploy_lambda.sh                   # AWS deployment script
├── Makefile                           # Automation commands
├── pyproject.toml                     # Dependencies
└── README.md                          # Documentation
```


-----

## License

This project is licensed under the MIT License.