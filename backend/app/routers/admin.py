"""Admin router — trigger batch retraining and SVD updates."""
from fastapi import APIRouter, Depends, HTTPException, Request
from backend.app.dependencies import get_current_user_optional
from backend.src.retrain import retrain_model_pipeline

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.post("/retrain")
def trigger_retrain(request: Request, current_user: str = Depends(get_current_user_optional)):
    """Triggers offline model retraining and atomically updates the server state."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Authentication required.",
        )
    
    from backend.app.main import app
    try:
        new_cache = retrain_model_pipeline(app=app)
        return {
            "message": "Retraining completed successfully and server state updated atomically.",
            "metrics": {
                "rmse": float(new_cache["metrics"]["rmse"]),
                "mae": float(new_cache["metrics"]["mae"]),
                "map_10": float(new_cache["metrics"]["map_10"]),
                "ndcg_10": float(new_cache["metrics"]["ndcg_10"]),
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")
