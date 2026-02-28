import re
import os
#import html
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
from markdownify import markdownify as md
#import store
from store import Chunk
from errorLog import log
import config

debugmode = True

class Extractor: # pylint: disable=unused-variable
    def __init__(self, source_epubFilename: str):
        self.source_epubFilename = source_epubFilename
        self.epubchapters = []
        self.epubimages = []
        self.chapterhtmlpkg :list[Chunk] = []
        self.finished = False
        self.author = ''
        self.title = ''
        self.language = ''
    
    def extract_chapters(self)  -> None:
        try:
            book = epub.read_epub(config.PATH_INP + self.source_epubFilename)
            self.epubimages = list(book.get_items_of_type(ebooklib.ITEM_IMAGE)) + list(book.get_items_of_type(ebooklib.ITEM_COVER))
            self.epubchapters = list(book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            self.title = book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unbekannter Titel'
            self.author = book.get_metadata('DC', 'creator')[0][0] if book.get_metadata('DC', 'creator') else 'Unbekannter Autor'
            self.language = book.get_metadata('DC', 'language')[0][0] if book.get_metadata('DC', 'language') else 'Unbekannte Sprache'
            log.printlog(f'extract_chapters {self.title} - {self.author} - {self.language}')
        except Exception as e:
            log.error(f'{self.source_epubFilename} konnte nicht gelesen werden. {str(e)}')
            return
        bookchapter_id = 0
        for echapter in self.epubchapters:
            bookchapter_id += 1 
            source_chaptername = echapter.get_name()
            chapterhtml = self._chapter2html(echapter)
            chaptertitle = self._chapter2title(echapter)
            self.chapterhtmlpkg.append(Chunk(source_chaptername, 0, 'raw', chapterhtml))
            self.chapterhtmlpkg[-1].chapter_id = bookchapter_id
            self.chapterhtmlpkg[-1].metadata.append({'chaptertitle': chaptertitle})
            if debugmode: log.printlog(source_chaptername)
        self.finished = True
    
    def _chapter2html(self, epubchapter) -> str:
        soup = BeautifulSoup(epubchapter.get_body_content(), 'html.parser')
        return str(soup)
    
    def _chapter2title(self, epubchapter) -> str:
        ''' Die ersten beiden h1 Titel als Überschrift verwenden'''
        soup = BeautifulSoup(epubchapter.get_body_content(), 'html.parser')
        headings = [h1.get_text(strip=True) for h1 in soup.find_all("h1", limit = 2)] #
        headings_str = " - ".join(headings) if headings else epubchapter.get_name()
        log.printlog(f'<h1>: {headings_str}')
        return str(headings_str)

class Cleaner: # pylint: disable=unused-variable
    def __init__(self, removeEmptyLine = False, replaceNewlineChar = False,  ):
        self.removeEmptyLine = removeEmptyLine
        self.replaceNewlineChar = replaceNewlineChar
    def clean(self,html_in: str) -> str:
        html_out = html_in
        if config.cfg.use_markdown:
            html_out = md(html_out)
        if self.removeEmptyLine:
            html_out = html_out.replace('\n\n','\n')
        return html_out
    def cleanchunks(self, chunks_in: list[Chunk]) -> list[Chunk]:
        return chunks_in
    
class Chunker: # pylint: disable=unused-variable
    def __init__(self, maxps: int, maxwords: int, minwords = 50):
        self.maxps = maxps
        self.maxwords = maxwords
        self.minwords = minwords # maxps werden ignoriert, wenn minwords nicht erreicht wurde.
        self.currentChunkID = 0

    def chunkit(self, inputchunks: list[Chunk]) -> list[Chunk]:
        debugmode = True
        outputchunks : list[Chunk] = []
        if len(inputchunks) > 0:
            if debugmode: log.printlog(str(inputchunks))
            chunktext = ''
            paracount = 0
            heading_pattern = re.compile(r"^h[1-6]$")
            last_source_chaptername = inputchunks[0].source_chaptername
            last_chapter_id = inputchunks[0].chapter_id
            chunkitem: Chunk # typehint     
            for chunkitem in inputchunks:
                if chunkitem.content != '':              
                    soup = BeautifulSoup(chunkitem.content, 'html.parser')
                    elements = [tag for tag in soup.find_all(True) if tag.name in ["p","img","table","tbody","pre","ul","li","span"] or heading_pattern.match(tag.name)]
                    for element in elements:
                        elementtext = element.get_text().replace('<br>',' ').strip()
                        if elementtext != '' or 'img' in element.name: # Leerzeilen überspringen
                            if 'img' in element.name:
                                if chunktext != '': # chunkitem beenden, bisher gesammelten Text packen
                                    outputchunks.append(Chunk(last_source_chaptername,self.currentChunkID,'text',chunktext,last_chapter_id))
                                    self.currentChunkID +=1
                                    chunktext = ''
                                    paracount = 0
                                imagefilename = 'images/' + os.path.basename(str(element.get('src'))) # Pfadnamen standardisieren
                                outputchunks.append(Chunk(chunkitem.source_chaptername, self.currentChunkID, "image", imagefilename,chunkitem.chapter_id))
                                self.currentChunkID +=1
                            elif element.name.startswith('h'): # blochunkitemck beenden, bisher gesammelten Text packen
                                #print('"' + element.name+'"' )
                                if chunktext != '':
                                    outputchunks.append(Chunk(last_source_chaptername,self.currentChunkID,'text',chunktext,last_chapter_id))
                                    self.currentChunkID +=1
                                    chunktext = ''
                                    paracount = 0
                                outputchunks.append(Chunk(chunkitem.source_chaptername,self.currentChunkID,'heading',elementtext,chunkitem.chapter_id))
                                outputchunks[-1].headinglevel = element.name
                                self.currentChunkID +=1
                            elif element.name == 'table' or element.name == 'pre':
                                if chunktext != '':
                                    outputchunks.append(Chunk(last_source_chaptername,self.currentChunkID,'text',chunktext,last_chapter_id))
                                    self.currentChunkID +=1
                                    chunktext = ''
                                    paracount = 0
                                # bei table den ursprünglichen Text verwenden, nicht den bereinigten.
                                outputchunks.append(Chunk(chunkitem.source_chaptername,self.currentChunkID,'table',element.prettify(),chunkitem.chapter_id))
                                outputchunks[-1].headinglevel = element.name
                                self.currentChunkID +=1
                            else: # alles standardmäßig als 'p' behandeln
                                if chunktext != '': chunktext += '\n'
                                if 'ul' in element.name or 'li' in element.name or 'span' in element.name:
                                    chunktext += ' ' + elementtext + '\n'
                                else:   
                                    chunktext += '\n' + elementtext
                                if 'p' in element.name: paracount +=1 # nur neue <p> zählen
                                wordcount = chunktext.count(' ') # Wörter (=Leerzeichen) zählen
                                if (paracount >= self.maxps and wordcount > self.minwords) or wordcount > self.maxwords:
                                    if wordcount > self.maxwords: 
                                        log.printlog(f'break wordcount: {str(wordcount)} (chunkID {self.currentChunkID})')
                                        paracount = 0 # Da der Text komplett einzeln verarbeitet wird, die ps auf 0 zurücksetzen
                                        maxmaxwords = 1.5*self.maxwords
                                        if wordcount > maxmaxwords:
                                            log.printlog(f'chunk {self.currentChunkID} weiter aufteilen.. (wordcount > 1.5*maxwords)')
                                            # wenn wordcount viel zu groß, letzten <p> zerlegen.
                                            chunks = splitpara(chunktext, self.maxwords)
                                            for chunk_text in chunks:
                                                outputchunks.append(Chunk(chunkitem.source_chaptername, self.currentChunkID, 'text', chunk_text, chunkitem.chapter_id))
                                                if debugmode: log.printlog(f'id: {chunkitem.chapter_id}, {chunkitem.source_chaptername}, {self.currentChunkID}, text, (wordcount: {chunk_text.count(" ")})')
                                                self.currentChunkID += 1
                                        else: # trotzdem speichern, wenn nur geringfügig mehr Wörter
                                            outputchunks.append(Chunk(chunkitem.source_chaptername,self.currentChunkID,'text',chunktext,chunkitem.chapter_id))
                                            if debugmode: log.printlog(f'chunk {self.currentChunkID} trotzdem gespeichert da wordcount < 1.5* maxwords)')
                                            self.currentChunkID +=1                                     
                                    if paracount >= self.maxps : 
                                        log.printlog('break maxps: ' + str(paracount))
                                        outputchunks.append(Chunk(chunkitem.source_chaptername,self.currentChunkID,'text',chunktext,chunkitem.chapter_id))
                                        self.currentChunkID +=1
                                    chunktext = ''
                                    paracount = 0
                        else:
                            if debugmode: log.printlog('empty elementtext in chunkitem')
                else:
                    if debugmode: log.printlog('empty chunkitem')
                last_source_chaptername = chunkitem.source_chaptername
                last_chapter_id = chunkitem.chapter_id
            if chunktext != '': # letztes <p> oder mehrere im Kapitel aufnehmen
                outputchunks.append(Chunk(last_source_chaptername,self.currentChunkID,'text',chunktext,last_chapter_id)) 
                self.currentChunkID +=1       
        for chunkitem in outputchunks:
            log.printlog(f'id: {chunkitem.chapter_id}, {chunkitem.source_chaptername}, {chunkitem.chunk_id}, {chunkitem.chunktype}, (wordcount: {chunkitem.content.count(" ")})')
        return outputchunks
        

def splitpara(fullchunktext: str, maxwords: int) -> list[str]:
    """
    Teilt einen Absatz in Chunks auf, deren Wortanzahl maxwords gerade überschreitet.
    
    Args:
        fullchunktext: Der komplette Absatz als String
        maxwords: Maximale Wortanzahl pro Chunk
    
    Returns:
        Liste von Chunks, die jeweils mehrere Sätze enthalten
    """
    # Sätze mit Regex erkennen
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', fullchunktext)
    
    chunks = []
    current_chunk = ""
    current_wordcount = 0
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        sentence_wordcount = sentence.count(' ') + 1  # Wörter zählen (Leerzeichen + 1)
        
        # Wenn der Satz alleine schon zu groß wäre, füge ihn einzeln hinzu
        if sentence_wordcount > maxwords:
            # Vorherigen Chunk speichern falls vorhanden
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""
                current_wordcount = 0
            
            chunks.append(sentence)
            continue
        
        # Prüfen ob der Satz zum aktuellen Chunk hinzugefügt werden kann
        if current_wordcount + sentence_wordcount <= maxwords:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            current_wordcount += sentence_wordcount
        else:
            # maxwords würde überschritten - aktuellen Chunk speichern
            if current_chunk:
                chunks.append(current_chunk)
            
            # Neuen Chunk mit aktuellem Satz starten
            current_chunk = sentence
            current_wordcount = sentence_wordcount
    
    # Restlichen Chunk speichern falls vorhanden
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks