#from typing import Union, Any
from __future__ import annotations # pylint: disable=unused-variable
#import re
import copy
from store import chunk, translation, mainstore
from prompts import promptset

from ErrorLog import log
from call import llmcaller
import config

class processor: 
    def __init__(self, sourcetranslation: translation, processedTranslation: translation, mainstore4save: mainstore,
                 translationmodelname: str, prompt: promptset):
        self.sourcetranslation: translation = sourcetranslation
        self.processedTranslation = processedTranslation
        self.processedTranslation.modelname = translationmodelname # + str(prompt.PromptID)
        self.processedTranslation.promptset = prompt
        self.mainstore4save = mainstore4save # ermöglicht dem processor den mainstore zu speichern.
        self.overwrite = False
        self.finished = False
        self.prompt = prompt
        self.aborted = False
        self.autosave = config.cfg.processorAutosave
        self.autosaveInterval = config.cfg.processorAutosaveInterval# alle 10 chunks speichern
    
    def do(self, start_at_chunkID = 0, stop_at_chunkID = None) -> None:
        log.printlog(f'processing {self.processedTranslation.modelname}')
        if not self.prompt: # Ohne Prompt nur kopieren
            log.error('process None-Type Prompt? - skip)')
            return     
        autosaveno = 0
        maxNewtoken = self.prompt.maxNewToken
        if self.prompt.allowLongAnswer: maxNewtoken *= 3 # Wenn nur Übersetzung -> lange Texte erlauben
        llm = llmcaller(config.cfg.current_OPEN_API_MODELNAME, config.cfg.current_OPENAI_API_BASE,config.cfg.current_OPENAI_API_KEY, maxNewtoken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        chunkitem: chunk # typehint
        for chunkitem in self.sourcetranslation.chunks:
            if not config.continueProcess: break
            if chunkitem.chunkID < start_at_chunkID: continue
            if stop_at_chunkID and chunkitem.chunkID > stop_at_chunkID: break
            nextprocessedchunk = self.processedTranslation.chunkExists(chunkitem.chunkID)
            # 1. Fall Chunk existiert bereits, nicht überschreiben -> skip
            if nextprocessedchunk and not self.overwrite: continue
            # 2. Chunk existiert noch nicht -> neu anlegen
            if not nextprocessedchunk: 
                nextprocessedchunk = copy.deepcopy(chunkitem) # !Deepcopy
                self.processedTranslation.chunks.append(nextprocessedchunk)
            # eigentliche Verarbeitung
            if chunkitem.chunktype not in self.sourcetranslation.chunkTypeNoProcess: # blacklist
                log.printlog(f'do: {chunkitem.chunkID}/{self.sourcetranslation.numberOfChunks} {chunkitem.source_chaptername}' + \
                        f' ({chunkitem.chunktype})')
                if chunkitem.chunktype == 'heading' and config.cfg.translateHeading:
                    # abweichender Systemprompt für Überschriften nötig?
                    nextcontent = llm.request(self._inputtext_safe(chunkitem.content), self.prompt)
                    #nextcontent = llm.request(self._inputtext_safe(chunkitem.content), config.get_promptsetByID(config.AllPromptset,12))
                elif chunkitem.chunktype == 'heading':
                    nextcontent = self._inputtext_safe(chunkitem.content)
                else:
                    nextcontent = llm.request(self._inputtext_safe(chunkitem.content), self.prompt)
                if nextcontent:
                    if not self.processedTranslation.promptset.allowLongAnswer:
                        wordcountsource = chunkitem.content.count(' ')
                        wordcountnew = nextcontent.count(' ')
                        if wordcountnew > wordcountsource: nextcontent = chunkitem.content + ' *99'
                    nextprocessedchunk.content = nextcontent
                    if chunkitem.chunktype == 'heading' and config.cfg.translateHeading:
                        nextprocessedchunk.content =  chunkitem.content + ' (' +  nextcontent + ')'
                    log.print(f'{nextprocessedchunk.content}')
                    autosaveno += 1
                    if autosaveno >= self.autosaveInterval: 
                        self.mainstore4save.save()
                        log.print('autosave estore finished.')
                        # if previewOnAutosave: 
                        #     publishPreview.html_filename = self.mainstore4save.pathout + '_SBSpreview.html'
                        #     publishPreview.genHTML_SideBySide([self.mainstore4save.source] + self.mainstore4save.translations,
                        #             'templates/defaultsbs.css',True,start_at_chunkID,stop_at_chunkID)
                        #     log.print('preview finished.')
                        autosaveno = 0
                else:
                    log.error('Error LLM (Timeout?) - abort processor ')
                    self.aborted = True
                    break            
        self.processedTranslation.chunks.sort() # neu sortieren, fall neue Übersetzungen hinzugekommen sind
        if not self.aborted: self.finished = True
        lenprocess = len(self.processedTranslation.chunks)
        lensource = len(self.sourcetranslation.chunks)
        if lenprocess == lensource:
            self.processedTranslation.set_finished()
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource} -> complete')
        else:
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource}')
        self.mainstore4save.save()
    
    def _inputtext_safe(self,inputtext: str) -> str:
        inputtext_safe = inputtext.replace("<|", "< |").replace("|>", "| >") # verhindert interpreation von 
        # <|im_start|>user and <|im_end|>, tags
        # requesttext = self.prompt.prePrompt + inputtext_safe + self.prompt.postPrompt
        # preprompt und Postpromt jetzt im call
        return inputtext_safe


