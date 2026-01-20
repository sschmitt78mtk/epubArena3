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
from ErrorLog import log
from jaccard import jaccard_clean
import config
from prompts import promptset


if config.cfg.useMarkdown:
    import markdown
    
class chunk:
    def __init__(self, source_chaptername: str, chunkID: int, chunktype: str, content: str, chapterID = None):
        self.source_chaptername = source_chaptername
        self.chapterID = chapterID
        self.chunkID = chunkID
        self.content = content
        self.chunktype = chunktype # text, image, heading, table, raw 
        self.headinglevel = None
        self.imagedata = None
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
                if jaccardwin < 0.99: log.printlog(f"Jaccard_clean ({self.chunkID}): {jaccardwin:.2f}")
            #if content2 != self.content: print('jaccard:' + self.content)
            if config.cfg.useMarkdown: content2 = markdown.markdown(content2)
            htmlp = f'<p class="normal">{content2}</p>\n'
        return htmlp
    
    def __lt__(self, other):
         return self.chunkID < other.chunkID

class translation:
    def __init__(self, modelname: str):
        self.modelname = modelname
        self.promptset = promptset(0,'','','','New')
        self.chunks : list[chunk] = [] 
        self.numberOfChunks = 99999
        self.finished = False
        #self.chunkTypeNoTranslate = ['heading','table']
        #self.chunkTypeNoProcess = ['image','heading','table']
        self.chunkTypeNoTranslate = ['table']
        self.chunkTypeNoProcess = ['image','table']
        self.author = ''
        self.title = ''
        self.language = ''
    
    def chunkExists(self, chunkID: int) -> chunk | None:
        chunkAskedFor: chunk # typehint
        for chunkAskedFor in self.chunks:
            if chunkAskedFor.chunkID == chunkID: return chunkAskedFor
        return None
    
    def set_metadata(self, booktitle: str, bookauthor: str, booklanguage: str) -> None:
        self.title = booktitle
        self.author = bookauthor
        self.language = booklanguage
    
    def set_finished(self, finishstate = True) -> None:
        if finishstate:
            self.numberOfChunks = len(self.chunks)
            self.finished = True
        else:
            self.numberOfChunks = 9999
            self.finished = False
            
    def info(self) -> str:
        modelinfo = f'Modellname: {self.modelname}\n'
        promptinfo = f'{self.promptset.info()}\n'
        wordcountt = 0
        for chunkitem in self.chunks:
            wordcountt += chunkitem.content.count(' ')
        wordcount = f'wordcount: {str(wordcountt)}\n'
        return modelinfo + promptinfo + wordcount

                  
class mainstore:
    def __init__(self, source_epubFilename: str):
        self.source_epubFilename = source_epubFilename
        self.pklFilename = source_epubFilename + '.pkl'
        # self.author = ''
        # self.title = ''
        # self.language = ''
        self.source : translation = translation('Original')
        self.translations : list[translation] = []
        self.finished = False
   
    def save(self) -> None:
        try:
            with open(config.pathpkl + self.pklFilename, 'wb') as f:
                pickle.dump(self, f)
        except Exception as e:
            log.error(f'Fehler beim Schreiben von {self.pklFilename}, {str(e)}')
            
    # def _load(self):
    #     try:
    #         with open(self.pklFilename, 'rb') as f:
    #             self = pickle.load(f)
    #     except Exception as e:
    #         log.printlog(f'{self.pklFilename} konnte nicht geladen werden. {str(e)}')

    def getTranslationByModelName(self, modelname: str) -> translation:
        '''
        Wenn es noch keine Übersetzung mit dem Namen gibt, wird eine erstellt
        '''
        for t in self.translations:
            if t.modelname == modelname: 
                log.printlog(f'translation mit modelname {modelname} gefunden')
                return t
        newTranslation = translation(modelname)
        newTranslation.numberOfChunks = self.source.numberOfChunks
        self.translations.append(newTranslation)
        log.printlog(f'translation mit modelname {modelname} nicht gefunden, wird erstellt')
        return newTranslation
    
    def getmultipleTranslationsByModelNames(self, modelnames: str) -> list[translation]:
        '''
        mehrere modelnames (Semikolon als Trennzeichen) gibt eine Liste 
        '''
        translationNames = [item.strip() for item in modelnames.split(';')]
        translations: list[translation] = []
        for translationName in translationNames:        
            notfound = True
            for t in self.translations:
                if t.modelname == translationName: 
                    log.printlog(f'translation mit modelname {translationName} gefunden')
                    translations.append(t)
                    notfound = False                 
            if notfound:
                newTranslation = translation(translationName)
                newTranslation.numberOfChunks = self.source.numberOfChunks
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
   
