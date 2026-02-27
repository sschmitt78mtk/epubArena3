import os
import pickle
import glob

import webbrowser 
#import threading # für webbrowser in eigenen Thread
import time # für webbrowser
import html

import json
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory

import config
import errorLog
import epubArena3
import store
from prompts import Promptset, load_promptsets, save_promptsets

app = Flask(__name__, static_url_path='/static')    

statustext = 'Warten auf Datei'

@app.route("/upload_file", methods=["POST"]) 
def upload_file(): # pylint: disable=unused-variable
    global statustext
    if "file" not in request.files:
        return jsonify({"error": "Keine Datei hochgeladen"}), 400
    
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Keine Datei ausgewählt"}), 400       
    file_path = os.path.join(config.PATH_INP + str(file.filename))
    if str(file_path).endswith('epub'):
        file.save(file_path)
        statustext = f"Datei {file_path} erfolgreich hochgeladen"
         
        config.cfg.gePubFilename = str(file.filename)
        estoreinfo = store.loadstore(str(file.filename))
        errorLog.log.printlog(f'Info: {estoreinfo.info()}')
    else: 
        statustext = "nicht gespeichert, nur .epub-Dateien können verarbeitet werden."
    return redirect(url_for('index'))


@app.route('/uploadfile')
def uploadfile(): # pylint: disable=unused-variable
    return render_template('upload.html')
       
@app.route("/", methods=["GET", "POST"])
def index(): # pylint: disable=unused-variable
    Errors = ''
    if request.method == "POST":
        if "start" in request.form:  # Falls der "START"-Button gedrückt wurde
            if config.app_running:
                errorLog.log.printlog('Web: Start noch nicht möglich (laufender Prozess wird beendet)')
                config.continue_process = False
            else:
                Errors = '' # Prüfen, ob Werte sinnvoll
                # Update config using __dict__ to avoid static typing issues in IDEs
                config.cfg.__dict__['current_openai_api_base'] = request.form.get("current_openai_api_base") or ""
                config.cfg.__dict__['current_open_api_modelname'] = request.form.get("current_open_api_modelname") or ""
                config.cfg.__dict__['current_openai_api_key'] = request.form.get("current_openai_api_key") or ""
                config.cfg.__dict__['modelname'] = request.form.get("modelname") or ""
                config.cfg.__dict__['modelname_translation'] = request.form.get("modelname_translation") or ""
                config.cfg.__dict__['source4prompt2'] = request.form.get("source4prompt2") or ""
                config.cfg.__dict__['translate_heading'] = "translate_heading" in request.form
                ce_start_val = request.form.get("ce_start")
                ce_stop_val = request.form.get("ce_stop")
                config.cfg.ce_start = int(ce_start_val) if ce_start_val is not None and ce_start_val != "" else 0
                config.cfg.ce_stop = int(ce_stop_val) if ce_stop_val is not None and ce_stop_val != "" else 0
                config.cfg.batch_jobs = "batch_jobs" in request.form
                config.cfg.force_redo = "force_redo" in request.form
                config.cfg.processor_autosave = "processor_autosave" in request.form
                config.cfg.publish_only = "publish_only" in request.form
                config.cfg.use_markdown = "use_markdown" in request.form
                config.cfg.llm_from_file = "llm_from_file" in request.form
                config.cfg.use_langchain = "use_langchain" in request.form
                cp = request.form.get("chunker_maxp")
                cww = request.form.get("chunker_maxwords")
                config.cfg.chunker_maxp = int(cp) if cp is not None and cp != "" else 0
                config.cfg.chunker_maxwords = int(cww) if cww is not None and cww != "" else 0
                p1 = request.form.get("promptno_1")
                p2 = request.form.get("promptno_2")
                config.cfg.prompt1_no = int(p1) if p1 is not None and p1 != "" else 0
                config.cfg.prompt2_no = int(p2) if p2 is not None and p2 != "" else 0
                
                if not config.cfg.batch_jobs and not config.cfg.gePubFilename:
                    Errors = '\nkein ePub ausgewählt (und kein batchJobs angehakt)\n'
                if not config.cfg.gePubFilename.endswith('.epub'):
                    Errors = '\nkein ePub ausgewählt (nur .epub  können verarbeitet werden)\n'
            if Errors == '':
                config.cfg.update_main()    
                errorLog.log.printlog('Web: Start')
                config.continue_process = True 
                print(config.cfg.__dict__)
                save_lastConfig()
                epubArena3.run()
            else:
                errorLog.log.printlog(f'KEIN Start weil: {Errors} ')
            
        elif "stop" in request.form:  # Falls der "STOP"-Button gedrückt wurde
            config.continue_process = False
            errorLog.log.printlog('Web: Stop (aktueller chunk wird noch beendet)')
        elif "delete" in request.form:
            modelname2delete = request.form.get("modeltodelete")
            if modelname2delete is None:
                modelname2delete = ""
            errorLog.log.printlog(f'Web: Versuche Löschen der Translation mit Name "{modelname2delete}"')
            try:
                estoreinfo = store.loadstore(config.cfg.gePubFilename)
                estoreinfo.removeTranslationsByName(modelname2delete)
                errorLog.log.printlog(f'Info: {estoreinfo.info()}')
                estoreinfo.save()
            except Exception as e:
                errorLog.log.printlog(f'Web: Translation mit Name "{modelname2delete}" konnte nicht gelöscht werden. {str(e)}')
            
    return render_template("gui3.html", **config.cfg.__dict__)

