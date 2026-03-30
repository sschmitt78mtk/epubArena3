"""
API Config CRUD API for epubArena3
FastAPI APIRouter for API configuration management endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import json
import os

import config

# Create APIRouter
router = APIRouter(prefix="/api/configs", tags=["api_configs"])

# Mask string for API keys when displaying
MASKED_KEY = "••••••"
PARTIAL_MASK_LENGTH = 4  # Show last 4 characters

# Models for request/response
class APIConfigCreate(BaseModel):
    name: str
    OPENAI_API_BASE: str
    OPENAI_API_KEY: str
    OPEN_API_MODELNAME: str
    modelname: str

class APIConfigUpdate(BaseModel):
    name: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    OPEN_API_MODELNAME: Optional[str] = None
    modelname: Optional[str] = None

class APIConfigResponse(BaseModel):
    id: int  # index in the list
    name: str
    OPENAI_API_BASE: str
    OPENAI_API_KEY: str  # masked or partial
    OPEN_API_MODELNAME: str
    modelname: str

# Helper functions for API config CRUD operations
def load_api_configs() -> List[dict]:
    """Load API configs from JSON file"""
    if not os.path.exists(config.API_CONFIG_FILE):
        return []
    
    with open(config.API_CONFIG_FILE, 'r', encoding="utf-8") as f:
        return json.load(f)

def save_api_configs(configs: List[dict]) -> None:
    """Save API configs to JSON file"""
    with open(config.API_CONFIG_FILE, 'w', encoding="utf-8") as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)

def mask_api_key(key: str) -> str:
    """Mask API key for display (show last 4 chars)"""
    if not key:
        return ""
    if key == MASKED_KEY:
        return MASKED_KEY
    if len(key) <= 4:
        return MASKED_KEY
    # Show last 4 characters
    return f"{MASKED_KEY}{key[-4:]}"

def is_masked_key(key: str) -> bool:
    """Check if the key is masked (starts with mask)"""
    return key.startswith(MASKED_KEY)

def update_config_with_masking(existing_config: dict, update_data: dict) -> dict:
    """Update config while preserving masked API keys"""
    updated = existing_config.copy()
    
    for key, value in update_data.items():
        if value is not None:
            # Special handling for API key: if masked, keep original
            if key == "OPENAI_API_KEY" and is_masked_key(value):
                continue  # Keep existing key
            updated[key] = value
    
    return updated

def config_to_response(config_dict: dict, index: int) -> APIConfigResponse:
    """Convert config dict to Pydantic response model with masked key"""
    masked_key = mask_api_key(config_dict.get("OPENAI_API_KEY", ""))
    
    return APIConfigResponse(
        id=index,
        name=config_dict.get("name", ""),
        OPENAI_API_BASE=config_dict.get("OPENAI_API_BASE", ""),
        OPENAI_API_KEY=masked_key,
        OPEN_API_MODELNAME=config_dict.get("OPEN_API_MODELNAME", ""),
        modelname=config_dict.get("modelname", "")
    )

# CRUD Endpoints for API Configs
@router.get("/", response_model=List[APIConfigResponse])
async def list_api_configs():
    """Get all API configs (with masked API keys)"""
    configs = load_api_configs()
    return [config_to_response(c, i) for i, c in enumerate(configs)]

@router.get("/{config_id}", response_model=APIConfigResponse)
async def get_api_config(config_id: int):
    """Get a single API config by index ID"""
    configs = load_api_configs()
    if config_id < 0 or config_id >= len(configs):
        raise HTTPException(status_code=404, detail=f"API config with ID {config_id} not found")
    return config_to_response(configs[config_id], config_id)

@router.post("/", response_model=APIConfigResponse, status_code=201)
async def create_api_config(config_data: APIConfigCreate):
    """Create a new API config"""
    configs = load_api_configs()
    
    # Create new config dict
    new_config = {
        "name": config_data.name,
        "OPENAI_API_BASE": config_data.OPENAI_API_BASE,
        "OPENAI_API_KEY": config_data.OPENAI_API_KEY,
        "OPEN_API_MODELNAME": config_data.OPEN_API_MODELNAME,
        "modelname": config_data.modelname
    }
    
    # Add to list and save
    configs.append(new_config)
    save_api_configs(configs)
    
    # Return with masked key
    return config_to_response(new_config, len(configs) - 1)

@router.put("/{config_id}", response_model=APIConfigResponse)
async def update_api_config(config_id: int, config_data: APIConfigUpdate):
    """Update an existing API config"""
    configs = load_api_configs()
    if config_id < 0 or config_id >= len(configs):
        raise HTTPException(status_code=404, detail=f"API config with ID {config_id} not found")
    
    # Update config with masking handling
    updated_config = update_config_with_masking(configs[config_id], config_data.dict(exclude_unset=True))
    configs[config_id] = updated_config
    save_api_configs(configs)
    
    return config_to_response(updated_config, config_id)

@router.delete("/{config_id}", status_code=204)
async def delete_api_config(config_id: int):
    """Delete an API config by index ID"""
    configs = load_api_configs()
    if config_id < 0 or config_id >= len(configs):
        raise HTTPException(status_code=404, detail=f"API config with ID {config_id} not found")
    
    # Remove from list and save
    configs.pop(config_id)
    save_api_configs(configs)
    
    # 204 No Content response
    return None