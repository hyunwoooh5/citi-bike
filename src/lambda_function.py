import json
import pickle
from datetime import datetime
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, field_validator


class Info(BaseModel):
    station: Literal["W 21 St & 6 Ave", "University Pl & E 14 St", "8 Ave & W 31 St"]
    rideable_type: Literal["classic_bike", "electric_bike"]
    target_date: str

    @field_validator("target_date")
    @classmethod
    def check_target_date(cls, date_value):
        try:
            parsed_date = datetime.strptime(date_value, "%Y-%m-%d")

            if parsed_date.year != 2025:
                raise ValueError("Year should be 2025")
            elif parsed_date.month == 12:
                raise ValueError("Month should be less than 12")

        except ValueError as err:
            raise ValueError("Incorrect date") from err

        return date_value


with open("model.bin", "rb") as f:
    model = pickle.load(f)

# Load data globally to avoid overhead per invocation
DF_HISTORY = pd.read_csv("2025_long.csv", parse_dates=["time"])

DF_HISTORY["station"] = DF_HISTORY["station"].astype("category")
DF_HISTORY["rideable_type"] = DF_HISTORY["rideable_type"].astype("category")


def predict_day(model, info):
    start_search = pd.to_datetime(info.target_date) - pd.Timedelta(hours=2)
    end_search = pd.to_datetime(info.target_date) + pd.Timedelta(hours=24)

    mask = (
        (DF_HISTORY["station"] == info.station)
        & (DF_HISTORY["rideable_type"] == info.rideable_type)
        & (DF_HISTORY["time"] >= start_search)
        & (DF_HISTORY["time"] <= end_search)
    )
    data = DF_HISTORY.loc[mask].copy()

    data["lag_15m_stock"] = data["stock"].shift(1)  # 1 row back (assuming 15min freq)
    data["lag_30m_stock"] = data["stock"].shift(2)
    data["lag_45m_stock"] = data["stock"].shift(3)
    data["lag_60m_stock"] = data["stock"].shift(4)

    # B. Time Features
    data["hour"] = data["time"].dt.hour + data["time"].dt.minute / 60.0
    data["dayofweek"] = data["time"].dt.dayofweek
    data["is_rush_hour"] = data["hour"].apply(
        lambda h: 1 if (8 <= h < 10) or (17 <= h < 19) else 0
    )

    # C. Date Numerical
    start_ts = pd.to_datetime("2024-01-01").value
    end_ts = pd.to_datetime("2025-01-01").value
    data["date"] = (data["time"].dt.normalize().astype(np.int64) - start_ts) / (
        end_ts - start_ts
    )

    target_mask = (data["time"] >= pd.to_datetime(info.target_date + " 00:00:00")) & (
        data["time"] <= pd.to_datetime(info.target_date + " 23:45:00")
    )

    inference_df = data.loc[target_mask].copy()

    features = [
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
        "date",
    ]

    pred = model.predict(inference_df[features])
    result_df = pd.DataFrame(
        {"time": inference_df["time"] + pd.Timedelta(minutes=15), "prediction": pred}
    )
    result_df = result_df.reset_index()

    initial_stock = 10
    target = 10
    ans = []
    for i in range(len(result_df)):
        if result_df.loc[i, "prediction"] < initial_stock - target:
            ans.append(result_df.loc[i, "time"].strftime("%Y-%m-%d %H:%M:%S"))
            initial_stock -= target
    return ans


def lambda_handler(event, context):
    print("Parameters:", event)

    if "body" in event:
        # Call HTTP (curl)
        data = json.loads(event["body"])
    else:
        data = event

    info = Info(**data)
    prediction = predict_day(model, info)
    return {"prediction": prediction, "warning": bool(prediction)}
