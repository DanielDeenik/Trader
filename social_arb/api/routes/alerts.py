"""Real-time alerts system: REST endpoints + WebSocket stream."""

import logging
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

# Global connection manager and alert engine instance
_connection_manager: Optional["ConnectionManager"] = None
_alert_engine: Optional["AlertEngine"] = None


def get_alert_engine():
    """Get or create the global alert engine instance."""
    global _alert_engine
    if _alert_engine is None:
        from social_arb.alerts.engine import AlertEngine
        _alert_engine = AlertEngine()
    return _alert_engine


def get_connection_manager():
    """Get or create the global connection manager."""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


class AlertModel(BaseModel):
    """Alert response schema."""
    id: str
    type: str
    symbol: str
    message: str
    severity: str  # info, warning, critical
    timestamp: str
    data: dict


class ThresholdsModel(BaseModel):
    """Threshold configuration schema."""
    thresholds: dict


class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept and store a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a closed WebSocket connection."""
        self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.active_connections)


@router.get("/alerts", response_model=list[AlertModel])
def list_alerts(
    limit: int = 50,
    alert_type: Optional[str] = None,
    symbol: Optional[str] = None,
):
    """
    Fetch recent alerts.

    Query parameters:
    - limit: max number of alerts (default 50, max 500)
    - alert_type: filter by type (high_confidence_signal, divergence_spike, thesis_approved, etc.)
    - symbol: filter by symbol
    """
    engine = get_alert_engine()
    alerts = engine.get_recent_alerts(limit=min(limit, 500))

    # Apply filters
    if alert_type:
        alerts = [a for a in alerts if a["type"] == alert_type]
    if symbol:
        alerts = [a for a in alerts if a["symbol"] == symbol]

    return alerts


@router.get("/alerts/thresholds")
def get_thresholds():
    """Get current alert thresholds."""
    engine = get_alert_engine()
    return {"thresholds": engine.get_thresholds()}


@router.put("/alerts/thresholds", response_model=dict)
def update_thresholds(body: ThresholdsModel):
    """
    Update alert thresholds.

    Example:
    {
      "thresholds": {
        "divergence_spike": 0.75,
        "high_confidence_signal": 0.85
      }
    }
    """
    engine = get_alert_engine()
    try:
        updated = engine.update_thresholds(body.thresholds)
        logger.info(f"Alert thresholds updated: {body.thresholds}")
        return {"thresholds": updated, "status": "updated"}
    except Exception as e:
        logger.error(f"Error updating thresholds: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/alerts")
def clear_alerts():
    """Clear all stored alerts."""
    engine = get_alert_engine()
    engine.clear_alerts()
    logger.info("All alerts cleared")
    return {"status": "cleared"}


@router.websocket("/alerts/ws")
async def websocket_alerts(websocket: WebSocket):
    """
    WebSocket endpoint for real-time alert streaming.

    Connect to: ws://host/api/v1/alerts/ws

    Messages received:
    - type: "subscribe" | "unsubscribe" | "ping"
    - symbol (optional): for symbol-specific alerts

    Messages sent:
    - type: "alert" - new alert
    - type: "connection_established" - on connect
    - type: "pong" - in response to ping
    """
    manager = get_connection_manager()
    await manager.connect(websocket)

    try:
        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to alert stream",
        })

        # Keep connection alive and listen for client messages
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            msg_type = msg.get("type", "ping")

            if msg_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })
            else:
                logger.debug(f"WebSocket message: {msg_type}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def publish_alert(alert: dict):
    """
    Publish an alert to all connected WebSocket clients.
    Called by other routes or pipeline to broadcast alerts.
    """
    manager = get_connection_manager()
    if manager.get_connection_count() > 0:
        await manager.broadcast({
            "type": "alert",
            **alert,
        })
