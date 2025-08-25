"""
LLM Red Teaming System - Main FastAPI Application

A comprehensive red teaming system for evaluating Large Language Models
with real-time visualization and automated assessment capabilities.
"""

import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from fastapi import FastAPI, WebSocket, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our modules
from src.llm_providers import (
    OpenAIProvider, AnthropicProvider, GoogleProvider, HuggingFaceProvider
)
from src.red_team import RedTeamEngine, PromptCategory, PromptCategories, AttackPrompts
from src.assessment import AssessmentEngine, MetricsCalculator, ReportGenerator
from src.websocket import WebSocketManager, ConnectionHandler

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="LLM Red Teaming System",
    description="Automated red team testing for Large Language Models",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize components
websocket_manager = WebSocketManager()
connection_handler = ConnectionHandler(websocket_manager)
red_team_engine = RedTeamEngine()
assessment_engine = AssessmentEngine()

# Global state
active_sessions: Dict[str, Any] = {}


# Pydantic models
class ProviderConfig(BaseModel):
    provider: str
    model: str
    api_key: str


class AssessmentConfig(BaseModel):
    categories: List[str]
    temperature: float = 0.7
    max_tokens: int = 1000
    prompts_per_category: Optional[int] = None


class StartAssessmentRequest(BaseModel):
    provider_config: ProviderConfig
    assessment_config: AssessmentConfig


# Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "title": "LLM Red Teaming Dashboard"
    })


@app.get("/api/providers")
async def get_providers():
    """Get available LLM providers and their models."""
    providers = {
        "openai": {
            "name": "OpenAI",
            "models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview", "gpt-4o-mini"]
        },
        "anthropic": {
            "name": "Anthropic",
            "models": ["claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-haiku-20240307", "claude-3-5-sonnet-20241022"]
        },
        "google": {
            "name": "Google",
            "models": ["gemini-pro", "gemini-pro-vision", "gemini-1.5-pro", "gemini-1.5-flash"]
        },
        "huggingface": {
            "name": "HuggingFace",
            "models": ["microsoft/DialoGPT-medium", "microsoft/DialoGPT-large", "facebook/blenderbot-400M-distill", "EleutherAI/gpt-j-6B"]
        }
    }
    return providers


@app.get("/api/categories")
async def get_categories():
    """Get available red team testing categories."""
    categories = {}
    for category in PromptCategories.get_all_categories():
        info = PromptCategories.get_category_info(category)
        categories[category.value] = {
            "name": info.name,
            "description": info.description,
            "risk_level": info.risk_level,
            "prompt_count": len(AttackPrompts.get_prompts_by_category(category)),
            "examples": info.examples[:2]  # First 2 examples
        }
    return categories


@app.post("/api/test-connection")
async def test_connection(config: ProviderConfig):
    """Test connection to LLM provider."""
    try:
        provider = create_provider(config)
        success = await provider.test_connection()
        
        return {
            "success": success,
            "message": "Connection successful" if success else "Connection failed",
            "provider": config.provider,
            "model": config.model
        }
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}",
            "provider": config.provider,
            "model": config.model
        }


@app.post("/api/start-assessment")
async def start_assessment(request: StartAssessmentRequest):
    """Start a new red team assessment."""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Create provider
        provider = create_provider(request.provider_config)
        
        # Test connection first
        if not await provider.test_connection():
            raise HTTPException(status_code=400, detail="Failed to connect to LLM provider")
        
        # Convert category strings to enums
        categories = []
        for cat_name in request.assessment_config.categories:
            try:
                category = PromptCategories.get_category_by_name(cat_name)
                categories.append(category)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Unknown category: {cat_name}")
        
        # Store session info
        active_sessions[session_id] = {
            "provider_config": request.provider_config.dict(),
            "assessment_config": request.assessment_config.dict(),
            "start_time": datetime.now(),
            "status": "starting"
        }
        
        # Set up progress callback
        async def progress_callback(session_id: str, data: Dict[str, Any]):
            await websocket_manager.send_progress_update(session_id, data)
        
        red_team_engine.add_progress_callback(progress_callback)
        
        # Start assessment in background
        asyncio.create_task(run_assessment_async(
            session_id, provider, categories, request.assessment_config
        ))
        
        return {
            "session_id": session_id,
            "message": "Assessment started successfully",
            "total_prompts": sum(
                len(AttackPrompts.get_prompts_by_category(cat)[:request.assessment_config.prompts_per_category])
                for cat in categories
            )
        }
        
    except Exception as e:
        logger.error(f"Failed to start assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}")
