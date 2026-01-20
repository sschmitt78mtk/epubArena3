import os
import pickle

import webbrowser 
#import threading # für webbrowser in eigenen Thread
import time # für webbrowser
import html

import json
from flask import Flask, render_template, request, jsonify, redirect, url_for

import config
import ErrorLog
import epubArena3
import store
from prompts import promptset, load_promptsets, save_promptsets

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
    file_path = os.path.join(config.pathinp + file.filename)
    if str(file_path).endswith('epub'):
        file.save(file_path)
        statustext = f"Datei {file_path} erfolgreich hochgeladen"
         
        config.cfg.gePubFilename = file.filename
        estoreinfo = store.loadstore(file.filename)
        ErrorLog.log.printlog(f'Info: {estoreinfo.info()}')
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
            if config.appRunning:
                ErrorLog.log.printlog('Web: Start noch nicht möglich (laufender Prozess wird beendet)')
                config.continueProcess = False
            else:
                Errors = '' # Prüfen, ob Werte sinnvoll
                config.cfg.current_OPENAI_API_BASE = request.form.get("current_OPENAI_API_BASE")
                config.cfg.current_OPEN_API_MODELNAME = request.form.get("current_OPEN_API_MODELNAME")
                config.cfg.current_OPENAI_API_KEY = request.form.get("current_OPENAI_API_KEY")
                config.cfg.modelname = request.form.get("modelname")
                config.cfg.modelnameTranslation = request.form.get("modelnameTranslation")
                config.cfg.source4prompt2 = request.form.get("source4prompt2")
                config.cfg.translateHeading = "translateHeading" in request.form
                config.cfg.cestart = int(request.form.get("cestart"))
                config.cfg.cestop = int(request.form.get("cestop"))
                config.cfg.batchJobs = "batchJobs" in request.form
                config.cfg.forceRedo = "forceRedo" in request.form
                config.cfg.previewOnAutosave = "previewOnAutosave" in request.form
                config.cfg.publishOnly = "publishOnly" in request.form
                config.cfg.useMarkdown = "useMarkdown" in request.form
                config.cfg.LLMfromFile = "LLMfromFile" in request.form
                config.cfg.uselangchain = "uselangchain" in request.form
                config.cfg.chunker_maxp = int(request.form.get("chunker_maxp"))
                config.cfg.chunker_maxwords = int(request.form.get("chunker_maxwords"))
                config.cfg.Prompt1No = int(request.form.get("promptno_1"))
                config.cfg.Prompt2No = int(request.form.get("promptno_2"))
                
                if not config.cfg.batchJobs and not config.cfg.gePubFilename:
                    Errors = '\nkein ePub ausgewählt (und kein batchJobs angehakt)\n'
                if not config.cfg.gePubFilename.endswith('.epub'):
                    Errors = '\nkein ePub ausgewählt (nur .epub  können verarbeitet werden)\n'
            if Errors == '':
                config.cfg.updateMain()    
                ErrorLog.log.printlog('Web: Start')
                config.continueProcess = True 
                print(config.cfg.__dict__)
                save_lastConfig()
                epubArena3.run()
            else:
                ErrorLog.log.printlog(f'KEIN Start weil: {Errors} ')
            
        elif "stop" in request.form:  # Falls der "STOP"-Button gedrückt wurde
            config.continueProcess = False
            ErrorLog.log.printlog('Web: Stop (aktueller chunk wird noch beendet)')
        elif "delete" in request.form:
            modelname2delete = request.form.get("modeltodelete")
            ErrorLog.log.printlog(f'Web: Versuche Löschen der Translation mit Name "{modelname2delete}"')
            try:
                estoreinfo = store.loadstore(config.cfg.gePubFilename)
                estoreinfo.removeTranslationsByName(modelname2delete)
                ErrorLog.log.printlog(f'Info: {estoreinfo.info()}')
                estoreinfo.save()
            except Exception as e:
                ErrorLog.log.printlog(f'Web: Translation mit Name "{modelname2delete}" konnte nicht gelöscht werden. {str(e)}')
            
    return render_template("gui3.html", **config.cfg.__dict__)

