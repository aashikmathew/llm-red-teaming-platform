"""
WebSocket manager for real-time communication with frontend.
"""

import json
import asyncio
from typing import Dict, List, Set, Any
from fastapi import WebSocket, WebSocketDisconnect
import logging


class WebSocketManager:
    """Manages WebSocket connections and real-time communication."""
    
    def __init__(self):
        # Active connections per session
        self.connections: Dict[str, Set[WebSocket]] = {}
        # All active connections
        self.active_connections: Set[WebSocket] = set()
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket, session_id: str = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if session_id:
            if session_id not in self.connections:
                self.connections[session_id] = set()
            self.connections[session_id].add(websocket)
        
        self.logger.info(f"WebSocket connected. Session: {session_id}, Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket, session_id: str = None):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        
        if session_id and session_id in self.connections:
            self.connections[session_id].discard(websocket)
            if not self.connections[session_id]:
                del self.connections[session_id]
        
        self.logger.info(f"WebSocket disconnected. Session: {session_id}, Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Error sending personal message: {e}")
            self.active_connections.discard(websocket)
    
    async def send_to_session(self, session_id: str, message: dict):
        """Send a message to all connections in a session."""
        if session_id not in self.connections:
            return
        
        disconnected = set()
        for connection in self.connections[session_id].copy():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Error sending to session {session_id}: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection, session_id)
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all active connections."""
        disconnected = set()
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Error broadcasting: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_progress_update(self, session_id: str, data: Dict[str, Any]):
        """Send a progress update for a specific session."""
        message = {
            "type": "progress_update",
            "session_id": session_id,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_session(session_id, message)
    
    async def send_test_result(self, session_id: str, result_data: Dict[str, Any]):
        """Send individual test result update."""
        message = {
            "type": "test_result",
            "session_id": session_id,
            "data": result_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_session(session_id, message)
    
    async def send_session_complete(self, session_id: str, final_data: Dict[str, Any]):
        """Send session completion notification."""
        message = {
            "type": "session_complete",
            "session_id": session_id,
            "data": final_data,
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_session(session_id, message)
    
    async def send_error(self, session_id: str, error_message: str):
        """Send error message to session."""
        message = {
            "type": "error",
            "session_id": session_id,
            "data": {"error": error_message},
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.send_to_session(session_id, message)
    
    def get_connection_count(self, session_id: str = None) -> int:
        """Get number of active connections."""
        if session_id:
            return len(self.connections.get(session_id, set()))
        return len(self.active_connections)
    
    def get_active_sessions(self) -> List[str]:
        """Get list of sessions with active connections."""
        return list(self.connections.keys())
