#from typing import Union, Any
from __future__ import annotations # pylint: disable=unused-variable
#import re
import copy
from store import Chunk, Translation, Mainstore
from prompts import Promptset

from ErrorLog import log
from call import Llmcaller
import config

# class chapterhtmlpkg(chunk):
#     def __init__(self, source_chaptername: str, html_str: str):
#         self.chapterhtml_str = html_str
#         super().__init__() 

class Processor: 
    def __init__(self, sourcetranslation: Translation, processedTranslation: Translation, mainstore4save: Mainstore,
                 translationmodelname: str, prompt: Promptset):
        self.sourcetranslation: Translation = sourcetranslation
        self.processedTranslation = processedTranslation
        self.processedTranslation.modelname = translationmodelname # + str(prompt.PromptID)
        self.processedTranslation.promptset = prompt
        self.mainstore4save = mainstore4save # ermöglicht dem processor den mainstore zu speichern.
        self.overwrite = False
        self.finished = False
        self.prompt = prompt
        self.aborted = False
        self.autosave = config.cfg.processor_autosave
        self.autosaveInterval = config.cfg.processor_autosave_interval# alle 10 chunks speichern
    
    def do(self, start_at_chunkID = 0, stop_at_chunkID = None) -> None:
        log.printlog(f'processing {self.processedTranslation.modelname}')
        if not self.prompt: # Ohne Prompt nur kopieren
            log.error('process None-Type Prompt? - skip)')
            return     
        autosaveno = 0
        maxNewtoken = self.prompt.maxNewToken
        if self.prompt.allowLongAnswer: maxNewtoken *= 3 # Wenn nur Übersetzung -> lange Texte erlauben
        llm = Llmcaller(config.cfg.current_open_api_modelname, config.cfg.current_openai_api_base,config.cfg.current_openai_api_key, maxNewtoken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        chunkitem: Chunk # typehint
        for chunkitem in self.sourcetranslation.chunks:
            if not config.continue_process: break
            if chunkitem.chunk_id < start_at_chunkID: continue
            if stop_at_chunkID and chunkitem.chunk_id > stop_at_chunkID: break
            nextprocessedchunk = self.processedTranslation.chunk_exists(chunkitem.chunk_id)
            # 1. Fall Chunk existiert bereits, nicht überschreiben -> skip
            if nextprocessedchunk and not self.overwrite: continue
            # 2. Chunk existiert noch nicht -> neu anlegen
            if not nextprocessedchunk: 
                nextprocessedchunk = copy.deepcopy(chunkitem) # !Deepcopy
                self.processedTranslation.chunks.append(nextprocessedchunk)
            # eigentliche Verarbeitung
            if chunkitem.chunktype not in self.sourcetranslation.chunk_type_no_process: # blacklist
                log.printlog(f'do: {chunkitem.chunk_id}/{self.sourcetranslation.number_of_chunks} {chunkitem.source_chaptername}' + \
                        f' ({chunkitem.chunktype})')
                if chunkitem.chunktype == 'heading' and config.cfg.translate_heading:
                    # abweichender Systemprompt für Überschriften nötig?
                    headingwordcount = chunkitem.content.count(' ') + 1 # minimum 1 Word
                    maxtokenheading = headingwordcount * 4 # translation of heading is max. 3x wordcount
                    nextcontent = llm.request(self._inputtext_safe(chunkitem.content), self.prompt, maxtokenheading)
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
                    if chunkitem.chunktype == 'heading' and config.cfg.translate_heading:
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


class ProcessorMultiSource(Processor): # pylint: disable=unused-variable
    def __init__(self, sourcetranslation: Translation, sourcetranslations: list[Translation], processedTranslation: Translation, mainstore4save: Mainstore,
                 translationmodelname: str, prompt: Promptset):
        super().__init__(sourcetranslation, processedTranslation, mainstore4save, translationmodelname, prompt)
        self.sourcetranslations: list[Translation] = sourcetranslations
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
        llm = Llmcaller(config.cfg.current_open_api_modelname, config.cfg.current_openai_api_base,config.cfg.current_openai_api_key, self.prompt.maxNewToken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        chunkitem: Chunk # typehint
        for chunkitem in self.sourcetranslations[0].chunks:
            if not config.continue_process: break
            if chunkitem.chunk_id < start_at_chunkID: continue
            if stop_at_chunkID and chunkitem.chunk_id > stop_at_chunkID: break
            nextprocessedchunk = self.processedTranslation.chunk_exists(chunkitem.chunk_id)
            # 1. Fall Chunk existiert bereits, nicht überschreiben -> skip
            if nextprocessedchunk and not self.overwrite: continue
            # 2. Chunk existiert noch nicht -> neu anlegen
            if not nextprocessedchunk: 
                nextprocessedchunk = copy.deepcopy(chunkitem) # !Deepcopy
                self.processedTranslation.chunks.append(nextprocessedchunk)
            # eigentliche Verarbeitung
            if chunkitem.chunktype not in self.sourcetranslations[0].chunk_type_no_process: # blacklist
                log.printlog(f'do(multipleSources): {chunkitem.chunk_id}/{self.sourcetranslation.number_of_chunks} {chunkitem.source_chaptername}' + \
                        f' ({chunkitem.chunktype})')
                chunkitem0 = self._getChunkitemByChunkID(self.sourcetranslation, chunkitem.chunk_id)
                chunkitem1 = chunkitem
                chunkitem2 = self._getChunkitemByChunkID(self.sourcetranslations[1], chunkitem.chunk_id)
                if chunkitem0 is None :
                    log.printlog(f'chunk {chunkitem.chunk_id} in source nicht bereit')
                    continue
                if chunkitem2 is None :
                    log.printlog(f'chunk {chunkitem.chunk_id} in {self.sourcetranslations[1].modelname} nicht bereit')
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
        
    def _getChunkitemByChunkID(self, t: Translation, chID: int) -> Chunk | None:
        chunkitem: Chunk
        for chunkitem in t.chunks:
            if chunkitem.chunk_id == chID:
                return chunkitem
        return None
        
        