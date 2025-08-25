"""
WebSocket connection handler for managing client connections and messages.
"""

import json
import asyncio
from typing import Dict, Any
from fastapi import WebSocket, WebSocketDisconnect
import logging

from .websocket_manager import WebSocketManager


class ConnectionHandler:
    """Handles individual WebSocket connections and message routing."""
    
    def __init__(self, websocket_manager: WebSocketManager):
        self.manager = websocket_manager
        self.logger = logging.getLogger(__name__)
    
    async def handle_connection(self, websocket: WebSocket, session_id: str = None):
        """Handle a WebSocket connection lifecycle."""
        await self.manager.connect(websocket, session_id)
        
        try:
            await self._send_welcome_message(websocket, session_id)
            
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Route message based on type
                await self._route_message(websocket, session_id, message)
                
        except WebSocketDisconnect:
            self.logger.info(f"WebSocket disconnected: {session_id}")
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {e}")
        finally:
            self.manager.disconnect(websocket, session_id)
    
    async def _send_welcome_message(self, websocket: WebSocket, session_id: str):
        """Send welcome message to newly connected client."""
        welcome_message = {
            "type": "welcome",
            "data": {
                "session_id": session_id,
                "message": "Connected to Red Team Dashboard",
                "connection_count": self.manager.get_connection_count(session_id)
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(welcome_message, websocket)
    
    async def _route_message(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Route incoming messages to appropriate handlers."""
        message_type = message.get("type")
        
        if message_type == "ping":
            await self._handle_ping(websocket, message)
        elif message_type == "subscribe":
            await self._handle_subscribe(websocket, session_id, message)
        elif message_type == "unsubscribe":
            await self._handle_unsubscribe(websocket, session_id, message)
        elif message_type == "get_status":
            await self._handle_get_status(websocket, session_id, message)
        else:
            await self._handle_unknown_message(websocket, message)
    
    async def _handle_ping(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle ping message from client."""
        pong_message = {
            "type": "pong",
            "data": {"timestamp": asyncio.get_event_loop().time()},
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(pong_message, websocket)
    
    async def _handle_subscribe(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle subscription to specific events."""
        subscription_type = message.get("data", {}).get("subscription")
        
        response = {
            "type": "subscription_confirmed",
            "data": {
                "subscription": subscription_type,
                "session_id": session_id
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(response, websocket)
    
    async def _handle_unsubscribe(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle unsubscription from events."""
        subscription_type = message.get("data", {}).get("subscription")
        
        response = {
            "type": "unsubscription_confirmed",
            "data": {
                "subscription": subscription_type,
                "session_id": session_id
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(response, websocket)
    
    async def _handle_get_status(self, websocket: WebSocket, session_id: str, message: Dict[str, Any]):
        """Handle status request."""
        status = {
            "type": "status_response",
            "data": {
                "session_id": session_id,
                "connection_count": self.manager.get_connection_count(session_id),
                "total_connections": self.manager.get_connection_count(),
                "active_sessions": self.manager.get_active_sessions()
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(status, websocket)
    
    async def _handle_unknown_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle unknown message types."""
        error_response = {
            "type": "error",
            "data": {
                "error": f"Unknown message type: {message.get('type')}",
                "received_message": message
            },
            "timestamp": asyncio.get_event_loop().time()
        }
        await self.manager.send_personal_message(error_response, websocket)
