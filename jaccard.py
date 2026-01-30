
# from functools import lru_cache # für caching
import re
import spacy
from ErrorLog import log

# entfernt doppelt vorkommende Sätze 

def jaccard_clean_simple(texttoclean: str) -> str: # pylint: disable=unused-variable
        
    # 1. Sätze extrahieren (bis zum Punkt)
    sentences = re.findall(r'[^.!?]+[.!?]', texttoclean)

    # 2. Funktion für Jaccard-Ähnlichkeit zwischen zwei Sätzen (wortbasiert)
    def jaccard_similarity(sent1, sent2):
        set1 = set(re.findall(r'\w+', sent1.lower()))
        set2 = set(re.findall(r'\w+', sent2.lower()))
        if not set1 and not set2:
            return 1.0
        return len(set1 & set2) / len(set1 | set2)

    # 3. Doppelte oder sehr ähnliche Sätze entfernen
    threshold = 0.8
    unique_sentences : list[str]= []

    for s in sentences:
        if not any(jaccard_similarity(s, u) >= threshold for u in unique_sentences):
            unique_sentences.append(s)

    # 4. Ergebnis
    result = " ".join(unique_sentences)
    return result
    #print(result)


# Globales Modell-Caching
_SPACY_MODEL = None
spacy_model_lang = ''

def get_spacy_model(language: str):
    global _SPACY_MODEL
    global spacy_model_lang
    if 'de' in language.lower(): language = 'DE'
    if _SPACY_MODEL is None or spacy_model_lang != language: # Modell laden wenn noch gecached, oder Sprache gewechselt
        if language == 'DE':
            try:
                _SPACY_MODEL = spacy.load("de_core_news_sm")
                spacy_model_lang = 'DE'
            except Exception as e:
                log.error(f"Spacy-Modell nicht gefunden. Installiere: python -m spacy download de_core_news_sm, {str(e)}")
        else:
            try:
                _SPACY_MODEL = spacy.load("en_core_web_sm")
                spacy_model_lang = 'EN'
            except Exception as e:
                log.error(f"Spacy-Modell nicht gefunden. Installiere: python -m spacy download en_core_web_sm, {str(e)}")
    return _SPACY_MODEL


def jaccard_clean(texttoclean: str, language = 'DE', threshold: float = 0.7) -> tuple[float, str]: # pylint: disable=unused-variable
    """
    Optimierte Version für maximale Geschwindigkeit
    """
    nlp = get_spacy_model(language)
    # sentencizer = nlp.add_pipe("sentencizer", before="parser")
    
    # interne Version für Satzsegmentierung erzeugen (Original bleibt unverändert)
    segmented_for_spacy = re.sub(r'\n+', '. ', texttoclean)

    doc = nlp(segmented_for_spacy)

    # Dokument verarbeiten
    # doc = nlp(texttoclean) # Erkennung von Sätzen ohne Satzzeichen funktioniert hiermit nicht.
    
    # Sätze extrahieren und direkt filtern
    sentences = []
    for sent in doc.sents:
        text = sent.text.strip()
        if len(text) > 3:  # Kurze "Sätze" ignorieren
            sentences.append(text)
    
    if len(sentences) <= 1:
        return 1.0 , texttoclean
    
    # Vorberechnete Wort-Sets für bessere Performance
    sentence_sets = []
    for sentence in sentences:
        words = set(re.findall(r'\w+', sentence.lower()))
        sentence_sets.append(words)
    
    # Doppelte entfernen mit vorberechneten Sets
    unique_indices = []
    for i, current_set in enumerate(sentence_sets):
        is_duplicate = False
        for j in unique_indices:
            kept_set = sentence_sets[j]
            if not current_set and not kept_set:
                similarity = 1.0
            else:
                intersection = len(current_set & kept_set)
                union = len(current_set | kept_set)
                similarity = intersection / union if union > 0 else 0.0
            
            if similarity >= threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_indices.append(i)
    
    # Ergebnis zusammensetzen
    unique_sentences = [sentences[i] for i in unique_indices]
    textcleaned = " ".join(unique_sentences)
    jaccardwin = len(textcleaned)/(len(texttoclean))
    #if jaccardwin < 0.99: log.printlog(f"Jaccard_clean: {jaccardwin:.2f}")
    return jaccardwin, textcleaned


# test = """
# Kapitel 11. Eine der größten offenen Fragen in der Welt der LLMs ist heute, wie man sie am besten in die Hände von Endnutzern legen kann. In gewisser Weise sind LLMs tatsächlich eine intuitivere Schnittstelle für das Rechnen als das, was davor kam. Sie sind viel nachsichtiger gegenüber Tippfehlern, Zungenfehlern und der allgemeinen Ungenauigkeit von Menschen, verglichen mit traditionellen Computeranwendungen. Andererseits kommt die Fähigkeit, Eingaben zu verarbeiten, die "etwas daneben" sind, mit einer Tendenz einher, manchmal Ergebnisse zu produzieren, die auch "etwas daneben" sind – was auch sehr wenig mit den bisherigen Computertendenzen zu tun hat. Tatsächlich wurden Computer so entworfen, dass sie zuverlässig dieselbe Reihe von Anweisungen mit denselben Ergebnissen jedes Mal wiederholen. Dieser Grundsatz der Zuverlässigkeit hat sich in den letzten Jahrzehnten auf die Gestaltung von Benutzeroberflächen für Mensch-Computer-Interaktionen (die je nach Kontext HCI, UX oder UI genannt werden) ausgebreitet, sodass viele der üblichen Konstrukte für Anwendungen, die stark auf LLMs angewiesen sind, suboptimal sind. Nehmen wir ein Beispiel: Figma ist eine Softwareanwendung, die von Designern verwendet wird, um treue Darstellungen von Designs für Websites, mobile Anwendungen, Buch- oder Magazincover zu erstellen – die Liste geht weiter. Wie bei fast allen Produktivitätssoftware (Software zur Erstellung irgendeiner Art von Langforminhalt) ist ihre Benutzeroberfläche eine Kombination aus folgendem:
# Einem Farbton von Werkzeugen und vorgefertigten Grundelementen (fundamentalen Bausteinen), in diesem Fall Linien, Formen, Auswahl- und Malwerkzeugen und vielem mehr
# Einem Farbton von Werkzeugen und vorgefertigten Grundelementen (fundamentalen Bausteinen), in diesem Fall Linien, Formen, Auswahl- und Malwerkzeugen und vielem mehr
# (fundamentalen Bausteinen), in diesem Fall Linien, Formen, Auswahl- und Malwerkzeugen und vielem mehr
# Einem Farbton von Werkzeugen und vorgefertigten Grundelementen (fundamentalen Bausteinen), in diesem Fall Linien, Formen, Auswahl- und Malwerkzeugen und vielem mehr
# Einem Farbton von Werkzeugen und vorgefertigten
# """

#print("\033[H\033[3J", end="")
#print(jaccard_clean(test))