from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/analyzer")

class AnalyzeRequest(BaseModel):
    data: dict

@router.post("/predict")
def predict(_: AnalyzeRequest):
    return {"status": "ok"}
