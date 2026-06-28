from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
import asyncio
import logging

from backend.app.database import get_db
from backend.app.models_db import DBRating, DBMovie
from backend.app.cache import cache_dec
from backend.app.ws_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Feed"])


def get_sync_payload(db: Session) -> dict:
    from backend.app.main import app
    
    # 1. Fetch stats
    db_ratings_count = db.query(DBRating).count()
    db_movies_count = db.query(DBMovie).filter(DBMovie.is_active == True).count()
    total_ratings = len(getattr(app.state, "ratings_df", []))
    total_users = len(getattr(app.state.col_model, "user_mapper", {})) if hasattr(app.state, "col_model") else 0
    svd_components = getattr(app.state.col_model, "n_factors", 50) if hasattr(app.state, "col_model") else 50
    
    # Check if app.state.cache exists and has metrics
    metrics = {"rmse": 0.0, "ndcg_10": 0.0, "map_10": 0.0}
    if hasattr(app.state, "cache") and "metrics" in app.state.cache:
        metrics = {
            "rmse": float(app.state.cache["metrics"].get("rmse", 0.0)),
            "ndcg_10": float(app.state.cache["metrics"].get("ndcg_10", 0.0)),
            "map_10": float(app.state.cache["metrics"].get("map_10", 0.0)),
        }
        
    stats = {
        "total_ratings": total_ratings,
        "live_ratings": db_ratings_count,
        "users_count": total_users,
        "movies_count": db_movies_count,
        "svd_components": svd_components,
        "metrics": metrics,
    }
    
    # 2. Fetch recent feed (limit 15)
    results = (
        db.query(DBRating, DBMovie)
        .join(DBMovie, DBRating.movieId == DBMovie.movieId)
        .order_by(DBRating.timestamp.desc())
        .limit(15)
        .all()
    )
    
    feed = [
        {
            "id": r.id,
            "userId": r.userId,
            "movieId": r.movieId,
            "title": m.title,
            "rating": r.rating,
            "timestamp": r.timestamp,
        }
        for r, m in results
    ]
    
    return {
        "type": "sync",
        "stats": stats,
        "feed": feed
    }


async def broadcast_system_update(db: Session):
    payload = get_sync_payload(db)
    await manager.broadcast(payload)


def trigger_broadcast_update(db: Session):
    """
    Sync helper to broadcast system updates to all active WebSocket clients.
    Handles running event loops gracefully.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast_system_update(db))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(broadcast_system_update(db))


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket, db: Session = Depends(get_db)):
    await manager.connect(websocket)
    try:
        # Send initial data immediately upon connection
        initial_payload = get_sync_payload(db)
        await websocket.send_json(initial_payload)
        # Keep connection open
        while True:
            # Wait for any text (client can send keepalive pings)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        manager.disconnect(websocket)



@router.get("/stats")
@cache_dec("stats", maxsize=16, ttl=300)
def get_stats(request: Request, db: Session = Depends(get_db)):
    """Returns SVD model diagnostics, rating counts, and evaluation metrics."""
    from backend.app.main import app

    db_ratings_count = db.query(DBRating).count()
    db_movies_count = db.query(DBMovie).filter(DBMovie.is_active == True).count()
    total_ratings = len(app.state.ratings_df)
    total_users = len(app.state.col_model.user_mapper)

    return {
        "total_ratings": total_ratings,
        "live_ratings": db_ratings_count,
        "users_count": total_users,
        "movies_count": db_movies_count,
        "svd_components": app.state.col_model.n_factors,
        "metrics": {
            "rmse": float(app.state.cache["metrics"]["rmse"]),
            "ndcg_10": float(app.state.cache["metrics"]["ndcg_10"]),
            "map_10": float(app.state.cache["metrics"]["map_10"]),
        },
    }


@router.get("/feed")
def get_global_feed(request: Request, db: Session = Depends(get_db), limit: int = 10, page: int = 1):
    """Returns paginated live rating activity from all users (network stream).

    Args:
        limit: Entries per page (max 50).
        page:  Page number (1-indexed).
    """
    limit = min(limit, 50)
    offset = (page - 1) * limit

    results = (
        db.query(DBRating, DBMovie)
        .join(DBMovie, DBRating.movieId == DBMovie.movieId)
        .order_by(DBRating.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    total = db.query(DBRating).count()
    feed = [
        {
            "id": r.id,
            "userId": r.userId,
            "movieId": r.movieId,
            "title": m.title,
            "rating": r.rating,
            "timestamp": r.timestamp,
        }
        for r, m in results
    ]

    return {"page": page, "limit": limit, "total": total, "results": feed}
