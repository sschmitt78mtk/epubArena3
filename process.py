#from typing import Union, Any
from __future__ import annotations # pylint: disable=unused-variable
#import re
import copy
import asyncio
from typing import List, Tuple
from store import Chunk, Translation, Mainstore
from prompts import Promptset

from errorLog import log
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
    
    async def _do_async_impl(self, start_at_chunkID=0, stop_at_chunkID=None) -> None:
        """Async implementation with parallel processing (max 4 concurrent calls)"""
        log.printlog(f'processing {self.processedTranslation.modelname}')
        if not self.prompt:  # Ohne Prompt nur kopieren
            log.error('process None-Type Prompt? - skip)')
            return
        
        # Create LLM caller
        maxNewtoken = self.prompt.maxNewToken
        if self.prompt.allowLongAnswer:
            maxNewtoken *= 3  # Wenn nur Übersetzung -> lange Texte erlauben
        llm = Llmcaller(config.cfg.current_open_api_modelname,
                       config.cfg.current_openai_api_base,
                       config.cfg.current_openai_api_key,
                       maxNewtoken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        
        # Prepare chunks for processing
        chunks_to_process: List[Tuple[Chunk, Chunk]] = []
        existing_chunk_ids = {chunk.chunk_id for chunk in self.processedTranslation.chunks}
        for chunkitem in self.sourcetranslation.chunks:
            if not config.continue_process:
                break
            if chunkitem.chunk_id < start_at_chunkID:
                continue
            if stop_at_chunkID and chunkitem.chunk_id > stop_at_chunkID:
                break
            
            nextprocessedchunk = self.processedTranslation.chunk_exists(chunkitem.chunk_id)
            if nextprocessedchunk and not self.overwrite:
                continue
            
            if not nextprocessedchunk:
                nextprocessedchunk = copy.deepcopy(chunkitem)  # !Deepcopy
                if chunkitem.chunktype in self.sourcetranslation.chunk_type_no_process:
                    self.processedTranslation.chunks.append(nextprocessedchunk)
            
            if chunkitem.chunktype not in self.sourcetranslation.chunk_type_no_process:
                chunks_to_process.append((chunkitem, nextprocessedchunk))
        
        # Process chunks in parallel with semaphore limiting to 4 concurrent calls
        semaphore = asyncio.Semaphore(4)
        autosaveno = 0
        
        async def process_chunk(chunkitem: Chunk, nextprocessedchunk: Chunk) -> bool:
            """Process a single chunk asynchronously"""
            async with semaphore:
                try:
                    log.printlog(f'do: {chunkitem.chunk_id}/{self.sourcetranslation.number_of_chunks} '
                                f'{chunkitem.source_chaptername} ({chunkitem.chunktype})')
                    
                    if chunkitem.chunktype == 'heading' and config.cfg.translate_heading:
                        # abweichender Systemprompt für Überschriften nötig?
                        headingwordcount = chunkitem.content.count(' ') + 1  # minimum 1 Word
                        maxtokenheading = headingwordcount * 4  # translation of heading is max. 3x wordcount
                        nextcontent = await llm.request_async(
                            self._inputtext_safe(chunkitem.content),
                            self.prompt,
                            maxtokenheading
                        )
                    elif chunkitem.chunktype == 'heading':
                        nextcontent = self._inputtext_safe(chunkitem.content)
                    else:
                        nextcontent = await llm.request_async(
                            self._inputtext_safe(chunkitem.content),
                            self.prompt
                        )
                    
                    if nextcontent:
                        if not self.processedTranslation.promptset.allowLongAnswer:
                            wordcountsource = chunkitem.content.count(' ')
                            wordcountnew = nextcontent.count(' ')
                            if wordcountnew > wordcountsource:
                                nextcontent = chunkitem.content + ' *99'
                        
                        nextprocessedchunk.content = nextcontent
                        if chunkitem.chunktype == 'heading' and config.cfg.translate_heading:
                            nextprocessedchunk.content = chunkitem.content + ' (' + nextcontent + ')'
                        
                        if nextprocessedchunk.chunk_id not in existing_chunk_ids:
                            self.processedTranslation.chunks.append(nextprocessedchunk)
                        log.print(f'{nextprocessedchunk.content}')
                        return True
                    else:
                        log.error(f'Error LLM for chunk {chunkitem.chunk_id} - skipping')
                        return False
                        
                except Exception as e:
                    log.error(f'Error processing chunk {chunkitem.chunk_id}: {str(e)}')
                    return False
        
        # Create tasks for all chunks
        tasks = []
        for chunkitem, nextprocessedchunk in chunks_to_process:
            task = asyncio.create_task(process_chunk(chunkitem, nextprocessedchunk))
            tasks.append(task)
        
        # Process results as they complete
        for completed_task in asyncio.as_completed(tasks):
            success = await completed_task
            if success:
                autosaveno += 1
                if autosaveno >= self.autosaveInterval:
                    self.mainstore4save.save()
                    log.print('autosave estore finished.')
                    autosaveno = 0
            
            # Check if processing should be stopped
            if not config.continue_process:
                log.printlog('Processing stopped by user request')
                # Cancel remaining tasks
                for task in tasks:
                    if not task.done():
                        task.cancel()
                break
        
        # Final processing
        self.processedTranslation.chunks.sort()  # neu sortieren, fall neue Übersetzungen hinzugekommen sind
        if not self.aborted:
            self.finished = True
        
        lenprocess = len(self.processedTranslation.chunks)
        lensource = len(self.sourcetranslation.chunks)
        if lenprocess == lensource:
            self.processedTranslation.set_finished()
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource} -> complete')
        else:
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource}')
        
        self.mainstore4save.save()
    
    def do(self, start_at_chunkID=0, stop_at_chunkID=None) -> None:
        """Synchronous wrapper for async processing"""
        asyncio.run(self._do_async_impl(start_at_chunkID, stop_at_chunkID))
    
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

        
    async def _do_async_impl(self, start_at_chunkID=0, stop_at_chunkID=None) -> None:
        """Async implementation for multi-source processing with parallel processing"""
        log.printlog(f'processing (multipleSources: {self.sourcecount}): {self.sourcemodelnames}')
        # TBD: Vergleichsprozessor
        if not self.prompt:  # Ohne Prompt nur kopieren
            log.error('process None-Type Prompt? - skip)')
            return
        
        # Create LLM caller
        llm = Llmcaller(config.cfg.current_open_api_modelname,
                       config.cfg.current_openai_api_base,
                       config.cfg.current_openai_api_key,
                       self.prompt.maxNewToken)
        llm.temperature = self.prompt.temperature
        llm.top_p = self.prompt.top_p
        llm.system_message = self.prompt.system_message
        
        # Prepare chunks for processing
        chunks_to_process: List[Tuple[Chunk, Chunk]] = []
        existing_chunk_ids = {chunk.chunk_id for chunk in self.processedTranslation.chunks}
        for chunkitem in self.sourcetranslations[0].chunks:
            if not config.continue_process:
                break
            if chunkitem.chunk_id < start_at_chunkID:
                continue
            if stop_at_chunkID and chunkitem.chunk_id > stop_at_chunkID:
                break
            
            nextprocessedchunk = self.processedTranslation.chunk_exists(chunkitem.chunk_id)
            if nextprocessedchunk and not self.overwrite:
                continue
            
            if not nextprocessedchunk:
                nextprocessedchunk = copy.deepcopy(chunkitem)  # !Deepcopy
                if chunkitem.chunktype not in self.sourcetranslations[0].chunk_type_no_process:
                    # defer append until processed to avoid placeholders on abort
                    pass
                else:
                    self.processedTranslation.chunks.append(nextprocessedchunk)
            
            if chunkitem.chunktype not in self.sourcetranslations[0].chunk_type_no_process:
                chunks_to_process.append((chunkitem, nextprocessedchunk))
        
        # Process chunks in parallel with semaphore limiting to 4 concurrent calls
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_CALLS)
        autosaveno = 0
        
        async def process_chunk(chunkitem: Chunk, nextprocessedchunk: Chunk) -> bool:
            """Process a single chunk asynchronously for multi-source"""
            async with semaphore:
                try:
                    log.printlog(f'do(multipleSources): {chunkitem.chunk_id}/{self.sourcetranslation.number_of_chunks} '
                                f'{chunkitem.source_chaptername} ({chunkitem.chunktype})')
                    
                    chunkitem0 = self._getChunkitemByChunkID(self.sourcetranslation, chunkitem.chunk_id)
                    chunkitem1 = chunkitem
                    chunkitem2 = self._getChunkitemByChunkID(self.sourcetranslations[1], chunkitem.chunk_id)
                    
                    if chunkitem0 is None:
                        log.printlog(f'chunk {chunkitem.chunk_id} in source nicht bereit')
                        return False
                    if chunkitem2 is None:
                        log.printlog(f'chunk {chunkitem.chunk_id} in {self.sourcetranslations[1].modelname} nicht bereit')
                        return False
                    
                    promptcontent = '##SOURCE:\n' + chunkitem0.content + '##SAMPLE A:\n' + chunkitem1.content + '\n##SAMPLE B:\n' + chunkitem2.content + '\n'
                    
                    nextcontent = await llm.request_async(self._inputtext_safe(promptcontent), self.prompt)
                    
                    if nextcontent:
                        nextprocessedchunk.content = nextcontent
                        if nextprocessedchunk.chunk_id not in existing_chunk_ids:
                            self.processedTranslation.chunks.append(nextprocessedchunk)
                        log.print(f'{nextprocessedchunk.content}')
                        return True
                    else:
                        log.error(f'Error LLM for chunk {chunkitem.chunk_id} - skipping')
                        return False
                        
                except Exception as e:
                    log.error(f'Error processing chunk {chunkitem.chunk_id}: {str(e)}')
                    return False
        
        # Create tasks for all chunks
        tasks = []
        for chunkitem, nextprocessedchunk in chunks_to_process:
            task = asyncio.create_task(process_chunk(chunkitem, nextprocessedchunk))
            tasks.append(task)
        
        # Process results as they complete
        for completed_task in asyncio.as_completed(tasks):
            success = await completed_task
            if success:
                autosaveno += 1
                if autosaveno >= self.autosaveInterval:
                    self.mainstore4save.save()
                    log.print('autosave estore finished.')
                    autosaveno = 0
        
        # Final processing
        self.processedTranslation.chunks.sort()  # neu sortieren, fall neue Übersetzungen hinzugekommen sind
        if not self.aborted:
            self.finished = True
        
        lenprocess = len(self.processedTranslation.chunks)
        lensource = len(self.sourcetranslation.chunks)
        if lenprocess == lensource:
            self.processedTranslation.set_finished()
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource} -> complete')
        else:
            log.printlog(f'processing {self.processedTranslation.modelname} {lenprocess}/{lensource}')
        
        self.mainstore4save.save()
    
    def do(self, start_at_chunkID=0, stop_at_chunkID=None) -> None:
        """Synchronous wrapper for async processing"""
        asyncio.run(self._do_async_impl(start_at_chunkID, stop_at_chunkID))
        
    def _getChunkitemByChunkID(self, t: Translation, chID: int) -> Chunk | None:
        chunkitem: Chunk
        for chunkitem in t.chunks:
            if chunkitem.chunk_id == chID:
                return chunkitem
        return None
        
        
