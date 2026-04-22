"""API routes for task queue management."""

import json
import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException, Request
from social_arb.api.schemas import TaskCreate
from social_arb.api.deps import get_db_path
from social_arb.db import store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/tasks")
async def create_task(req: TaskCreate, request: Request):
    """Enqueue a new task."""
    try:
        queue = request.app.state.queue
        task_id = await queue.enqueue(
            task_type=req.task_type,
            params=req.params,
            max_attempts=req.max_attempts,
        )
        logger.info(f"Enqueued task id={task_id} type={req.task_type}")
        return {"task_id": task_id, "status": "pending"}
    except Exception as e:
        logger.error(f"Failed to enqueue task: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List tasks with optional status filter."""
    db_path = get_db_path()
    try:
        if status:
            tasks = store.query_tasks_by_status(status=status, limit=limit, db_path=db_path)
        else:
            tasks = store.query_tasks(limit=limit, db_path=db_path)
        return {"tasks": tasks, "total_count": len(tasks)}
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """Get status of a specific task."""
    db_path = get_db_path()
    try:
        tasks = store.query_tasks(db_path=db_path)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: int):
    """Cancel a pending task."""
    db_path = get_db_path()
    try:
        tasks = store.query_tasks(db_path=db_path)
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        if task["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail=f"Can only cancel pending tasks, this is {task['status']}",
            )
        store.fail_task(task_id=task_id, error="Cancelled by user", db_path=db_path)
        return {"task_id": task_id, "status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-health")
async def get_source_health(
    hours: int = Query(24, ge=1, le=720),
):
    """Get per-source health metrics."""
    db_path = get_db_path()
    try:
        health = store.query_source_health(hours=hours, db_path=db_path)
        return {
            "sources": health,
            "total_sources": len(health),
            "as_of": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get source health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
