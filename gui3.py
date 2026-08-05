import asyncio
import os
import pickle
import glob
import webbrowser
import time
import html
import json
import sys
from typing import Optional, List, Dict, Any
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import errorLog
import epubArena3
import store
import md2epub
from prompts import Promptset, load_promptsets, save_promptsets
from prompt_api import router as prompt_router
from api_configs import router as api_configs_router

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app = FastAPI(title="epubArena 3 FastAPI")

# Trust proxy headers (such as X-Forwarded-Proto and X-Forwarded-For) from any host.
# This ensures that FastAPI is aware it is being accessed over HTTPS behind a reverse proxy (like Traefik)
# and properly constructs secure redirect/URL schemes (https instead of http).
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# Include prompt API router
app.include_router(prompt_router)
# Include API configs router
app.include_router(api_configs_router)

# Base directory of this module (ensures relative paths work even when uvicorn
# is started from elsewhere).
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Add url_for function to template globals
def url_for(endpoint: str, **kwargs):
    """Simple url_for compatibility for templates"""
    if endpoint == 'static':
        filename = kwargs.get('filename', '')
        return f"/static/{filename}"
    # Map endpoint names to paths
    endpoint_map = {
        'uploadfile': '/uploadfile',
        'edit_prompts': '/editprompts',
        'edit_api_configs': '/editapiconfigs',
        'index': '/'
    }
    return endpoint_map.get(endpoint, f'/{endpoint}')

templates.env.globals['url_for'] = url_for

# Global state
statustext = 'Waiting for file'

# Application state
class AppState:
    def __init__(self):
        self.statustext = 'Waiting for file'
        self.config = config.cfg

app_state = AppState()

# Models for request/response
class MessageResponse(BaseModel):
    statustext: str
    log_last_10_lines: str

class FileItem(BaseModel):
    name: str
    size: int
    modified: float

# CRUD Endpoints are now in prompt_api.py router

# Dependency to get app state
def get_app_state():
    return app_state

@app.post("/upload_file")
async def upload_file(
    file: UploadFile = File(...),
    state: AppState = Depends(get_app_state)
):
    if not file.filename:
        return JSONResponse({"error": "No file selected"}, status_code=400)

    content = await file.read()
    filename = file.filename
    file_path = config.PATH_INP / filename

    if filename.lower().endswith('.epub'):
        # Save uploaded epub file
        with open(file_path, "wb") as f:
            f.write(content)

        state.statustext = f"File {file_path} successfully uploaded"
        config.cfg.gePubFilename = filename
        estoreinfo = store.loadstore(filename)
        errorLog.log.printlog(f'Info: {estoreinfo.info()}')

    elif filename.lower().endswith('.md'):
        # Save markdown file, then auto-convert to EPUB
        with open(file_path, "wb") as f:
            f.write(content)

        # Build output epub filename: <name>(MD).epub
        base = os.path.splitext(filename)[0]
        epub_filename = f"{base}(MD).epub"
        epub_path = config.PATH_INP / epub_filename

        try:
            md2epub.md2epub(
                input_path=str(file_path),
                output_path=str(epub_path),
                title=base,
                author="Unknown",
            )
            config.cfg.gePubFilename = epub_filename
            state.statustext = (
                f"Markdown converted: {filename} → {epub_filename}"
            )
            errorLog.log.printlog(
                f"Converted {filename} to {epub_filename}"
            )
        except Exception as e:
            state.statustext = (
                f"Error converting {filename}: {str(e)}"
            )
            errorLog.log.printlog(
                f"Error converting {filename} to EPUB: {str(e)}"
            )

    else:
        state.statustext = "not saved, only .epub and .md files are supported."

    return RedirectResponse(url="/", status_code=303)

