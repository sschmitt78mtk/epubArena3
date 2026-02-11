import os
import shutil

from prompts import Promptset, get_promptsetByID, load_promptsets, save_promptsets

# pylint: disable=unused-variable

LOCAL_OPEN_API_MODELNAME="occiglot-7b-de-en-instruct@q8_0"
LOCAL_OPENAI_API_KEY="lm-studio"
LOCAL_OPENAI_API_BASE="http://127.0.0.1:5005/v1"

# APPSTATE
app_running = False
continue_process = True

SUPPORT_KEYBOARD_BREAK = False
PROMPTS_JSON_FILE_NEW = "prompts_sample.json"
API_CONFIG_FILE_NEW = "api_configs_sample.json"
PROMPTS_JSON_FILE = "prompts.json"
API_CONFIG_FILE = "api_configs.json"


PATH_BASE = "data/"
PATH_PKL = "data/pkl/"
PATH_LOG = "data/pkl/"
PATH_OUT = "data/output/"
PATH_INP = "data/input/"

PATH_CFG = "data/cfg/"

# PATH_PKL = "/app/data/pkl/"
# PATH_LOG = "/app/data/pkl/"
# PATH_OUT = "/app/data/output/"
# PATH_INP = "/app/data/input/"
# PATH_CFG = "/app/data/cfg/"

# pylint: enable=unused-variable

paths = [PATH_BASE, PATH_PKL, PATH_OUT, PATH_INP, PATH_LOG, PATH_CFG]
def check_paths() -> None: 
    for directory in paths:
        if not os.path.exists(directory):
            os.makedirs(directory)
check_paths()

all_promptset = []

# check api-config-files exists
if not os.path.exists(PATH_CFG + API_CONFIG_FILE):
    print("API_CONFIG_FILE does not exist, using sample.")
    if os.path.exists(API_CONFIG_FILE_NEW):
        shutil.move(API_CONFIG_FILE_NEW, PATH_CFG + API_CONFIG_FILE)
    else:
        print("API_CONFIG_FILE sample NOT FOUND either.")

# check prmpt-config-files exists
if os.path.exists(PATH_CFG + PROMPTS_JSON_FILE):
    print("PROMPTS_JSON_FILE exists.")
    all_promptset = load_promptsets(PATH_CFG + PROMPTS_JSON_FILE)
else:
    print("PROMPTS_JSON_FILE does not exist, create new one.")
    if os.path.exists(PROMPTS_JSON_FILE_NEW):
        shutil.move(PROMPTS_JSON_FILE_NEW, PATH_CFG + PROMPTS_JSON_FILE)
        all_promptset = load_promptsets(PROMPTS_JSON_FILE_NEW)
    else:
        all_promptset = [
            Promptset(0,'1:1 (Original)', '','','keine Verarbeitung',True),
            Promptset(1,'Reduziere den Text auf die zentralen Fakten und Zahlen. Keine Ausschmückungen.','','','TBD',False)
        ]
    save_promptsets(all_promptset, PATH_CFG + PROMPTS_JSON_FILE)
    
class Configuration:
    def __init__(self):
        self.gePubFilename = "deep1.epub"
        self.current_openai_api_base = LOCAL_OPEN_API_MODELNAME
        self.current_openai_api_key = LOCAL_OPENAI_API_KEY
        self.current_open_api_modelname = LOCAL_OPEN_API_MODELNAME
        self.modelname = "occiglot-Q8"
        self.modelname_translation = ""  # Wenn abweichendes Modell für Übersetzung, wird die abwechelnde Generierung angehalten
        self.batch_jobs = False
        self.force_redo = False
        #self.preview_on_autosave = preview_on_autosave
        self.publish_only = False
        self.use_markdown = True
        self.llm_from_file = False
        self.use_langchain = False
        self.translate_heading = True
        self.ce_start = 0
        self.ce_stop = 0
        self.reload_epub = False
        self.chunker_maxp = 20
        self.chunker_maxwords = 350
        self.prompt1_no = 0
        self.prompt2_no = 3
        self.source4prompt1 = "" # aktuell nicht benutzt
        self.prompt1 = get_promptsetByID(all_promptset, 0)
        self.source4prompt2 = ""
        self.prompt2 = get_promptsetByID(all_promptset, 1)
        self.processor_autosave = True
        self.processor_autosave_interval = 10
    
    def update_main(self) -> None:
        self.prompt1 = get_promptsetByID(all_promptset, self.prompt1_no)
        self.prompt2 = get_promptsetByID(all_promptset, self.prompt2_no)

cfg = Configuration() # pylint: disable=unused-variable
