from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
import pickle
from predict import Info, predict_single

class PredictResponse(BaseModel):
    prediction: list[float]

try:
    with open("bin/model.bin", "rb") as f:
        model = pickle.load(f)


except FileNotFoundError:
    with open("model.bin", "rb") as f:
        model = pickle.load(f)


app = FastAPI(title="citi-bike")

@app.post("/predict")
def predict(info: Info) -> PredictResponse:
    prob = predict_single(model, info)

    return PredictResponse(
        prediction=prob
    )


if __name__ == "__main__":
    uvicorn.run("serve:app", host="0.0.0.0", port=1212, reload=True)