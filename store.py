from __future__ import annotations # pylint: disable=unused-variable
from typing import Any
import pickle
import os
from pathlib import Path
#import json
import html
import base64 # Für Einbettung von Image
#from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from errorLog import log
from jaccard import jaccard_clean
import config
from prompts import Promptset


if config.cfg.use_markdown:
    import markdown
    
class Chunk:
    def __init__(self, source_chaptername: str, chunk_id: int, chunktype: str, content: str, chapter_id = None):
        self.source_chaptername = source_chaptername
        self.chapter_id = chapter_id
        self.chunk_id = chunk_id
        self.content = content
        self.chunktype = chunktype # text, image, heading, table, raw 
        self.headinglevel = ''
        self.imagedata = ''
        self.metadata: list[dict[str, Any]] = []
    
    def htmlp(self, do_jaccard_clean = False) -> str: # für epubPublication
        htmlsafecontent = htmlsafe(self.content)
        htmlp = ''
        if self.chunktype == "heading":
            htmlp = f'<{self.headinglevel}>{htmlsafecontent}</{self.headinglevel}>'
        elif self.chunktype == "image":
            htmlp = f'<figure class="mediaobject"><img src="{htmlsafecontent.replace("../","")}" /></figure>'
        elif self.chunktype == "table":
            htmlp = f'<div class ="etable">{htmlsafecontent}</div>'
        else:
            content2 = htmlsafecontent
            if do_jaccard_clean: 
                jaccardwin, content2 = jaccard_clean(content2)
                if jaccardwin < 0.99: log.printlog(f"Jaccard_clean ({self.chunk_id}): {jaccardwin:.2f}")
            #if content2 != self.content: print('jaccard:' + self.content)
            if config.cfg.use_markdown: content2 = markdown.markdown(content2)
            htmlp = f'<p class="normal">{content2}</p>\n'
        return htmlp
    
    def __lt__(self, other):
         return self.chunk_id < other.chunk_id

class Translation:
    def __init__(self, modelname: str):
        self.modelname = modelname
        self.promptset = Promptset(0,'','','','New')
        self.chunks : list[Chunk] = [] 
        self.number_of_chunks = 99999
        self.finished = False
        #self.chunkTypeNoTranslate = ['heading','table']
        #self.chunkTypeNoProcess = ['image','heading','table']
        self.chunk_type_no_translate = ['table']
        self.chunk_type_no_process = ['image','table']
        self.author = ''
        self.title = ''
        self.language = ''
    
    def chunk_exists(self, chunk_id: int) -> Chunk | None:
        chunk_asked_for: Chunk # typehint
        for chunk_asked_for in self.chunks:
            if chunk_asked_for.chunk_id == chunk_id: return chunk_asked_for
        return None
    
    def set_metadata(self, booktitle: str, bookauthor: str, booklanguage: str) -> None:
        self.title = booktitle
        self.author = bookauthor
        self.language = booklanguage
    
    def set_finished(self, finishstate = True) -> None:
        if finishstate:
            self.number_of_chunks = len(self.chunks)
            self.finished = True
        else:
            self.number_of_chunks = 9999
            self.finished = False
            
    def info(self) -> str:
        modelinfo = f'Modellname: {self.modelname}\n'
        promptinfo = f'{self.promptset.info()}\n'
        wordcountt = 0
        for chunkitem in self.chunks:
            wordcountt += chunkitem.content.count(' ')
        wordcount = f'wordcount: {str(wordcountt)}\n'
        return modelinfo + promptinfo + wordcount

                  