@app.route("/get_messages", methods=["GET"])
def get_messages(): # pylint: disable=unused-variable
    if not ErrorLog.log.Logfiletext: # None abfangen
        log_last_10_lines = '...'
    else:
        infoFromLogfile = html.escape(ErrorLog.log.Sessiontext) # verhindert, daß HTML-Code in info-DIV aktiv werden kann
        lines = infoFromLogfile.splitlines()
        last_10_lines = lines[-300:]
        log_last_10_lines = "<br/>".join(last_10_lines)
        #log_last_10_lines = "\r\n".join(last_10_lines)
    return jsonify(statustext = statustext, log_last_10_lines = log_last_10_lines)

@app.route("/get_prompts", methods=["GET"])
def get_prompts(): # pylint: disable=unused-variable
    prompt_objects = config.AllPromptset # [epubArena3.prompt1, epubArena3.prompt2] 
    all_prompts = [p.__dict__ for p in prompt_objects]  # Konvertiere alle zu Dictionaries
    return jsonify({
        'prompts': all_prompts,  # Haupt-Array mit allen Prompts
        'activePrompt1' : config.cfg.Prompt1No,
        'activePrompt2' : config.cfg.Prompt2No,
        'count': len(all_prompts)  # Optional: Anzahl der Prompts
    })

@app.route('/get_api_configs')
def get_api_configs(): # pylint: disable=unused-variable
    if os.path.exists(config.apiconfigfile):
        with open(config.apiconfigfile, 'r', encoding="utf-8") as f:
            configs = json.load(f)
    else:
        configs = []
    return jsonify({
        "configs": configs,
        "default_config": 0
    })

@app.route("/get_prompts2", methods=["GET"])
def get_prompts2(): # pylint: disable=unused-variable
    prompt_objects = config.AllPromptset
    return jsonify({
        "prompts": [p.__dict__ for p in prompt_objects]
    })

@app.route("/save_prompts2", methods=["POST"])
def save_prompts2(): # pylint: disable=unused-variable
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify(success=False, message="Ungültige Daten"), 400

    prompts: list[promptset] = []
    for entry in data:
        try:
            prompts.append(promptset.from_dict(entry))
        except (KeyError, TypeError) as exc:
            return jsonify(success=False, message=f"Prompt nicht vollständig: {str(exc)}"), 400

    try:
        save_promptsets(prompts, config.promtsjsonfile)
        config.AllPromptset = load_promptsets(config.promtsjsonfile) # Prompts nach dem bearbeiten neu laden
    except Exception as exc:
        return jsonify(success=False, message=f"Speichern fehlgeschlagen: {str(exc)}"), 500

    return jsonify(success=True, prompts=[p.__dict__ for p in prompts])

@app.route("/editprompts")
def edit_prompts(): # pylint: disable=unused-variable
    current_prompts = config.AllPromptset
    return render_template("editprompts.html", prompts=[p.__dict__ for p in current_prompts])

def load_lastConfig() -> None:
    pklFilename = config.pathpkl + 'laststate.pkl'
    try:
        with open(pklFilename, 'rb') as f:
            config.cfg = pickle.load(f)
        ErrorLog.log.printlog(f'Daten aus PKL-Datei {pklFilename} geladen.')
        estoreinfo = store.loadstore(config.cfg.gePubFilename)
        estoreinfo.info()
    except Exception as e:
        ErrorLog.log.printlog(f'{pklFilename} konnte nicht geladen werden. {str(e)}')

def save_lastConfig() -> None:
    pklFilename = config.pathpkl + 'laststate.pkl'
    try:
        with open(pklFilename, 'wb') as f:
            pickle.dump(config.cfg, f)
        ErrorLog.log.printlog(f'Status in PKL-Datei {pklFilename} gespeichert.')
    except Exception as e:
        ErrorLog.log.printlog(f'{pklFilename} konnte nicht gespeichert werden. {str(e)}')            
    
def open_browser() -> None: # pylint: disable=unused-variable
    time.sleep(1) # Warte kurz, bis der Flask-Server gestartet ist
    webbrowser.open('http://127.0.0.1/')

if __name__ == '__main__':
    load_lastConfig()
    #threading.Thread(target=open_browser).start() # Starte den Browser in einem separaten Thread
    app.run(host='0.0.0.0', port=8080, debug=True) # Starte den Flask-Server
        
