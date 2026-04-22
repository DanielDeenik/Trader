"""Scheduler status and control API routes."""

import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])

# Valid schedule names that can be triggered or configured
VALID_SCHEDULES = {
    "collect", "analyze", "train_stepps", "private_collect", "enrich_sentiment",
}

# Manual trigger dispatchers — maps schedule name to the scheduler method that creates its task
TRIGGER_METHODS = {
    "collect": "_create_collect_task",
    "analyze": "_create_analyze_task",
    "train_stepps": "_create_train_stepps_task",
    "private_collect": "_create_private_collect_task",
    "enrich_sentiment": "_create_enrich_sentiment_task",
}


class TriggerRequest(BaseModel):
    schedule_name: str


class IntervalUpdateRequest(BaseModel):
    schedule_name: str
    interval_seconds: int = Field(ge=60, description="Minimum 60 seconds")


@router.get("/status")
async def get_scheduler_status(request: Request):
    """Get current scheduler status and schedule configuration."""
    scheduler = request.app.state.scheduler
    return scheduler.get_status()


@router.post("/trigger")
async def trigger_schedule(req: TriggerRequest, request: Request):
    """Manually trigger a scheduled task immediately."""
    if req.schedule_name not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule: {req.schedule_name}. Valid: {sorted(VALID_SCHEDULES)}",
        )

    scheduler = request.app.state.scheduler
    method_name = TRIGGER_METHODS[req.schedule_name]

    try:
        method = getattr(scheduler, method_name)
        await method()
        logger.info(f"Manually triggered schedule: {req.schedule_name}")
        return {"triggered": req.schedule_name, "status": "enqueued"}
    except Exception as e:
        logger.error(f"Failed to trigger {req.schedule_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/interval")
async def update_interval(req: IntervalUpdateRequest, request: Request):
    """Update the interval for a scheduled task."""
    if req.schedule_name not in VALID_SCHEDULES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid schedule: {req.schedule_name}. Valid: {sorted(VALID_SCHEDULES)}",
        )

    scheduler = request.app.state.scheduler
    try:
        scheduler.update_interval(req.schedule_name, req.interval_seconds)
        return {
            "schedule_name": req.schedule_name,
            "interval_seconds": req.interval_seconds,
            "status": "updated",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