async def get_session_status(session_id: str):
    """Get status of a specific session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_info = active_sessions[session_id]
    red_team_session = red_team_engine.get_session(session_id)
    
    status = {
        "session_id": session_id,
        "status": session_info["status"],
        "start_time": session_info["start_time"].isoformat(),
        "provider": session_info["provider_config"]["provider"],
        "model": session_info["provider_config"]["model"]
    }
    
    if red_team_session:
        status.update({
            "total_prompts": red_team_session.total_prompts,
            "completed_prompts": red_team_session.completed_prompts,
            "progress_percentage": (red_team_session.completed_prompts / red_team_session.total_prompts * 100) if red_team_session.total_prompts > 0 else 0,
            "is_complete": red_team_session.is_complete,
            "duration_seconds": red_team_session.duration_seconds
        })
    
    return status


@app.get("/api/session/{session_id}/results")
async def get_session_results(session_id: str):
    """Get assessment results for a session."""
    red_team_session = red_team_engine.get_session(session_id)
    
    if not red_team_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not red_team_session.is_complete:
        raise HTTPException(status_code=400, detail="Assessment not yet complete")
    
    # Generate comprehensive assessment
    assessment = assessment_engine.generate_assessment(red_team_session)
    
    return assessment.to_dict()


@app.get("/api/session/{session_id}/report")
async def download_report(session_id: str):
    """Download PDF report for a completed assessment session."""
    
    red_team_session = red_team_engine.get_session(session_id)
    
    if not red_team_session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not red_team_session.is_complete:
        raise HTTPException(status_code=400, detail="Assessment not yet complete")
    
    try:
        # Generate comprehensive assessment
        assessment = assessment_engine.generate_assessment(red_team_session)
        
        # Create reports directory if it doesn't exist
        reports_dir = "reports"
        os.makedirs(reports_dir, exist_ok=True)
        
        # Generate report filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"red-team-assessment-{session_id}-{timestamp}.pdf"
        filepath = os.path.join(reports_dir, filename)
        
        # Generate PDF report
        report_generator = ReportGenerator()
        generated_path = report_generator.generate_report(assessment, filepath)
        
        # Return the file for download
        return FileResponse(
            path=generated_path,
            filename=filename,
            media_type='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Failed to generate report for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates."""
    await connection_handler.handle_connection(websocket, session_id)


@app.get("/api/sessions")
async def get_all_sessions():
    """Get all assessment sessions."""
    sessions = []
    for session_id, session_info in active_sessions.items():
        red_team_session = red_team_engine.get_session(session_id)
        
        session_data = {
            "session_id": session_id,
            "status": session_info["status"],
            "start_time": session_info["start_time"].isoformat(),
            "provider": session_info["provider_config"]["provider"],
            "model": session_info["provider_config"]["model"]
        }
        
        if red_team_session:
            session_data.update({
                "total_prompts": red_team_session.total_prompts,
                "completed_prompts": red_team_session.completed_prompts,
                "is_complete": red_team_session.is_complete
            })
        
        sessions.append(session_data)
    
    return {"sessions": sessions}


def create_provider(config: ProviderConfig):
    """Create LLM provider instance based on configuration."""
    provider_classes = {
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "google": GoogleProvider,
        "huggingface": HuggingFaceProvider
    }
    
    if config.provider not in provider_classes:
        raise ValueError(f"Unknown provider: {config.provider}")
    
    provider_class = provider_classes[config.provider]
    return provider_class(config.api_key, config.model)


async def run_assessment_async(
    session_id: str,
    provider,
    categories: List[PromptCategory],
    config: AssessmentConfig
):
    """Run assessment asynchronously in background."""
    try:
        active_sessions[session_id]["status"] = "running"
        
        # Start red team assessment
        session = await red_team_engine.start_assessment(
            session_id=session_id,
            provider=provider,
            categories=categories,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            prompts_per_category=config.prompts_per_category
        )
        
        # Generate assessment
        assessment = assessment_engine.generate_assessment(session)
        
        # Update session status
        active_sessions[session_id]["status"] = "completed"
        active_sessions[session_id]["assessment"] = assessment.to_dict()
        
        # Notify completion
        await websocket_manager.send_session_complete(session_id, {
            "assessment_summary": {
                "total_prompts": assessment.metrics.total_prompts,
                "safeguard_success_rate": assessment.metrics.overall_safeguard_success_rate,
                "vulnerability_score": assessment.metrics.overall_vulnerability_score,
                "risk_level": assessment.findings.risk_level
            }
        })
        
        logger.info(f"Assessment completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Assessment failed for session {session_id}: {e}")
        active_sessions[session_id]["status"] = "failed"
        active_sessions[session_id]["error"] = str(e)
        
        await websocket_manager.send_error(session_id, str(e))


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