class Mainstore:
    def __init__(self, source_epub_filename: str):
        self.source_epub_filename = source_epub_filename
        self.pkl_filename = source_epub_filename + '.pkl'
        # self.author = ''
        # self.title = ''
        # self.language = ''
        self.source : Translation = Translation('Original')
        self.translations : list[Translation] = []
        self.finished = False
   
    def save(self) -> None:
        try:
            with open(config.PATH_PKL + self.pkl_filename, 'wb') as file:
                pickle.dump(self, file)
        except Exception as exc:
            log.error(f'Fehler beim Schreiben von {self.pkl_filename}, {str(exc)}')
            
    # def _load(self):
    #     try:
    #         with open(self.pklFilename, 'rb') as f:
    #             self = pickle.load(f)
    #     except Exception as e:
    #         log.printlog(f'{self.pklFilename} konnte nicht geladen werden. {str(e)}')

    def getTranslationByModelName(self, modelname: str) -> Translation:
        '''
        Wenn es noch keine Übersetzung mit dem Namen gibt, wird eine erstellt
        '''
        for t in self.translations:
            if t.modelname == modelname: 
                log.printlog(f'translation mit modelname {modelname} gefunden')
                return t
        newTranslation = Translation(modelname)
        newTranslation.number_of_chunks = self.source.number_of_chunks
        self.translations.append(newTranslation)
        log.printlog(f'translation mit modelname {modelname} nicht gefunden, wird erstellt')
        return newTranslation
    
    def getmultipleTranslationsByModelNames(self, modelnames: str) -> list[Translation]:
        '''
        mehrere modelnames (Semikolon als Trennzeichen) gibt eine Liste 
        '''
        translationNames = [item.strip() for item in modelnames.split(';')]
        translations: list[Translation] = []
        for translationName in translationNames:        
            notfound = True
            for t in self.translations:
                if t.modelname == translationName: 
                    log.printlog(f'translation mit modelname {translationName} gefunden')
                    translations.append(t)
                    notfound = False                 
            if notfound:
                newTranslation = Translation(translationName)
                newTranslation.number_of_chunks = self.source.number_of_chunks
                self.translations.append(newTranslation)
                translations.append(newTranslation)
                log.printlog(f'translation mit modelname {translationName} nicht gefunden, wird erstellt')
        return translations
        
    def info(self) -> None:
        log.printlog(f'estore translations: {str(len(self.translations))}')
        for tr in self.translations:
            log.printlog(f'estore translation modelname : {str(tr.modelname)} - {tr.language} - ({str(len(tr.chunks))} chunks)')
    
    def removeEmptyTranslations(self) -> None:
        # Der Pythonic-Weg, um Elemente basierend auf einer Bedingung zu entfernen, ist die Verwendung einer 
        # List Comprehension. Dabei erstellst du eine neue Liste, die nur die Elemente enthält, die die 
        # Bedingung erfüllen.
        self.translations = [t for t in self.translations if len(t.chunks) != 0]    
    
    def removeTranslationsByName(self, modname: str) -> None:
        log.printlog(f'Translation mit Name "{modname}" aus store gelöscht (falls vorhanden).')
        self.translations = [t for t in self.translations if t.modelname != modname]                                       
   
def loadstore(source_epub_filename: str) -> Mainstore: # pylint: disable=unused-variable
    pkl_filename = config.PATH_PKL + source_epub_filename + '.pkl'
    try:
        with open(pkl_filename, 'rb') as file:
            data = pickle.load(file)
        log.printlog(f'Daten aus PKL-Datei {pkl_filename} geladen.')
        return data
    except Exception as exc:
            log.printlog(f'{pkl_filename} konnte nicht geladen werden. {str(exc)}')
            return (Mainstore(source_epub_filename)) # wenn es nicht geladen werden kann, einen neuen erstellen  
      
    
