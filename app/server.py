from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from prometheus_fastapi_instrumentator import Instrumentator
from .schemas import CleanRequest, CleanResponse, ReviewRequest
from .pipeline import run_pipeline
from .review_queue import update as update_review, enqueue as enqueue_review, get_pending_reviews

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

MODEL_READY = True


@app.get('/healthz')
def healthz():
    return {'status': 'ok', 'model_loaded': MODEL_READY}


@app.post('/clean', response_model=CleanResponse)
async def clean(req: CleanRequest):
    result = await run_in_threadpool(
        run_pipeline,
        req.text,
        req.translate_embedded,
        req.terms,
        req.id,
    )
    if result.get("review_status") == "pending":
        enqueue_review(
            str(req.id or ""),
            {"text": req.text, "clean_text": result.get("clean_text"), "flags": result.get("flags"), "changes": result.get("changes")},
        )
    return CleanResponse(**result)


@app.post('/review/{item_id}')
async def review(item_id: str, body: ReviewRequest):
    """Human-in-the-loop review endpoint."""
    updated = update_review(item_id, approved=body.approved, correction=body.correction)
    return updated


@app.get('/reviews/pending')
async def pending_reviews():
    return get_pending_reviews()