def loadstore(source_epubFilename: str) -> mainstore: # pylint: disable=unused-variable
    pklFilename = config.pathpkl + source_epubFilename + '.pkl'
    try:
        with open(pklFilename, 'rb') as f:
            data = pickle.load(f)
        log.printlog(f'Daten aus PKL-Datei {pklFilename} geladen.')
        return data
    except Exception as e:
            log.printlog(f'{pklFilename} konnte nicht geladen werden. {str(e)}')
            return (mainstore(source_epubFilename)) # wenn es nicht geladen werden kann, einen neuen erstellen  
      
    
class publication: # pylint: disable=unused-variable
    def __init__(self, mainstoreproject: mainstore):
        self.mainstoreproject = mainstoreproject
        self.source_epubFilename = mainstoreproject.source_epubFilename
        self.html_filename = self.source_epubFilename + '.html'
        self.outputpath = ''
        self.jaccard_clean = False # True
    
    def genHTML(self, translationproject: translation, css_file = 'templates/default.css', preview = False, 
                linkToPictures = False, saveFile = True) -> str:
        css = self._loadcss(css_file)
        html_str =  f'<html><head><style>{css}</style>'
        html_str += '<meta http-equiv="content-type" content="text/html; charset=UTF-8">'
        if not translationproject.finished:
            html_str += '<meta http-equiv="refresh" content="30" >'
        html_str += f'<title>{self.source_epubFilename} - summary</title></head>\n<body>\n'
        for chunkitem in translationproject.chunks:
            log.print(f'genHTML: {chunkitem.chunkID}/{translationproject.numberOfChunks} {chunkitem.source_chaptername}')
            if chunkitem.chunktype == 'image':
                if linkToPictures: # epubPublishing
                    html_str += f'<figure class="mediaobject"><img src="{chunkitem.content.replace("../","")}" /></figure>'
                elif preview: 
                    html_str += f'<p>image {chunkitem.content}</p>\n'
                else:
                    mime, base64_string = getbase64image(self.source_epubFilename,chunkitem.content)
                    html_str += f'<img class= "figure" src="data:image/{mime};base64,{base64_string}" />\n'
            elif chunkitem.chunktype == 'heading':
                html_str += f'<{chunkitem.headinglevel}>{chunkitem.content}</{chunkitem.headinglevel}>'
            elif chunkitem.chunktype == 'table':
                html_str += f'<div class ="etable">{chunkitem.content}</div>'
            else:
                # TBD: self.jaccard_clean 
                html_str += f'<p>{chunkitem.content}<br><cs class="chunkid">{chunkitem.chunkID}</cs></p>'
        html_str += translationproject.promptset.info()
        html_str += '</body>\n</html>'
        if saveFile:
            try:
                with open(config.pathout + self.html_filename, "w", encoding="utf-8") as text_file:
                    text_file.write(html_str)
            except Exception as e:
                log.error(f'Fehler beim Schreiben von {self.html_filename}, {str(e)}')
        return html_str

    def genHTML_SideBySide(self, translationprojects: list[translation], css_file = 'templates/defaultsbs.css', preview = False,
                           start_at_chunkID = 0, stop_at_chunkID = None, Navstyle = 1) -> None:
        css = self._loadcss(css_file)
        numcolumns = len(translationprojects)
        html_str =  f'<html><head><style>{css}</style>'
        if Navstyle == 1:
            js = self._loadcss('templates/defaultsbs.js')
            html_str +=  f'<script>{js}'
            for i, k in enumerate(translationprojects):
                html_str += f"\nconst toggleCol{str(i+1)} = document.getElementById('toggleCol{str(i+1)}');"
                html_str += f"\ntoggleCol{str(i+1)}.addEventListener('change', function() " + '{toggleColumn(' + str(i) + ', this.checked);});'
            html_str += "const textcompare = document.getElementById('textcompare');"
            html_str += "\ntextcompare.addEventListener('change', function() {toggleColumn(99, this.checked);});"
            html_str += "\n});\n</script>\n"
        html_str += '<meta http-equiv="content-type" content="text/html; charset=UTF-8">'
        html_str += f'<title>{self.source_epubFilename} - summary</title></head>\n<body>\n'
        if Navstyle == 1:
            html_str += '<nav class="navbar"><div class="controls">'
            for i, translproject in enumerate(translationprojects): #  in range(len(translationprojects)):
                html_str += f'<label><input type="checkbox" id="toggleCol{str(i+1)}" checked>{translproject.modelname} ({str(i+1)})</label>'    
            html_str += '<label><input type="checkbox" id="textcompare">compare</label></div></nav>'
        html_str += '<div class="content">'
        html_str += '<table id="translationstable" width="100%" cellspacing="2" cellpadding="2" border="1"><tbody>\n' 
        for chunkitem in translationprojects[0].chunks:
            log.print(f'genHTMLsbs: {chunkitem.chunkID}/{translationprojects[0].numberOfChunks} {chunkitem.source_chaptername}')
            if chunkitem.chunkID < start_at_chunkID: continue
            if stop_at_chunkID and chunkitem.chunkID > stop_at_chunkID: break
            htmlsafecontent = htmlsafe(chunkitem.content) 
            if chunkitem.chunktype == 'image':
                if preview: 
                    html_str += f'<tr class="imagerow"><th colspan="{numcolumns}"><p>image {htmlsafecontent}</p></th></tr>\n'
                else:
                    mime, base64_string = getbase64image(self.source_epubFilename,chunkitem.content)
                    html_str += f'<tr class="imagerow"><th colspan="{numcolumns}"><img src="data:image/{mime};base64,{base64_string}" /></th></tr>\n'
            elif chunkitem.chunktype == 'heading':
                html_str += f'<tr class="headingrow"><th colspan="{numcolumns}"><{chunkitem.headinglevel}>{htmlsafecontent}</{chunkitem.headinglevel}></th></tr>\n'

            elif chunkitem.chunktype == 'table':
                html_str += f'<tr class="etable"><th colspan="{numcolumns}"><pre>{chunkitem.content}</pre></th></tr>\n'
            else:
                # spalte 1 source, spalte 2 translation
                html_str += f'<tr><td class="translation">{htmlsafecontent}<br><cs class="chunkid">{chunkitem.chunkID}</cs></td>'
                for tproject in translationprojects[1:]:# erstes überspringen 
                    content2 = htmlsafe(self._contentBychunkID(chunkitem.chunkID,tproject))
                    if self.jaccard_clean: 
                        jaccardwin, content2 = jaccard_clean(content2)
                        if jaccardwin < 0.99: log.printlog(f"Jaccard_clean ({chunkitem.chunkID}): {jaccardwin:.2f}")
                    if config.cfg.useMarkdown: content2 = markdown.markdown(content2)
                    # print(content2)
                    html_str += f'<td class="translation"><div>{content2}</div></td>'
                html_str += '</tr>\n'  
        
        html_str += '<td class="translation">' + translationprojects[0].info().replace("\n","<br>")+ '</td>'
        for tproject in translationprojects[1:]: # erstes überspringen
            html_str += '<td class="translation">' + tproject.info().replace("\n","<br>")+ '</td>'
        html_str += '</tr>\n'  
        html_str += '</tbody></table><br></div>\n</body>\n</html>'
        try:
            with open(config.pathout + self.html_filename, "w", encoding="utf-8") as text_file:
                    text_file.write(html_str)
        except Exception as e:
            log.error(f'Fehler beim Schreiben von {self.html_filename}, {str(e)}')
    
    def _contentBychunkID(self,chunkID : int, transl : translation) -> str:
        for chunkitem in transl.chunks:
            if chunkitem.chunkID == chunkID: return chunkitem.content
        return '-'
    
                       
    def _loadcss(self, css_file) -> str:
        try:
            css = Path(css_file).read_text(encoding="UTF-8")
        except Exception as e:
            print(f'{css_file} nicht vorhanden. {str(e)}')
            css = ''
        return css
    
    def genEPUB(self, transl: translation, newfilename = None) -> None:
        if len(transl.chunks) > 0:
            epubfilename = f'{self.source_epubFilename}_{transl.modelname}.epub'
            if newfilename: epubfilename = newfilename
            log.printlog(f'Erzeuge ePub {epubfilename}')
            book = epub.EpubBook()
            book.set_identifier("123456")
            book.set_title(transl.title)
            book.set_language(transl.language)
            book.add_author(f'{transl.author} ({transl.modelname})')
            allChapters = []
            ChapternameLastUsed = transl.chunks[0].source_chaptername
            chapterTitle = self.source_epubFilename # workaround chunk0 hat keine titel
            #if not chapterTitle: chapterTitle = f'{ChapternameLastUsed} - ID{transl.chunks[0].chunkID}'
            allChapters.append(epub.EpubHtml(title=chapterTitle, file_name=f'ID{transl.chunks[0].chunkID}.xhtml', lang="de"))
            chapterText = ''
            chunkitem: chunk
            for chunkitem in transl.chunks:
                if ChapternameLastUsed != chunkitem.source_chaptername: # neues Kapitel -> neues Kapitel beginnen
                    ChapternameLastUsed = chunkitem.source_chaptername
                    chapterTitle = None # chunkitem.metadata[0]['chaptertitle']
                    if not chapterTitle: chapterTitle = f'{ChapternameLastUsed} - ID{transl.chunks[0].chunkID}'
                    allChapters.append(epub.EpubHtml(title=f'{ChapternameLastUsed} - ID{chunkitem.chunkID}', file_name=f'ID{chunkitem.chunkID}.xhtml', lang="de"))
                if allChapters[-1].content:
                    chapterText = str(allChapters[-1].content)
                else: 
                    chapterText = ''
                chapterText += chunkitem.htmlp(self.jaccard_clean)
                allChapters[-1].content = chapterText
            
            for echapter in allChapters:
                book.add_item(echapter)        
            
            booksource = epub.read_epub(config.pathinp + self.source_epubFilename)
            epubimages = list(booksource.get_items_of_type(ebooklib.ITEM_IMAGE)) + list(booksource.get_items_of_type(ebooklib.ITEM_COVER))
            for image in epubimages:
                image.file_name = 'images/' + os.path.basename(image.file_name) # Pfadnamen standardisieren
                book.add_item(image)
            
            book.toc = allChapters # Inhaltsverzeichnis
            book.spine = ["nav"] + allChapters # Spine (Lesereihenfolge festlegen)
            book.add_item(epub.EpubNcx()) # Standard-Navigationsdatei hinzufügen
            book.add_item(epub.EpubNav())

            try:
                epub.write_epub(config.pathout + epubfilename, book, {})
            except Exception as e:
                log.error(f'Fehler beim Schreiben von {epubfilename}, {str(e)}')
        else:
            log.error(f'genEPUB Fehler - Translation {transl.modelname} hat keine chunks. ')
        log.saveFile()
        
    
def getbase64image(epubfilename, imagefilename) -> tuple[str | None, str | None]:
    imagefilename = imagefilename.replace('../','')
    try:
        book = epub.read_epub(config.pathinp + epubfilename)
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
    except Exception as e:
        log.error (f'Grafikdatei: {imagefilename} nicht in epub: {epubfilename} oder ePub konnte nicht gelesen werden, {str(e)}')    
    log.error (f'Grafikdatei: {imagefilename} nicht in epub: {epubfilename}')
    return None, None

def htmlsafe(inputstr: str) -> str:
    outputstr = inputstr.replace("```", "'''")
    outputstr = outputstr.replace(' ',' ') # non breaking spaces ersetzen
    outputstr = html.escape(outputstr)
    return outputstr