@app.route("/get_messages", methods=["GET"])
def get_messages(): # pylint: disable=unused-variable
    if not errorLog.log.Logfiletext: # None abfangen
        log_last_10_lines = '...'
    else:
        infoFromLogfile = html.escape(errorLog.log.Sessiontext) # verhindert, daß HTML-Code in info-DIV aktiv werden kann
        lines = infoFromLogfile.splitlines()
        last_10_lines = lines[-300:]
        log_last_10_lines = "<br/>".join(last_10_lines)
        #log_last_10_lines = "\r\n".join(last_10_lines)
    return jsonify(statustext = statustext, log_last_10_lines = log_last_10_lines)

@app.route("/get_prompts", methods=["GET"])
def get_prompts():  # pylint: disable=unused-variable
    prompt_objects = config.all_promptset  # [epubArena3.prompt1, epubArena3.prompt2]
    all_prompts = [p.__dict__ for p in prompt_objects]
    return jsonify({
        'prompts': all_prompts,
        'activePrompt1': config.cfg.prompt1_no,
        'activePrompt2': config.cfg.prompt2_no,
        'count': len(all_prompts)
    })

@app.route('/get_api_configs')
def get_api_configs(): # pylint: disable=unused-variable
    if os.path.exists(config.PATH_CFG + config.API_CONFIG_FILE):
        with open(config.PATH_CFG + config.API_CONFIG_FILE, 'r', encoding="utf-8") as f:
            configs = json.load(f)
    else:
        configs = []
    return jsonify({
        "configs": configs,
        "default_config": 0
    })

@app.route("/get_prompts2", methods=["GET"])
def get_prompts2(): # pylint: disable=unused-variable
    prompt_objects = config.all_promptset
    return jsonify({
        "prompts": [p.__dict__ for p in prompt_objects]
    })

@app.route("/save_prompts2", methods=["POST"])
def save_prompts2(): # pylint: disable=unused-variable
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify(success=False, message="Ungültige Daten"), 400

    prompts: list[Promptset] = []
    for entry in data:
        try:
            prompts.append(Promptset.from_dict(entry))
        except (KeyError, TypeError) as exc:
            return jsonify(success=False, message=f"Prompt nicht vollständig: {str(exc)}"), 400

    try:
        save_promptsets(prompts, config.PATH_CFG + config.PROMPTS_JSON_FILE)
        config.all_promptset = load_promptsets(config.PATH_CFG + config.PROMPTS_JSON_FILE) # Prompts nach dem bearbeiten neu laden
    except Exception as exc:
        return jsonify(success=False, message=f"Speichern fehlgeschlagen: {str(exc)}"), 500

    return jsonify(success=True, prompts=[p.__dict__ for p in prompts])

@app.route("/editprompts")
def edit_prompts(): # pylint: disable=unused-variable
    current_prompts = config.all_promptset
    return render_template("editprompts.html", prompts=[p.__dict__ for p in current_prompts])

@app.route("/list_epub_files", methods=["GET"])
def list_epub_files(): # pylint: disable=unused-variable
    """Return a JSON list of all EPUB files in the output directory."""
    downloadable_files = []
    try:
        patterns = [os.path.join(config.PATH_OUT, "*.epub"),
                    os.path.join(config.PATH_OUT, "*.html")]

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
    
    return jsonify({"files": downloadable_files})

@app.route("/download/<filename>")
def download_file(filename): # pylint: disable=unused-variable
    """Serve EPUB files for download from the output directory."""
    # Security: only allow .epub files and prevent directory traversal
    allowed_extensions = ('.epub', '.html')
    if not filename.lower().endswith(allowed_extensions):
        return jsonify({"error": "Only EPUB and HTML files can be downloaded"}), 400
    
    # Ensure the file exists in the output directory
    file_path = os.path.join(config.PATH_OUT, filename)
    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404
    
    # Serve the file for download
    return send_from_directory(config.PATH_OUT, filename, as_attachment=True)

def load_lastConfig() -> None:
    pklFilename = config.PATH_PKL + 'laststate.pkl'
    try:
        with open(pklFilename, 'rb') as f:
            config.cfg = pickle.load(f)
        errorLog.log.printlog(f'Daten aus PKL-Datei {pklFilename} geladen.')
        estoreinfo = store.loadstore(config.cfg.gePubFilename)
        estoreinfo.info()
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} konnte nicht geladen werden. {str(exc)}')

def save_lastConfig() -> None:
    pklFilename = config.PATH_PKL + 'laststate.pkl'
    try:
        with open(pklFilename, 'wb') as f:
            pickle.dump(config.cfg, f)
        errorLog.log.printlog(f'Status in PKL-Datei {pklFilename} gespeichert.')
    except Exception as exc:
        errorLog.log.printlog(f'{pklFilename} konnte nicht gespeichert werden. {str(exc)}')
    
def open_browser() -> None: # pylint: disable=unused-variable
    time.sleep(1) # Warte kurz, bis der Flask-Server gestartet ist
    webbrowser.open('http://127.0.0.1/')

if __name__ == '__main__':
    load_lastConfig()
    #threading.Thread(target=open_browser).start() # Starte den Browser in einem separaten Thread
    app.run(host='0.0.0.0', port=8080, debug=True) # Starte den Flask-Server
        
