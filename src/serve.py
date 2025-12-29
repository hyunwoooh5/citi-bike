import pickle

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from predict import Info, predict_day


class PredictResponse(BaseModel):
    prediction: list[str]
    warning: bool


try:
    with open("bin/model.bin", "rb") as f:
        model = pickle.load(f)


except FileNotFoundError:
    with open("model.bin", "rb") as f:
        model = pickle.load(f)


app = FastAPI(title="citi-bike")


@app.post("/predict")
def predict(info: Info) -> PredictResponse:
    prediction = predict_day(model, info)

    return PredictResponse(prediction=prediction, warning=bool(prediction))


@app.get("/health")  # check if the app works
def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("serve:app", host="0.0.0.0", port=9696, reload=True)
