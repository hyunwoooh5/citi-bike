# NYC Citi Bike Stock Prediction Service

**Machine Learning powered service to predict bike availability for NYC's top stations.**


## Overview

This project builds and deploys a machine learning model to predict the **stock (bike availability) 15 minutes into the future** for the top 3 most popular Citi Bike stations in NYC.


The final model, an **XGBoost Regressor**, is served via a **FastAPI** application for local testing and is containerized for serverless deployment on **AWS Lambda**.



-----

## Problem Statement & Object


### Why is this important? (Business Value)

In bike-sharing systems like Citi Bike, **Rebalancing** is a critical operational challenge.

* **Empty Stations:** If a station has no bikes, customers cannot start their trips, leading to **lost revenue** and churn.
* **Full Stations:** If a station is full, users cannot return their bikes, leading to **customer dissatisfaction** and potential overtime fees.


### The Objective

To solve this, this project aims to predict the stock level **15 minutes ahead**. Accurate predictions allow the operations team to proactively rebalance bikes or notify users, optimizing system efficiency.



-----

## Dataset & Features

The data is sourced from the [NYC Citi Bike System Data](https://citibikenyc.com/system-data).

* **Training Data:** 2024 records (via `data/download_data.sh` and `db/2024_citibike_top3_stations.sql`).
* **Test Data:** 2025 records (via `data/2025_citibike_top3_stations.sql`).
* **Preprocessing:** Handled by `src/data.py`.

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

Performed in [`notebook/notebook.ipynb`](notebooks/notebook.ipynb):

* Analyzed summary statistics and distributions.
* Imputed missing values using mean and mode strategies.
* Visualized variable correlations and time-series patterns.

### 3. Model Selection

Three different model architectures were trained and evaluated based on **Root Mean Squared Error (RMSE)** on the test set.

| Model | Description | MSE (Test) |
| --- | --- | --- |
| **VAR (Vector AutoRegression)** | Multivariate time-series statistical model | 20.1269 |
| **LSTM (Neural Network)** | 2-Layer LSTM with hidden size 64 | 15.1735 |
| **XGBoost Regressor** | **Gradient Boosting Decision Tree** | **2.6108** 🏆 |

### 4. Final Model

The **XGBoost Regressor** was selected for its superior performance and efficiency.

* **Hyperparameters:** `n_estimators=30`, `max_depth=20`, `learning_rate=0.1`
* **Artifact:** The trained model is saved as `bin/model.bin` for deployment.

-----




## Usage and Deployment

This project uses **[uv](https://github.com/astral-sh/uv)** for fast and reliable Python package management.

### Prerequisites

Install `uv` (macOS/Linux):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh

```


### Option 1: Run Locally (FastAPI)

1. **Install dependencies:**
```bash
uv sync --locked

```


2. **Run the server:**
```bash
uv run python src/serve.py

```


3. **Access the API:**
Open [http://localhost:1212/docs](https://www.google.com/search?q=http://localhost:1212/docs) to use the Swagger UI.



### Option 2: Run with Docker

1. **Build the image:**
```bash
docker build --platform=linux/amd64 -t citi-bike .

```


2. **Run the container:**
```bash
docker run -it --rm --platform=linux/amd64 -p 1212:9696 citi-bike

```


### Retraining the Model

To retrain the model with new data or parameters:

```bash
uv run python src/train.py

```

This overwrites `bin/model.bin`.




-----


## Deployment to AWS Lambda

This guide assumes you have the AWS CLI configured.

### 1. IAM Role Setup

Create an execution role for Lambda.

```bash
# 1. Create Trust Policy
echo '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
}' > trust-policy.json

# 2. Create Role
aws iam create-role --role-name lambda-basic-execution-role --assume-role-policy-document file://trust-policy.json

# 3. Attach Policy
aws iam attach-role-policy --role-name lambda-basic-execution-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

```

#### 2. Deploy the Function

The [deploy_lambda.sh](deploy_lambda.sh) script builds the Docker image, pushes it to AWS ECR, and creates/updates the Lambda function.

```bash
chmod +x deploy_lambda.sh
./deploy_lambda.sh

```

### 3. Invoke the Function

Test the deployed Lambda function using `curl`.

```bash
curl -X POST '<YOUR_LAMBDA_FUNCTION_URL>' \
-H "Content-Type: application/json" \
-d '{"station": "W 21 St & 6 Ave", "rideable_type": "classic_bike", "target_date": "2025-03-01"}'

```

-----




## Project structure


```plaintext
├── bin/
│   └── model.bin                 # Trained model artifact
├── data/
│   ├── download_data.sh          # Script to download raw data
│   └── *.csv                     # Processed datasets
├── db/
│   └── *.sql                     # SQL scripts for data extraction
├── notebooks/
│   └── notebook.ipynb            # EDA and model experimentation
├── src/
│   ├── data.py                   # Feature engineering logic
│   ├── train.py                  # Model training script
│   ├── predict.py                # Prediction logic
│   ├── serve.py                  # FastAPI server (Local)
│   ├── lambda_function.py        # AWS Lambda handler
│   └── invoke.py                 # Script to test Lambda invocation
├── Dockerfile                    # Docker config for FastAPI
├── Dockerfile.lambda             # Docker config for AWS Lambda
├── deploy_lambda.sh              # AWS deployment script
├── pyproject.toml                # Dependencies
└── README.md                     # Documentation

```


-----

## License

This project is licensed under the MIT License.