from fastapi import FastAPI
from .schemas import CleanRequest, CleanResponse
from .pipeline import run_pipeline

app = FastAPI()
MODEL_READY = True


@app.get('/healthz')
def healthz():
    return {'status': 'ok', 'model_loaded': MODEL_READY}


@app.post('/clean', response_model=CleanResponse)
def clean(req: CleanRequest):
    result = run_pipeline(req.text, terms=req.terms, translate_embedded=req.translate_embedded)
    return CleanResponse(**result)
