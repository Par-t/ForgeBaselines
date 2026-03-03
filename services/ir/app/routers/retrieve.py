"""BM25 retrieval endpoint."""

from fastapi import APIRouter, HTTPException

from app.schemas.retrieval import RetrieveRequest, RetrieveResponse
from app.retrieval.runner import run_retrieval

router = APIRouter(tags=["retrieval"])


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve(request: RetrieveRequest):
    """Run BM25 retrieval and return IR metrics."""
    try:
        metrics, n_docs, n_queries = run_retrieval(
            corpus_path=request.corpus_path,
            queries_path=request.queries_path,
            text_column=request.text_column,
            k_values=request.k_values,
            experiment_id=request.experiment_id,
            user_id=request.user_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Missing required column: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    return RetrieveResponse(
        experiment_id=request.experiment_id,
        user_id=request.user_id,
        metrics=metrics,
        n_docs=n_docs,
        n_queries=n_queries,
    )
