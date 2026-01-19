"""
model_routes.py - VIO Model Management Routes

Handles model switching using VIO's native /set_ai_model API endpoint.
No LiteLLM proxy - uses original VIO Cloud integration.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import requests
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model")


# VIO API Configuration
VIO_API_BASE = os.getenv("VIO_BASE_URL", "https://vio.automotive-wan.com:446")
VIO_USERNAME = os.getenv("VIO_USERNAME", "uih62283")
VIO_TOKEN = os.getenv("VIO_API_TOKEN")
VIO_VERIFY_SSL = os.getenv("VIO_VERIFY_SSL", "false").lower() == "true"


# Request/Response Models
class ModelSwitchRequest(BaseModel):
    vision_model: str


class ModelResponse(BaseModel):
    success: bool
    current_model: Optional[str] = None
    message: Optional[str] = None


class AvailableModelsResponse(BaseModel):
    success: bool
    models: List[Dict[str, str]]


# All available VIO models
VIO_MODELS = [
    # Vision & Image Models
    {"key": "pixtral-large", "name": "Pixtral Large", "category": "vision", "description": "Image understanding"},
    {"key": "gpt-5", "name": "GPT-5", "category": "vision", "description": "Image understanding"},
    {"key": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "category": "agentic", "description": "Agentic AI usage"},
    {"key": "claude-4.5-sonnet", "name": "Claude 4.5 Sonnet", "category": "vision", "description": "Advanced vision"},
    {"key": "claude-3.7-sonnet", "name": "Claude 3.7 Sonnet", "category": "vision", "description": "Vision capable"},
    {"key": "claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "category": "general", "description": "Balanced"},
    
    # Reasoning Models
    {"key": "deepseek-r1", "name": "DeepSeek R1", "category": "reasoning", "description": "Deep reasoning"},
    {"key": "grok-4-fast-non-reasoning", "name": "Grok-4-fast-non-reasoning", "category": "fast", "description": "Fast responses"},
    {"key": "phi-4-reasoning", "name": "Phi-4-reasoning", "category": "reasoning", "description": "Reasoning focused"},
    
    # Fast Models
    {"key": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "category": "fast", "description": "Very fast"},
    {"key": "gpt-5-mini", "name": "GPT 5-mini", "category": "fast", "description": "Fast GPT"},
    {"key": "gpt-5-nano", "name": "GPT 5-nano", "category": "fast", "description": "Ultra fast"},
    {"key": "nova-lite", "name": "Nova Lite", "category": "fast", "description": "Lightweight"},
    {"key": "nova-micro", "name": "Nova Micro", "category": "fast", "description": "Minimal"},
    
    # GPT Family
    {"key": "gpt-5-chat", "name": "GPT 5-chat", "category": "general", "description": "Chat optimized"},
    {"key": "gpt-5-high", "name": "GPT-5-high", "category": "general", "description": "High quality"},
    {"key": "gpt-5-low", "name": "GPT-5-low", "category": "general", "description": "Low cost"},
    {"key": "gpt-5-medium", "name": "GPT-5-medium", "category": "general", "description": "Balanced"},
    {"key": "gpt-4o", "name": "GPT-4o", "category": "general", "description": "GPT-4 optimized"},
    {"key": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "category": "fast", "description": "Fast and efficient"},
    {"key": "gpt-o3-mini", "name": "GPT-o3-mini", "category": "fast", "description": "Compact GPT"},
    {"key": "gpt-oss-120b", "name": "GPT-OSS-120B", "category": "general", "description": "Open source"},
    {"key": "gpt-oss-20b", "name": "GPT-OSS-20B", "category": "general", "description": "Open source"},
    {"key": "gpt-5.1", "name": "Gpt-5.1", "category": "general", "description": "Latest GPT"},
    
    # LLaMA Family
    {"key": "llama-3.1-8b", "name": "LLaMA 3.1 8B", "category": "general", "description": "Efficient"},
    {"key": "llama3-405b", "name": "Llama3 405B", "category": "general", "description": "Very large"},
    {"key": "meta-llama-3.3-70b", "name": "Meta LLaMA 3.3 70B", "category": "general", "description": "Meta's latest"},
    
    # Mistral Family
    {"key": "mistral-large-2", "name": "Mistral Large 2", "category": "general", "description": "Large model"},
    {"key": "mistral-large-2402", "name": "Mistral Large 2402", "category": "general", "description": "Latest version"},
    
    # Nova Family
    {"key": "nova-premier", "name": "Nova Premier", "category": "general", "description": "Premium model"},
    {"key": "nova-pro-v1", "name": "Nova Pro v1", "category": "general", "description": "Professional"},
    
    # Qwen Family
    {"key": "qwen-3.5-235b", "name": "Qwen 3.5 235B", "category": "general", "description": "Very large Chinese model"},
    {"key": "qwen3-coder-480b-a35b-v1", "name": "Qwen3-coder-480b-a35b-v1", "category": "code", "description": "Coding specialist"},
    
    # Other Models
    {"key": "mai-ds-r1", "name": "MAI-DS-R1", "category": "general", "description": "Specialized model"},
    {"key": "grok-3", "name": "Grok-3", "category": "general", "description": "Grok model"},
]


# Current model state (in-memory)
current_vision_model = "Gemini 2.5 Pro"  # Default


@router.get("/current", response_model=ModelResponse)
async def get_current_model():
    """Get the currently active vision model."""
    return ModelResponse(
        success=True,
        current_model=current_vision_model,
        message=f"Current model: {current_vision_model}"
    )


@router.post("/switch", response_model=ModelResponse)
async def switch_model(request: ModelSwitchRequest):
    """
    Switch the vision model using VIO's /set_ai_model API.
    
    This calls VIO's native model switching endpoint.
    """
    global current_vision_model
    
    # Find the model in our list
    model_found = None
    for model in VIO_MODELS:
        if model["key"] == request.vision_model or model["name"] == request.vision_model:
            model_found = model
            break
    
    if not model_found:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{request.vision_model}' not found in available models"
        )
    
    # Prepare VIO API request
    vio_url = f"{VIO_API_BASE}/set_ai_model"
    vio_payload = {
        "username": VIO_USERNAME,
        "token": VIO_TOKEN,
        "type": "SET_AI_MODEL",
        "name": model_found["name"]  # VIO API expects the full name
    }
    
    try:
        logger.info(f"Switching VIO model to: {model_found['name']}")
        
        # Call VIO API
        response = requests.post(
            vio_url,
            json=vio_payload,
            verify=VIO_VERIFY_SSL,
            timeout=10
        )
        
        if response.status_code == 200:
            current_vision_model = model_found["name"]
            logger.info(f"✅ VIO model switched successfully to: {model_found['name']}")
            
            return ModelResponse(
                success=True,
                current_model=current_vision_model,
                message=f"Successfully switched to {model_found['name']}"
            )
        else:
            error_msg = f"VIO API returned status {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
            
    except requests.RequestException as e:
        error_msg = f"Failed to connect to VIO API: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/available", response_model=AvailableModelsResponse)
async def get_available_models():
    """Get list of all available VIO models."""
    return AvailableModelsResponse(
        success=True,
        models=VIO_MODELS
    )


@router.post("/scenario")
async def apply_scenario(scenario: str):
    """Apply a predefined model scenario."""
    scenarios = {
        "vision": "pixtral-large",
        "agentic": "gemini-2.5-pro", 
        "fast": "gemini-2.0-flash",
        "balanced": "claude-4.5-sonnet",
        "reasoning": "deepseek-r1"
    }
    
    if scenario not in scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario}")
    
    model_key = scenarios[scenario]
    return await switch_model(ModelSwitchRequest(vision_model=model_key))