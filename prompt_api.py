"""
Prompt CRUD API for epubArena3
FastAPI APIRouter for prompt management endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import config
from prompts import Promptset, load_promptsets, save_promptsets

# Create APIRouter
router = APIRouter(prefix="/api/prompts", tags=["prompts"])

# Models for request/response
class PromptCreate(BaseModel):
    system_message: str
    prePrompt: str = ""
    postPrompt: str = ""
    infostr: str = ""
    allowLongAnswer: bool = True
    temperature: float = 0.2
    top_p: float = 0.8
    maxNewToken: int = 500
    targetlanguage: str = "DE"
    AIasJudge: bool = False

class PromptUpdate(BaseModel):
    system_message: Optional[str] = None
    prePrompt: Optional[str] = None
    postPrompt: Optional[str] = None
    infostr: Optional[str] = None
    allowLongAnswer: Optional[bool] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    maxNewToken: Optional[int] = None
    targetlanguage: Optional[str] = None
    AIasJudge: Optional[bool] = None

class PromptResponse(BaseModel):
    PromptID: int
    system_message: str
    prePrompt: str
    postPrompt: str
    infostr: str
    allowLongAnswer: bool
    temperature: float
    top_p: float
    maxNewToken: int
    targetlanguage: str
    AIasJudge: bool

# Helper functions for prompt CRUD operations
def get_next_prompt_id() -> int:
    """Get next unique PromptID (max existing + 1)"""
    if not config.all_promptset:
        return 0
    return max(p.PromptID for p in config.all_promptset) + 1

def get_prompt_by_id(prompt_id: int) -> Optional[Promptset]:
    """Find prompt by PromptID"""
    for prompt in config.all_promptset:
        if prompt.PromptID == prompt_id:
            return prompt
    return None

def save_all_prompts() -> None:
    """Save current prompts to JSON file and update config"""
    save_promptsets(config.all_promptset, str(config.PROMPTS_JSON_FILE))
    config.all_promptset = load_promptsets(str(config.PROMPTS_JSON_FILE))

def prompt_to_response(prompt: Promptset) -> PromptResponse:
    """Convert Promptset to Pydantic response model"""
    return PromptResponse(
        PromptID=prompt.PromptID,
        system_message=prompt.system_message,
        prePrompt=prompt.prePrompt,
        postPrompt=prompt.postPrompt,
        infostr=prompt.infostr,
        allowLongAnswer=prompt.allowLongAnswer,
        temperature=prompt.temperature,
        top_p=prompt.top_p,
        maxNewToken=prompt.maxNewToken,
        targetlanguage=prompt.targetlanguage,
        AIasJudge=prompt.AIasJudge
    )

# CRUD Endpoints for Prompts
@router.get("/", response_model=List[PromptResponse])
async def list_prompts():
    """Get all prompts"""
    return [prompt_to_response(p) for p in config.all_promptset]

@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(prompt_id: int):
    """Get a single prompt by ID"""
    prompt = get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt with ID {prompt_id} not found")
    return prompt_to_response(prompt)

@router.post("/", response_model=PromptResponse, status_code=201)
async def create_prompt(prompt_data: PromptCreate):
    """Create a new prompt with auto-generated ID"""
    # Create new Promptset with auto-generated ID
    new_id = get_next_prompt_id()
    prompt = Promptset(
        PromptID=new_id,
        system_message=prompt_data.system_message,
        prePrompt=prompt_data.prePrompt,
        postPrompt=prompt_data.postPrompt,
        infostr=prompt_data.infostr,
        allowLongAnswer=prompt_data.allowLongAnswer,
        temperature=prompt_data.temperature,
        top_p=prompt_data.top_p,
        maxNewToken=prompt_data.maxNewToken,
        targetlanguage=prompt_data.targetlanguage,
        AIasJudge=prompt_data.AIasJudge
    )
    
    # Add to list and save
    config.all_promptset.append(prompt)
    save_all_prompts()
    
    return prompt_to_response(prompt)

@router.put("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(prompt_id: int, prompt_data: PromptUpdate):
    """Update an existing prompt"""
    prompt = get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt with ID {prompt_id} not found")
    
    # Update fields if provided
    if prompt_data.system_message is not None:
        prompt.system_message = prompt_data.system_message
    if prompt_data.prePrompt is not None:
        prompt.prePrompt = prompt_data.prePrompt
    if prompt_data.postPrompt is not None:
        prompt.postPrompt = prompt_data.postPrompt
    if prompt_data.infostr is not None:
        prompt.infostr = prompt_data.infostr
    if prompt_data.allowLongAnswer is not None:
        prompt.allowLongAnswer = prompt_data.allowLongAnswer
    if prompt_data.temperature is not None:
        prompt.temperature = prompt_data.temperature
    if prompt_data.top_p is not None:
        prompt.top_p = prompt_data.top_p
    if prompt_data.maxNewToken is not None:
        prompt.maxNewToken = prompt_data.maxNewToken
    if prompt_data.targetlanguage is not None:
        prompt.targetlanguage = prompt_data.targetlanguage
    if prompt_data.AIasJudge is not None:
        prompt.AIasJudge = prompt_data.AIasJudge
    
    save_all_prompts()
    return prompt_to_response(prompt)

@router.delete("/{prompt_id}", status_code=204)
async def delete_prompt(prompt_id: int):
    """Delete a prompt by ID"""
    prompt = get_prompt_by_id(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt with ID {prompt_id} not found")
    
    # Remove from list and save
    config.all_promptset = [p for p in config.all_promptset if p.PromptID != prompt_id]
    save_all_prompts()
    
    # 204 No Content response
    return None