@app.get("/uploadfile")
async def uploadfile(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def index_get(request: Request):
    # Pass all config attributes to template
    return templates.TemplateResponse("gui3.html", {
        "request": request,
        **config.cfg.__dict__
    })

@app.post("/")
async def index_post(
    request: Request,
    state: AppState = Depends(get_app_state),
    start: Optional[str] = Form(None),
    stop: Optional[str] = Form(None),
    delete: Optional[str] = Form(None),
    current_openai_api_base: Optional[str] = Form(None),
    current_openai_api_key: Optional[str] = Form(None),
    current_open_api_modelname: Optional[str] = Form(None),
    modelname: Optional[str] = Form(None),
    modelname_translation: Optional[str] = Form(None),
    source4prompt2: Optional[str] = Form(None),
    ce_start: Optional[str] = Form(None),
    ce_stop: Optional[str] = Form(None),
    translate_heading: Optional[str] = Form(None),
    batch_jobs: Optional[str] = Form(None),
    force_redo: Optional[str] = Form(None),
    publish_only: Optional[str] = Form(None),
    publish_markdown: Optional[str] = Form(None),
    use_markdown: Optional[str] = Form(None),
    processor_autosave: Optional[str] = Form(None),
    chunker_maxp: Optional[str] = Form(None),
    chunker_maxwords: Optional[str] = Form(None),
    promptno_1: Optional[str] = Form(None),
    promptno_2: Optional[str] = Form(None),
    api_timeout: Optional[str] = Form(None),
    max_concurrent_calls: Optional[str] = Form(None),
    modeltodelete: Optional[str] = Form(None),
):
    Errors = ''
    
    if start is not None:
        if config.app_running:
            errorLog.log.printlog('Web: Start noch nicht möglich (laufender Prozess wird beendet)')
            config.continue_process = False
        else:
            # Update config from form data
            if current_openai_api_base:
                config.cfg.__dict__['current_openai_api_base'] = current_openai_api_base
            if current_openai_api_key:
                config.cfg.__dict__['current_openai_api_key'] = current_openai_api_key
            if current_open_api_modelname:
                config.cfg.__dict__['current_open_api_modelname'] = current_open_api_modelname
            if modelname:
                config.cfg.__dict__['modelname'] = modelname
            if modelname_translation:
                config.cfg.__dict__['modelname_translation'] = modelname_translation
            if source4prompt2:
                config.cfg.__dict__['source4prompt2'] = source4prompt2
            
            config.cfg.__dict__['translate_heading'] = translate_heading == "on"
            config.cfg.ce_start = int(ce_start) if ce_start and ce_start != "" else 0
            config.cfg.ce_stop = int(ce_stop) if ce_stop and ce_stop != "" else 0
            config.cfg.__dict__['batch_jobs'] = batch_jobs == "on"
            config.cfg.__dict__['force_redo'] = force_redo == "on"
            config.cfg.__dict__['publish_only'] = publish_only == "on"
            config.cfg.__dict__['publish_markdown'] = publish_markdown == "on"
            config.cfg.__dict__['use_markdown'] = use_markdown == "on"
            config.cfg.__dict__['processor_autosave'] = processor_autosave == "on"
            
            if chunker_maxp:
                config.cfg.chunker_maxp = int(chunker_maxp) if chunker_maxp != "" else 0
            if chunker_maxwords:
                config.cfg.chunker_maxwords = int(chunker_maxwords) if chunker_maxwords != "" else 0
            
            if promptno_1:
                config.cfg.prompt1_no = int(promptno_1) if promptno_1 != "" else 0
            if promptno_2:
                config.cfg.prompt2_no = int(promptno_2) if promptno_2 != "" else 0
            
            if api_timeout:
                config.cfg.api_timeout = float(api_timeout) if api_timeout != "" else 600.0
            if max_concurrent_calls:
                config.cfg.max_concurrent_calls = int(max_concurrent_calls) if max_concurrent_calls != "" else 4

            if not config.cfg.batch_jobs and not config.cfg.gePubFilename:
                Errors = '\nNo ePub selected (and no batchJobs checked)\n'
            if config.cfg.gePubFilename and not config.cfg.gePubFilename.endswith('.epub'):
                Errors = '\nNo ePub selected (only .epub files can be processed)\n'
            
            if Errors == '':
                config.cfg.update_main()
                errorLog.log.printlog('Web: Start')
                config.continue_process = True
                print(config.cfg.__dict__)
                save_lastConfig()
                asyncio.create_task(asyncio.to_thread(epubArena3.run))
            else:
                errorLog.log.printlog(f'NO START because: {Errors}')
    
    elif stop is not None:
        config.continue_process = False
        errorLog.log.printlog('Web: Stop (current chunk will still be finished)')
    
    elif delete is not None:
        modelname2delete = modeltodelete or ""
        errorLog.log.printlog(f'Web: Trying to delete translation with name "{modelname2delete}"')
        try:
            estoreinfo = store.loadstore(config.cfg.gePubFilename)
            estoreinfo.removeTranslationsByName(modelname2delete)
            errorLog.log.printlog(f'Info: {estoreinfo.info()}')
            estoreinfo.save()
        except Exception as e:
            errorLog.log.printlog(f'Web: Translation with name "{modelname2delete}" could not be deleted. {str(e)}')
    
    # Return to main page
    return templates.TemplateResponse("gui3.html", {
        "request": request,
        **config.cfg.__dict__
    })

@app.get("/get_messages")
async def get_messages(state: AppState = Depends(get_app_state)):
    if not errorLog.log.Logfiletext:
        log_last_10_lines = '...'
    else:
        infoFromLogfile = html.escape(errorLog.log.Sessiontext)
        lines = infoFromLogfile.splitlines()
        last_10_lines = lines[-300:]
        log_last_10_lines = "<br/>".join(last_10_lines)
    
    return JSONResponse({
        "statustext": state.statustext,
        "log_last_10_lines": log_last_10_lines
    })

@app.get("/get_prompts")
async def get_prompts():
    prompt_objects = config.all_promptset
    all_prompts = [p.__dict__ for p in prompt_objects]
    return JSONResponse({
        'prompts': all_prompts,
        'activePrompt1': config.cfg.prompt1_no,
        'activePrompt2': config.cfg.prompt2_no,
        'count': len(all_prompts)
    })

@app.get("/get_api_configs")
async def get_api_configs():
    if os.path.exists(config.API_CONFIG_FILE):
        with open(config.API_CONFIG_FILE, 'r', encoding="utf-8") as f:
            configs = json.load(f)
    else:
        configs = []
    return JSONResponse({
        "configs": configs,
        "default_config": 0
    })

@app.get("/editprompts")
async def edit_prompts(request: Request):
    # Pass empty prompts - frontend will fetch via API
    return templates.TemplateResponse("editprompts.html", {
        "request": request,
        "prompts": []
    })

@app.get("/editapiconfigs")
async def edit_api_configs(request: Request):
    # Pass empty configs - frontend will fetch via API
    return templates.TemplateResponse("editapiconfigs.html", {
        "request": request,
        "configs": []
    })

@app.get("/list_epub_files")
async def list_epub_files():
    downloadable_files = []
    try:
        patterns = [
            os.path.join(config.PATH_OUT, "*.epub"),
            os.path.join(config.PATH_OUT, "*.html"),
            os.path.join(config.PATH_OUT, "*.md")
        ]
        
        file_paths = []
        for pat in patterns:
            file_paths.extend(glob.glob(pat))
        
        for file_path in sorted(file_paths):
            filename = os.path.basename(file_path)
            st = os.stat(file_path)
            downloadable_files.append({
                "name": filename,
                "size": st.st_size,
                "modified": st.st_mtime,
            })
    except Exception as e:
        errorLog.log.printlog(f"Error listing EPUB files: {str(e)}")
    
    return JSONResponse({"files": downloadable_files})

@app.get("/list_input_files")
async def list_input_files():
    """List all epub files in the input directory"""
    input_files = []
    try:
        patterns = [
            os.path.join(config.PATH_INP, "*.epub"),
            os.path.join(config.PATH_INP, "*.md")
        ]
        
        file_paths = []
        for pat in patterns:
            file_paths.extend(glob.glob(pat))
        
        for file_path in sorted(file_paths):
            filename = os.path.basename(file_path)
            st = os.stat(file_path)
            input_files.append({
                "name": filename,
                "size": st.st_size,
                "modified": st.st_mtime,
            })
    except Exception as e:
        errorLog.log.printlog(f"Error listing input files: {str(e)}")
    
    return JSONResponse({"files": input_files, "current_file": config.cfg.gePubFilename})

@app.post("/select_file")
async def select_file(
    filename: str = Form(...),
    state: AppState = Depends(get_app_state)
):
    """Select a previously uploaded file as the current input file"""
    try:
        file_path = config.PATH_INP / filename
        
        if not file_path.exists():
            return JSONResponse({"error": "File not found"}, status_code=404)
        
        # Update config with selected file
        config.cfg.gePubFilename = filename
        state.statustext = f"File {filename} selected"
        
        # Load store info
        estoreinfo = store.loadstore(filename)
        errorLog.log.printlog(f'Info: {estoreinfo.info()}')
        
        # Save the config
        save_lastConfig()
        
        return RedirectResponse(url="/", status_code=303)
    except Exception as e:
        errorLog.log.printlog(f"Error selecting file: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/download/{filename}")
async def download_file(filename: str):
    allowed_extensions = ('.epub', '.html', '.md')
    if not filename.lower().endswith(allowed_extensions):
        return JSONResponse({"error": "Only EPUB and HTML files can be downloaded"}, status_code=400)
    
    file_path = os.path.join(config.PATH_OUT, filename)
    if not os.path.exists(file_path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    return FileResponse(file_path, filename=filename)

def load_lastConfig() -> None:
    pklFilename = config.PATH_PKL / 'laststate.pkl'
    try:
        with open(pklFilename, 'rb') as f:
            config.cfg = pickle.load(f)
        errorLog.log.printlog(f'Data loaded from PKL file {pklFilename}.')
        estoreinfo = store.loadstore(config.cfg.gePubFilename)
        estoreinfo.info()
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} could not be loaded. {str(exc)}')

def save_lastConfig() -> None:
    pklFilename = config.PATH_PKL / 'laststate.pkl'
    try:
        with open(pklFilename, 'wb') as f:
            pickle.dump(config.cfg, f)
        errorLog.log.printlog(f'Status saved in PKL file {pklFilename}.')
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} could not be saved. {str(exc)}')

if __name__ == '__main__':
    load_lastConfig()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
