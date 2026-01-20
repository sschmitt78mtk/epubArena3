import os
from prompts import promptset, get_promptsetByID, load_promptsets, save_promptsets

# pylint: disable=unused-variable

localOPEN_API_MODELNAME="occiglot-7b-de-en-instruct@q8_0"
localOPENAI_API_KEY="lm-studio"
localOPENAI_API_BASE="http://127.0.0.1:5005/v1"

# APPSTATE
appRunning = False
continueProcess = True

supportKeyboardbreak = False
#promtsjsonfile = "prompts_sample.json"
#apiconfigfile = "api_configs_sample.json"
promtsjsonfile = "prompts.json"
apiconfigfile = "api_configs.json"

pathpkl = "pkl/"
pathout = "output/"
pathinp = "input/"
pathlog = "logs/"

# pylint: enable=unused-variable

paths = [pathpkl,pathout,pathinp,pathlog]
def check_paths() -> None: 
    for directory in paths:
        if not os.path.exists(directory):
            os.makedirs(directory)
check_paths()

AllPromptset = []

if os.path.exists(promtsjsonfile):
    print("promtsjsonfile exists.")
    AllPromptset = load_promptsets(promtsjsonfile)
else:
    print("promtsjsonfile does not exist.")
    AllPromptset = [
        promptset(0,'1:1 (Original)', '','','keine Verarbeitung',True),
        promptset(1,'Reduziere den Text auf die zentralen Fakten und Zahlen. Keine Ausschmückungen.','','','TBD',False)
    ]
    save_promptsets(AllPromptset,promtsjsonfile)
    
class Configuration:
    def __init__(self):
        self.gePubFilename = "deep1.epub"
        self.current_OPENAI_API_BASE = localOPEN_API_MODELNAME
        self.current_OPENAI_API_KEY = localOPENAI_API_KEY
        self.current_OPEN_API_MODELNAME = localOPEN_API_MODELNAME
        self.modelname = "occiglot-Q8"
        self.modelnameTranslation = ""  # Wenn abweichendes Modell für Übersetzung, wird die abwechelnde Generierung angehalten
        self.batchJobs = False
        self.forceRedo = False
        #self.previewOnAutosave = previewOnAutosave
        self.publishOnly = False
        self.useMarkdown = True
        self.LLMfromFile = False
        self.uselangchain = False
        self.translateHeading = True
        self.cestart = 0
        self.cestop = 0
        self.reloadepub = False
        self.chunker_maxp = 20
        self.chunker_maxwords = 350
        self.Prompt1No = 0
        self.Prompt2No = 3
        self.source4prompt1 = "" # aktuell nicht benutzt
        self.prompt1 = get_promptsetByID(AllPromptset,0)
        self.source4prompt2 = ""
        self.prompt2 = get_promptsetByID(AllPromptset,1)
        self.processorAutosave = True
        self.processorAutosaveInterval = 10
    
    def updateMain(self) -> None:
        self.prompt1 = get_promptsetByID(AllPromptset,self.Prompt1No)
        self.prompt2 = get_promptsetByID(AllPromptset,self.Prompt2No)

cfg = Configuration() # pylint: disable=unused-variable