class Publication: # pylint: disable=unused-variable
    def __init__(self, mainstoreproject: Mainstore):
        self.mainstoreproject = mainstoreproject
        self.source_epub_filename = mainstoreproject.source_epub_filename
        self.html_filename = self.source_epub_filename + '.html'
        self.outputpath = ''
        self.jaccard_clean = False # True
    
    def genHTML(self, translation_project: Translation, css_file = 'templates/default.css', preview = False, 
                link_to_pictures = False, save_file = True) -> str:
        css = self._loadcss(css_file)
        html_str =  f'<html><head><style>{css}</style>'
        html_str += '<meta http-equiv="content-type" content="text/html; charset=UTF-8">'
        if not translation_project.finished:
            html_str += '<meta http-equiv="refresh" content="30" >'
        html_str += f'<title>{self.source_epub_filename} - summary</title></head>\n<body>\n'
        for chunk_item in translation_project.chunks:
            log.print(f'genHTML: {chunk_item.chunk_id}/{translation_project.number_of_chunks} {chunk_item.source_chaptername}')
            if chunk_item.chunktype == 'image':
                if link_to_pictures: # epubPublishing
                    html_str += f'<figure class="mediaobject"><img src="{chunk_item.content.replace("../","")}" /></figure>'
                elif preview: 
                    html_str += f'<p>image {chunk_item.content}</p>\n'
                else:
                    mime, base64_string = getbase64image(self.source_epub_filename,chunk_item.content)
                    html_str += f'<img class= "figure" src="data:image/{mime};base64,{base64_string}" />\n'
            elif chunk_item.chunktype == 'heading':
                html_str += f'<{chunk_item.headinglevel}>{chunk_item.content}</{chunk_item.headinglevel}>'
            elif chunk_item.chunktype == 'table':
                html_str += f'<div class ="etable">{chunk_item.content}</div>'
            else:
                # TBD: self.jaccard_clean 
                html_str += f'<p>{chunk_item.content}<br><cs class="chunkid">{chunk_item.chunk_id}</cs></p>'
        html_str += translation_project.promptset.info()
        html_str += '</body>\n</html>'
        if save_file:
            try:
                with open(config.PATH_OUT + self.html_filename, "w", encoding="utf-8") as text_file:
                    text_file.write(html_str)
            except Exception as exc:
                log.error(f'Fehler beim Schreiben von {self.html_filename}, {str(exc)}')
        return html_str

    def genHTML_SideBySide(self, translation_projects: list[Translation], css_file = 'templates/defaultsbs.css', preview = False,
                           start_at_chunk_id = 0, stop_at_chunk_id = None, nav_style = 1) -> None:
        css = self._loadcss(css_file)
        numcolumns = len(translation_projects)
        html_str =  f'<html><head><style>{css}</style>'
        if nav_style == 1:
            js = self._loadcss('templates/defaultsbs.js')
            html_str +=  f'<script>{js}'
            for i, k in enumerate(translation_projects):
                html_str += f"\nconst toggleCol{str(i+1)} = document.getElementById('toggleCol{str(i+1)}');"
                html_str += f"\ntoggleCol{str(i+1)}.addEventListener('change', function() " + '{toggleColumn(' + str(i) + ', this.checked);});'
            html_str += "const textcompare = document.getElementById('textcompare');"
            html_str += "\ntextcompare.addEventListener('change', function() {toggleColumn(99, this.checked);});"
            html_str += "\n});\n</script>\n"
        html_str += '<meta http-equiv="content-type" content="text/html; charset=UTF-8">'
        html_str += f'<title>{self.source_epub_filename} - summary</title></head>\n<body>\n'
        if nav_style == 1:
            html_str += '<nav class="navbar"><div class="controls">'
            for i, transl_project in enumerate(translation_projects): #  in range(len(translation_projects)):
                html_str += f'<label><input type="checkbox" id="toggleCol{str(i+1)}" checked>{transl_project.modelname} ({str(i+1)})</label>'    
            html_str += '<label><input type="checkbox" id="textcompare">compare</label></div></nav>'
        html_str += '<div class="content">'
        html_str += '<table id="translationstable" width="100%" cellspacing="2" cellpadding="2" border="1"><tbody>\n' 
        for chunk_item in translation_projects[0].chunks:
            log.print(f'genHTMLsbs: {chunk_item.chunk_id}/{translation_projects[0].number_of_chunks} {chunk_item.source_chaptername}')
            if chunk_item.chunk_id < start_at_chunk_id: continue
            if stop_at_chunk_id and chunk_item.chunk_id > stop_at_chunk_id: break
            htmlsafecontent = htmlsafe(chunk_item.content) 
            if chunk_item.chunktype == 'image':
                if preview: 
                    html_str += f'<tr class="imagerow"><th colspan="{numcolumns}"><p>image {htmlsafecontent}</p></th></tr>\n'
                else:
                    mime, base64_string = getbase64image(self.source_epub_filename,chunk_item.content)
                    html_str += f'<tr class="imagerow"><th colspan="{numcolumns}"><img src="data:image/{mime};base64,{base64_string}" /></th></tr>\n'
            elif chunk_item.chunktype == 'heading':
                html_str += f'<tr class="headingrow"><th colspan="{numcolumns}"><{chunk_item.headinglevel}>{htmlsafecontent}</{chunk_item.headinglevel}></th></tr>\n'

            elif chunk_item.chunktype == 'table':
                html_str += f'<tr class="etable"><th colspan="{numcolumns}"><pre>{chunk_item.content}</pre></th></tr>\n'
            else:
                # spalte 1 source, spalte 2 translation
                html_str += f'<tr><td class="translation">{htmlsafecontent}<br><cs class="chunkid">{chunk_item.chunk_id}</cs></td>'
                for tproject in translation_projects[1:]:# erstes überspringen 
                    content2 = htmlsafe(self._content_by_chunk_id(chunk_item.chunk_id,tproject))
                    if self.jaccard_clean: 
                        jaccardwin, content2 = jaccard_clean(content2)
                        if jaccardwin < 0.99: log.printlog(f"Jaccard_clean ({chunk_item.chunk_id}): {jaccardwin:.2f}")
                    if config.cfg.use_markdown: content2 = markdown.markdown(content2)
                    # print(content2)
                    html_str += f'<td class="translation"><div>{content2}</div></td>'
                html_str += '</tr>\n'  
        
        html_str += '<td class="translation">' + translation_projects[0].info().replace("\n","<br>")+ '</td>'
        for tproject in translation_projects[1:]: # erstes überspringen
            html_str += '<td class="translation">' + tproject.info().replace("\n","<br>")+ '</td>'
        html_str += '</tr>\n'  
        html_str += '</tbody></table><br></div>\n</body>\n</html>'
        try:
            with open(config.PATH_OUT + self.html_filename, "w", encoding="utf-8") as text_file:
                    text_file.write(html_str)
        except Exception as exc:
            log.error(f'Fehler beim Schreiben von {self.html_filename}, {str(exc)}')
    
    def _content_by_chunk_id(self, chunk_id: int, translation_obj: Translation) -> str:
        for chunk_item in translation_obj.chunks:
            if chunk_item.chunk_id == chunk_id: return chunk_item.content
        return '-'
    
                       
    def _loadcss(self, css_file) -> str:
        try:
            css = Path(css_file).read_text(encoding="UTF-8")
        except Exception as e:
            print(f'{css_file} nicht vorhanden. {str(e)}')
            css = ''
        return css
    
    def genEPUB(self, translation_obj: Translation, newfilename = None) -> None:
        if len(translation_obj.chunks) > 0:
            epubfilename = f'{self.source_epub_filename}_{translation_obj.modelname}.epub'
            if newfilename: epubfilename = newfilename
            log.printlog(f'Erzeuge ePub {epubfilename}')
            book = epub.EpubBook()
            book.set_identifier("123456")
            book.set_title(translation_obj.title)
            book.set_language(translation_obj.language)
            book.add_author(f'{translation_obj.author} ({translation_obj.modelname})')
            all_chapters = []
            chapter_name_last_used = translation_obj.chunks[0].source_chaptername
            chapter_title = self.source_epub_filename # workaround chunk0 hat keine titel
            #if not chapter_title: chapter_title = f'{chapter_name_last_used} - ID{translation_obj.chunks[0].chunk_id}'
            all_chapters.append(epub.EpubHtml(title=chapter_title, file_name=f'ID{translation_obj.chunks[0].chunk_id}.xhtml', lang="de"))
            chapter_text = ''
            chunk_item: Chunk
            for chunk_item in translation_obj.chunks:
                if chapter_name_last_used != chunk_item.source_chaptername: # neues Kapitel -> neues Kapitel beginnen
                    chapter_name_last_used = chunk_item.source_chaptername
                    chapter_title = None # chunk_item.metadata[0]['chaptertitle']
                    if not chapter_title: chapter_title = f'{chapter_name_last_used} - ID{translation_obj.chunks[0].chunk_id}'
                    all_chapters.append(epub.EpubHtml(title=f'{chapter_name_last_used} - ID{chunk_item.chunk_id}', file_name=f'ID{chunk_item.chunk_id}.xhtml', lang="de"))
                if all_chapters[-1].content:
                    chapter_text = str(all_chapters[-1].content)
                else: 
                    chapter_text = ''
                chapter_text += chunk_item.htmlp(self.jaccard_clean)
                all_chapters[-1].content = chapter_text
            
            for echapter in all_chapters:
                book.add_item(echapter)        
            
            booksource = epub.read_epub(config.PATH_INP + self.source_epub_filename)
            epubimages = list(booksource.get_items_of_type(ebooklib.ITEM_IMAGE)) + list(booksource.get_items_of_type(ebooklib.ITEM_COVER))
            for image in epubimages:
                image.file_name = 'images/' + os.path.basename(image.file_name) # Pfadnamen standardisieren
                book.add_item(image)
            
            book.toc = all_chapters # Inhaltsverzeichnis
            book.spine = ["nav"] + all_chapters # Spine (Lesereihenfolge festlegen)
            book.add_item(epub.EpubNcx()) # Standard-Navigationsdatei hinzufügen
            book.add_item(epub.EpubNav())

            try:
                epub.write_epub(config.PATH_OUT + epubfilename, book, {})
            except Exception as exc:
                log.error(f'Fehler beim Schreiben von {epubfilename}, {str(exc)}')
        else:
            log.error(f'genEPUB Fehler - Translation {translation_obj.modelname} hat keine chunks. ')
        log.saveFile()
        
    
