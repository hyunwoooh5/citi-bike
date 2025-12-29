import pickle

import pandas as pd
import xgboost as xgb


def train(df, seed=42):
    features = [col for col in df.columns if col != "target_next_stock"]

    X = df[features]
    y = df["target_next_stock"]

    model = xgb.XGBRegressor(
        random_state=seed,
        enable_categorical=True,
        n_estimators=58,
        max_depth=6,
        learning_rate=0.2089,
    )

    model.fit(X, y)

    return model


if __name__ == "__main__":
    df = pd.read_csv("data/2024_top3_fe.csv")
    df["station"] = df["station"].astype("category")
    df["rideable_type"] = df["rideable_type"].astype("category")

    model = train(df)

    with open("bin/model.bin", "wb") as f_out:
        pickle.dump(model, f_out)
