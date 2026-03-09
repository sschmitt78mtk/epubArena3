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
from prompts import Promptset, load_promptsets, save_promptsets

app = FastAPI(title="epubArena 3 FastAPI")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Add url_for function to template globals (compatibility with Flask templates)
def url_for(endpoint: str, **kwargs):
    """Simple url_for compatibility for Flask templates"""
    if endpoint == 'static':
        filename = kwargs.get('filename', '')
        return f"/static/{filename}"
    # Map endpoint names to paths
    endpoint_map = {
        'uploadfile': '/uploadfile',
        'edit_prompts': '/editprompts',
        'index': '/'
    }
    return endpoint_map.get(endpoint, f'/{endpoint}')

templates.env.globals['url_for'] = url_for

# Global state (similar to Flask app)
statustext = 'Warten auf Datei'

# Application state
class AppState:
    def __init__(self):
        self.statustext = 'Warten auf Datei'
        self.config = config.cfg

app_state = AppState()

# Models for request/response
class PromptData(BaseModel):
    PromptID: int
    infostr: str
    system_message: str
    prePrompt: str
    postPrompt: str
    maxNewToken: int
    temperature: float
    top_p: float
    allowLongAnswer: bool

class MessageResponse(BaseModel):
    statustext: str
    log_last_10_lines: str

class FileItem(BaseModel):
    name: str
    size: int
    modified: float

# Dependency to get app state
def get_app_state():
    return app_state

@app.post("/upload_file")
async def upload_file(
    file: UploadFile = File(...),
    state: AppState = Depends(get_app_state)
):
    if not file.filename:
        return JSONResponse({"error": "Keine Datei ausgewählt"}, status_code=400)
    
    file_path = config.PATH_INP / file.filename
    if str(file_path).endswith('epub'):
        # Save uploaded file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        state.statustext = f"Datei {file_path} erfolgreich hochgeladen"
        config.cfg.gePubFilename = str(file.filename)
        estoreinfo = store.loadstore(str(file.filename))
        errorLog.log.printlog(f'Info: {estoreinfo.info()}')
    else:
        state.statustext = "nicht gespeichert, nur .epub-Dateien können verarbeitet werden."
    
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
    use_markdown: Optional[str] = Form(None),
    llm_from_file: Optional[str] = Form(None),
    use_langchain: Optional[str] = Form(None),
    processor_autosave: Optional[str] = Form(None),
    chunker_maxp: Optional[str] = Form(None),
    chunker_maxwords: Optional[str] = Form(None),
    promptno_1: Optional[str] = Form(None),
    promptno_2: Optional[str] = Form(None),
    modeltodelete: Optional[str] = Form(None),
):
    Errors = ''
    
    if start:
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
            config.cfg.__dict__['use_markdown'] = use_markdown == "on"
            config.cfg.__dict__['llm_from_file'] = llm_from_file == "on"
            config.cfg.__dict__['use_langchain'] = use_langchain == "on"
            config.cfg.__dict__['processor_autosave'] = processor_autosave == "on"
            
            if chunker_maxp:
                config.cfg.chunker_maxp = int(chunker_maxp) if chunker_maxp != "" else 0
            if chunker_maxwords:
                config.cfg.chunker_maxwords = int(chunker_maxwords) if chunker_maxwords != "" else 0
            
            if promptno_1:
                config.cfg.prompt1_no = int(promptno_1) if promptno_1 != "" else 0
            if promptno_2:
                config.cfg.prompt2_no = int(promptno_2) if promptno_2 != "" else 0
            
            if not config.cfg.batch_jobs and not config.cfg.gePubFilename:
                Errors = '\nkein ePub ausgewählt (und kein batchJobs angehakt)\n'
            if config.cfg.gePubFilename and not config.cfg.gePubFilename.endswith('.epub'):
                Errors = '\nkein ePub ausgewählt (nur .epub können verarbeitet werden)\n'
            
            if Errors == '':
                config.cfg.update_main()
                errorLog.log.printlog('Web: Start')
                config.continue_process = True
                print(config.cfg.__dict__)
                save_lastConfig()
                epubArena3.run()
            else:
                errorLog.log.printlog(f'KEIN Start weil: {Errors}')
    
    elif stop:
        config.continue_process = False
        errorLog.log.printlog('Web: Stop (aktueller chunk wird noch beendet)')
    
    elif delete:
        modelname2delete = modeltodelete or ""
        errorLog.log.printlog(f'Web: Versuche Löschen der Translation mit Name "{modelname2delete}"')
        try:
            estoreinfo = store.loadstore(config.cfg.gePubFilename)
            estoreinfo.removeTranslationsByName(modelname2delete)
            errorLog.log.printlog(f'Info: {estoreinfo.info()}')
            estoreinfo.save()
        except Exception as e:
            errorLog.log.printlog(f'Web: Translation mit Name "{modelname2delete}" konnte nicht gelöscht werden. {str(e)}')
    
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

@app.get("/get_prompts2")
async def get_prompts2():
    prompt_objects = config.all_promptset
    return JSONResponse({
        "prompts": [p.__dict__ for p in prompt_objects]
    })

@app.post("/save_prompts2")
async def save_prompts2(data: List[Dict[str, Any]]):
    if not isinstance(data, list):
        return JSONResponse({"success": False, "message": "Ungültige Daten"}, status_code=400)
    
    prompts: List[Promptset] = []
    for entry in data:
        try:
            prompts.append(Promptset.from_dict(entry))
        except (KeyError, TypeError) as exc:
            return JSONResponse({"success": False, "message": f"Prompt nicht vollständig: {str(exc)}"}, status_code=400)
    
    try:
        save_promptsets(prompts, str(config.PROMPTS_JSON_FILE))
        config.all_promptset = load_promptsets(str(config.PROMPTS_JSON_FILE))
    except Exception as exc:
        return JSONResponse({"success": False, "message": f"Speichern fehlgeschlagen: {str(exc)}"}, status_code=500)
    
    return JSONResponse({"success": True, "prompts": [p.__dict__ for p in prompts]})

@app.get("/editprompts")
async def edit_prompts(request: Request):
    current_prompts = config.all_promptset
    return templates.TemplateResponse("editprompts.html", {
        "request": request,
        "prompts": [p.__dict__ for p in current_prompts]
    })

@app.get("/list_epub_files")
async def list_epub_files():
    downloadable_files = []
    try:
        patterns = [
            os.path.join(config.PATH_OUT, "*.epub"),
            os.path.join(config.PATH_OUT, "*.html")
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

@app.get("/download/{filename}")
async def download_file(filename: str):
    allowed_extensions = ('.epub', '.html')
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
        errorLog.log.printlog(f'Daten aus PKL-Datei {pklFilename} geladen.')
        estoreinfo = store.loadstore(config.cfg.gePubFilename)
        estoreinfo.info()
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} konnte nicht geladen werden. {str(exc)}')

def save_lastConfig() -> None:
    pklFilename = config.PATH_PKL / 'laststate.pkl'
    try:
        with open(pklFilename, 'wb') as f:
            pickle.dump(config.cfg, f)
        errorLog.log.printlog(f'Status in PKL-Datei {pklFilename} gespeichert.')
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} konnte nicht gespeichert werden. {str(exc)}')

def open_browser() -> None:
    time.sleep(1)
    webbrowser.open('http://127.0.0.1:8082/')

if __name__ == '__main__':
    load_lastConfig()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8082)