def getbase64image(epubfilename, imagefilename) -> tuple[str | None, str | None]:
    imagefilename = imagefilename.replace('../','')
    try:
        book = epub.read_epub(config.PATH_INP + epubfilename)
        epubimages = list(book.get_items_of_type(ebooklib.ITEM_IMAGE)) + list(book.get_items_of_type(ebooklib.ITEM_COVER))
        for image in epubimages:
            if image.get_name() == imagefilename:
                image_data = image.content  # Binärdaten des Bildes
                image64data = base64.b64encode(image_data).decode("utf-8")  # Base64 umwandeln
                ext = image.file_name.split(".")[-1]
                mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"  # "jpg" → "jpeg" für HTML
                return mime_type, image64data
        # nicht gefunden? dann Suche ohne Pfad versuchen
        # log.print(f'nicht auf Anhieb in epub gefunden: "{imagefilename}"')
        imagefilename_wo_path = os.path.basename(imagefilename)
        for image in epubimages:
            if os.path.basename(image.file_name) == imagefilename_wo_path:
                image_data = image.content  # Binärdaten des Bildes
                image64data = base64.b64encode(image_data).decode("utf-8")  # Base64 umwandeln
                ext = image.file_name.split(".")[-1]
                mime_type = f"image/{'jpeg' if ext == 'jpg' else ext}"  # "jpg" → "jpeg" für HTML
                return mime_type, image64data
    except Exception as exc:
        log.error (f'Grafikdatei: {imagefilename} nicht in epub: {epubfilename} oder ePub konnte nicht gelesen werden, {str(exc)}')    
    log.error (f'Grafikdatei: {imagefilename} nicht in epub: {epubfilename}')
    return None, None

def htmlsafe(inputstr: str) -> str:
    outputstr = inputstr.replace("```", "'''")
    outputstr = outputstr.replace(' ',' ') # non breaking spaces ersetzen
    outputstr = html.escape(outputstr)
    return outputstr