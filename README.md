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

Performed in [`notebooks/data_collection_preprocessing_eda.ipynb`](notebooks/data_collection_preprocessing_eda.ipynb):

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

### 5. Final Model Deployment

The **XGBoost Regressor** is served via MLflow using the `champion` alias.

* **Hyperparameters:** `n_estimators=58`, `max_depth=6`, `learning_rate=0.2089`
* **Loading Strategy:**
To support Pandas `category` data types natively used by XGBoost, the model is loaded using the `sklearn` flavor (bypassing the strict PyFunc schema enforcement).
```python
import mlflow
model = mlflow.sklearn.load_model("models:/CitiBike_Predictor@champion")

```


* **Inference:** The model accepts categorical inputs directly without one-hot encoding, preserving the training schema.


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
*Note: The server runs on host `0.0.0.0` and port `9696`.*
```bash
uv run python src/serve.py

```


3. **Access the API:**
Open [http://localhost:9696/docs](http://localhost:9696/docs) to use the Swagger UI.



### Option 2: Run with Docker

1. **Build the image:**
```bash
docker build --platform=linux/amd64 -t citi-bike .

```


2. **Run the container:**
```bash
docker run -it --rm --platform=linux/amd64 -p 9696:9696 citi-bike

```

### Options 3: Run with Kubernetes (Kind & HPA)
This project supports local Kubernetes deployment with **Horizontal Pod Autoscaling (HPA)** using Kind.


#### 1. Setup Cluster & Metrics Server

Create a cluster and install the Metric Servers (patched for Kind) to enable HPA.

```bash
# 1. Create Cluster
kind create cluster --name citi-bike-cluster

# 2. Install Metrics Server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# 3. Patch Metrics Server (Required for Kind)
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

```


#### 2. Deploy Application

Build the image, load it into the cluster nodes, and deploy resources.

```bash
# 1. Build & Load Image
docker build -t citi-bike:v1 -f Dockerfile .
kind load docker-image citi-bike:v1 --name citi-bike-cluster

# 2. Apply Manifests (Deployment, Service, HPA)
kubectl apply -f k8s/

```


#### 3. Access the Service

Port-forward the service to your local machine.

```bash
kubectl port-forward service/citi-bike-service 8080:80

```

Access the API at: [http://localhost:8080/docs](https://www.google.com/search?q=http://localhost:8080/docs)


#### 4. Test Autoscaling (HPA)

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
# Option 1: Remove only the application (Keep the cluster running)
kubectl delete -f k8s/

# Option 2: Delete the entire Kind cluster (Removes everything including Metrics Server)
kind delete cluster --name citi-bike-cluster

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
│   ├── data_collection.py        # Add data to SQL database script
│   ├── data_preprocessing.py     # Feature engineering logic
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