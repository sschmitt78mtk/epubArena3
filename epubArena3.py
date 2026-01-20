# pip install ebooklib
# pip install beautifulsoup4
# pip install requests
# pip install keyboard
# pip install markdown
# pip install markdownify
# pip install openai
# pip install llama-cpp-python (optional für directLLM) -> akutell kein pythoch für 3.13 (3.12 verwenden?)
# pip install flask
# pip install spacy (optional? -> jaccard)

# pip install types-keyboard
# pip install types-beautifulsoup4

# pip install ebooklib beautifulsoup4 requests keyboard markdown markdownify openai flask spacy
# optional für direct : pip install llama-cpp-python


# cxfreeze --script epubArena.py

# 1. Environment erstellen
#python3 -m venv venv_ubuntu

# 2. Aktivieren
#source venv_ubuntu/bin/activate

#import argparse
#import re

#from datetime import datetime

#import sys # exit
import os
import glob
import config

# pylint: disable=wrong-import-position
if config.supportKeyboardbreak: import keyboard

#import store
from collect import extractor, cleaner, chunker
from store import loadstore, publication #, get_promptsetByID, load_promptsets, save_promptsets
from process import processor, processorMultiSource
from ErrorLog import log
#from prompts import promptset, get_promptsetByID, load_promptsets, save_promptsets

# pylint: enable=wrong-import-position





def main(ePubFilename: str) -> None:
    config.appRunning = True
    ePubFilename = os.path.basename(ePubFilename) # Pfad ignorieren
    log.setFilename(config.pathlog + ePubFilename + '.log',"errors.log")
    log.printlog(f'Programm gestartet - {ePubFilename}')
    estore = loadstore(ePubFilename)
    estore.info()
    
    if not estore.source.finished or config.cfg.reloadepub: # epub einlesen, wenn noch nicht beendet
        if config.cfg.reloadepub: estore.source.chunks.clear()
        eextractor = extractor(ePubFilename)
        echunker = chunker(config.cfg.chunker_maxp,config.cfg.chunker_maxwords) # 20paragraphs, 350 Wörter
        log.printlog(f'echunker: maxp {config.cfg.chunker_maxp} | maxwords {config.cfg.chunker_maxwords}')
        ecleaner = cleaner(True) # Leerzeilen entfernen
        eextractor.extract_chapters()
        for extractedchapter in eextractor.chapterhtmlpkg:
            log.printlog(f'ID: {extractedchapter.chapterID} Chapter: {extractedchapter.source_chaptername}')
            cleanedChapter = ecleaner.cleanchunks([extractedchapter])
            estore.source.chunks += echunker.chunkit(cleanedChapter)
        estore.source.set_metadata(eextractor.title,eextractor.author,eextractor.language)
        estore.source.set_finished()
        if log.errorcount > 0:
            log.error(f'{estore.pklFilename} wurde nicht gespeichert, da es Fehler beim Einlesen des epub gab.')
        else: estore.save()

      
    chunksTotal = estore.source.numberOfChunks
    log.printlog(f'Chunks total: {str(chunksTotal)}')  
    log.saveFile()
 
    Step1TName = config.cfg.modelname + '-' + str(config.cfg.prompt1.PromptID)
    
    if config.cfg.modelnameTranslation != "": 
        Step2TName = config.cfg.modelnameTranslation + '-' + str(config.cfg.prompt2.PromptID)
    else:  
        Step2TName = config.cfg.modelname + '-' + str(config.cfg.prompt2.PromptID)
    
    if not config.cfg.publishOnly:
        if config.cfg.prompt1 and config.cfg.prompt1.PromptID != 0: # Summary durchführen
            Step1T = estore.getTranslationByModelName(Step1TName) # erstellen
            Step1T.set_metadata(estore.source.title,estore.source.author,estore.source.language)
            Step1T_processor = processor(estore.source,Step1T,estore,Step1TName,config.cfg.prompt1)
            Step1T_processor.overwrite = config.cfg.forceRedo
            Step1T_processor.do(config.cfg.cestart,config.cfg.cestop)
        if config.cfg.prompt2 and config.cfg.prompt2.PromptID != 0: # Übersetzung
            Step2T = estore.getTranslationByModelName(Step2TName) # erstellen
            Step2T.set_metadata(estore.source.title,estore.source.author,'de-de')
            
            if config.cfg.source4prompt2 == '': # 1. normale Übersetzung aus Step1, wenn es kein source4prompt2 gibt
                if config.cfg.prompt1.PromptID != 0: # 1. normale Übersetzung aus Quelle, wenn es kein source4prompt2 gibt
                    source4step2 = estore.getTranslationByModelName(Step1TName) # Step1 als Quelle nehmen
                else:
                    source4step2 = estore.source # Source als Quelle nehmen
                Step2T_processor = processor(source4step2,Step2T,estore,Step2TName,config.cfg.prompt2)
            elif ';' not in config.cfg.source4prompt2: # angegebene Übersetzung als Quelle nehmen
                source4step2 = estore.getTranslationByModelName(config.cfg.source4prompt2)
                Step2T_processor = processor(source4step2,Step2T,estore,Step2TName,config.cfg.prompt2)
            else: # nicht leer + Semikolon im Namen -> mehrer Source-Models
                multiplesource4step2 = estore.getmultipleTranslationsByModelNames(config.cfg.source4prompt2)
                Step2T_processor = processorMultiSource(estore.source, multiplesource4step2,Step2T,estore,Step2TName,config.cfg.prompt2)
                
            Step2T_processor.overwrite = config.cfg.forceRedo
            Step2T_processor.do(config.cfg.cestart,config.cfg.cestop)
              

    estore.removeEmptyTranslations()
    
    # Work und Publish
    publishHTML = publication(estore)
    publishHTML.html_filename = ePubFilename + '_SBS.html'
    publishHTML.genHTML_SideBySide([estore.source] + estore.translations,'templates/defaultsbs.css',False,config.cfg.cestart,config.cfg.cestop)
    try:
        publishHTML.genEPUB(estore.getTranslationByModelName(Step2TName)) # die letzte Übersetzung/Summary publizieren
    except Exception as e:
        log.error(f'genEPUB konnte nicht gespeichert werden: {ePubFilename}, {str(e)}')
    
    estore.save()
    estore.info()
    log.printlog(f'{ePubFilename} - beendet.')
    log.saveFile()
    log.errorcount = 0
    config.appRunning = False
    config.continueProcess = True # für nächste Verarbeitung freigeben
    

if config.supportKeyboardbreak:
    def on_key_event(event):
        if event.name == "q":  # Falls "q" gedrückt wurde, Programm abbrechen
            sure = str(input('Wirklich beenden, tippe: ja \n')) # pylint: disable=bad-builtin
            if 'ja' in sure.lower() or 'j' in sure.lower():
                log.printlog('Abbruch durch Nutzer.')
                config.continueProcess = False
        
    keyboard.on_press(on_key_event) # Event-Listener starten 
  
def run() -> None:
    if config.cfg.batchJobs:
        for file in glob.glob(config.pathinp + "*.epub"):
            if config.continueProcess: 
                main(file)
            else:
                log.printlog(f'Skipped {file} (Nutzerabbruch)')
    elif os.path.exists(config.pathinp + config.cfg.gePubFilename):
        main(config.cfg.gePubFilename)
    else:
        log.printlog(f'Abbruch, die Datei "{config.cfg.gePubFilename}" existiert nicht.')

if __name__ == "__main__":
    run()
    