class processorMultiSource(processor): # pylint: disable=unused-variable
    def __init__(self, sourcetranslation: translation, sourcetranslations: list[translation], processedTranslation: translation, mainstore4save: mainstore,
                 translationmodelname: str, prompt: promptset):
        super().__init__(sourcetranslation, processedTranslation, mainstore4save, translationmodelname, prompt)
        self.sourcetranslations: list[translation] = sourcetranslations
        self.sourcecount = len(self.sourcetranslations)
        self.sourcemodelnames = ", ".join(t.modelname for t in self.sourcetranslations)
        log.printlog(f'Setup processorMultiSource: {", ".join(t.modelname for t in self.sourcetranslations)}')

        
    def do(self, start_at_chunkID = 0, stop_at_chunkID = None) -> None:
        log.printlog(f'processing (multipleSources: {self.sourcecount}): {self.sourcemodelnames}')
        # TBD: Vergleichsprozessor
        if not self.prompt: # Ohne Prompt nur kopieren
            log.error('process None-Type Prompt? - skip)')
            return     
        autosaveno = 0
        llm = llmcaller(config.cfg.current_OPEN_API_MODELNAME, config.cfg.current_OPENAI_API_BASE,config.cfg.current_OPENAI_API_KEY, self.prompt.maxNewToken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        chunkitem: chunk # typehint
        for chunkitem in self.sourcetranslations[0].chunks:
            if not config.continueProcess: break
            if chunkitem.chunkID < start_at_chunkID: continue
            if stop_at_chunkID and chunkitem.chunkID > stop_at_chunkID: break
            nextprocessedchunk = self.processedTranslation.chunkExists(chunkitem.chunkID)
            # 1. Fall Chunk existiert bereits, nicht überschreiben -> skip
            if nextprocessedchunk and not self.overwrite: continue
            # 2. Chunk existiert noch nicht -> neu anlegen
            if not nextprocessedchunk: 
                nextprocessedchunk = copy.deepcopy(chunkitem) # !Deepcopy
                self.processedTranslation.chunks.append(nextprocessedchunk)
            # eigentliche Verarbeitung
            if chunkitem.chunktype not in self.sourcetranslations[0].chunkTypeNoProcess: # blacklist
                log.printlog(f'do(multipleSources): {chunkitem.chunkID}/{self.sourcetranslation.numberOfChunks} {chunkitem.source_chaptername}' + \
                        f' ({chunkitem.chunktype})')
                chunkitem0 = self._getChunkitemByChunkID(self.sourcetranslation, chunkitem.chunkID)
                chunkitem1 = chunkitem
                chunkitem2 = self._getChunkitemByChunkID(self.sourcetranslations[1], chunkitem.chunkID)
                if chunkitem0 is None :
                    log.printlog(f'chunk {chunkitem.chunkID} in source nicht bereit')
                    continue
                if chunkitem2 is None :
                    log.printlog(f'chunk {chunkitem.chunkID} in {self.sourcetranslations[1].modelname} nicht bereit')
                    continue
                promptcontent = '##SOURCE:\n' + chunkitem0.content + '##SAMPLE A:\n' + chunkitem1.content + '\n##SAMPLE B:\n' + chunkitem2.content + '\n'
                #log.printlog(promptcontent)
                #nextcontent = 'promptcontent' # llm.request(self._inputtext_safe(chunkitem.content), self.prompt)
                nextcontent = llm.request(self._inputtext_safe(promptcontent), self.prompt)
                if nextcontent:
                    # if not self.processedTranslation.promptset.allowLongAnswer:
                    #     wordcountsource = chunkitem.content.count(' ')
                    #     wordcountnew = nextcontent.count(' ')
                    #     if wordcountnew > wordcountsource: nextcontent = chunkitem.content + ' *99'
                    nextprocessedchunk.content = nextcontent
                    # if chunkitem.chunktype == 'heading':
                    #     nextprocessedchunk.content =  chunkitem.content + ' (' +  nextcontent + ')'
                    log.print(f'{nextprocessedchunk.content}')
                    autosaveno += 1
                    if autosaveno >= self.autosaveInterval: 
                        self.mainstore4save.save()
                        log.print('autosave estore finished.')
                        autosaveno = 0
                else:
                    log.error('Error LLM (no anwer = Timeout?) - aborting processor ')
                    self.aborted = True
                    break            
        self.processedTranslation.chunks.sort() # neu sortieren, fall neue Übersetzungen hinzugekommen sind
        if not self.aborted: self.finished = True
        lenprocess = len(self.processedTranslation.chunks)
        lensource = len(self.sourcetranslation.chunks)
        if lenprocess == lensource:
            self.processedTranslation.set_finished()
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource} -> complete')
        else:
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource}')
        self.mainstore4save.save()
        
    def _getChunkitemByChunkID(self, t: translation, chID: int) -> chunk | None:
        chunkitem: chunk
        for chunkitem in t.chunks:
            if chunkitem.chunkID == chID:
                return chunkitem
        return None
        
        