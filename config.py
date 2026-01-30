import os
from prompts import Promptset, get_promptsetByID, load_promptsets, save_promptsets

# pylint: disable=unused-variable

LOCAL_OPEN_API_MODELNAME="occiglot-7b-de-en-instruct@q8_0"
LOCAL_OPENAI_API_KEY="lm-studio"
LOCAL_OPENAI_API_BASE="http://127.0.0.1:5005/v1"

# APPSTATE
app_running = False
continue_process = True

SUPPORT_KEYBOARD_BREAK = False
#PROMPTS_JSON_FILE = "prompts_sample.json"
#API_CONFIG_FILE = "api_configs_sample.json"
PROMPTS_JSON_FILE = "prompts.json"
API_CONFIG_FILE = "api_configs.json"
# For backward compatibility with existing code
promtsjsonfile = PROMPTS_JSON_FILE
apiconfigfile = API_CONFIG_FILE

PATH_PKL = "pkl/"
PATH_OUT = "output/"
PATH_INP = "input/"
PATH_LOG = "logs/"

# pylint: enable=unused-variable

paths = [PATH_PKL, PATH_OUT, PATH_INP, PATH_LOG]
def check_paths() -> None: 
    for directory in paths:
        if not os.path.exists(directory):
            os.makedirs(directory)
check_paths()

all_promptset = []

if os.path.exists(PROMPTS_JSON_FILE):
    print("promtsjsonfile exists.")
    all_promptset = load_promptsets(PROMPTS_JSON_FILE)
else:
    print("promtsjsonfile does not exist.")
    all_promptset = [
        Promptset(0,'1:1 (Original)', '','','keine Verarbeitung',True),
        Promptset(1,'Reduziere den Text auf die zentralen Fakten und Zahlen. Keine Ausschmückungen.','','','TBD',False)
    ]
    save_promptsets(all_promptset, PROMPTS_JSON_FILE)

# For backward compatibility with existing code
AllPromptset = all_promptset
    
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
