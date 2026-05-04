from datetime import datetime
from pathlib import Path
#import tkinter
#from tkinter import messagebox 

class Logfiles:
    def __init__(self):
        self.errorcount = 0
        self.LogFileName = ""
        self.errorLogFilename = ""
        self.Logfiletext = ""
        self.errorLogfiletext = ""
        self.Sessiontext = ""
        self.maxChars = 10000000 # ca 10MB

    def setFilename (self, LogFileName, errorLogFilename) -> None:
        self.LogFileName = LogFileName
        self.errorLogFilename = errorLogFilename
        self.Logfiletext = self.loadOldLogfile(LogFileName)
        self.Sessiontext += self.Logfiletext
        self.errorLogfiletext = self.loadOldLogfile(errorLogFilename) 

    def _ensure_max_chars(self, text: str) -> str:
        """Truncate text to maxChars to keep memory bounded."""
        return text[-self.maxChars:]

    def saveFile(self) -> None:
        if self.LogFileName:
            with open(self.LogFileName, "w", encoding="utf-8") as text_file:
                text_file.write(self.Logfiletext)
                print(self.LogFileName + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')
        if self.errorLogFilename and (self.errorcount > 0):
            with open(self.errorLogFilename, "w", encoding="utf-8") as text_file:
                text_file.write(self.errorLogfiletext)
                print(self.errorLogFilename + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')

    def timestamp(self) -> str:
        timestamptext = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " | "
        return timestamptext
    
    def print(self, Logtext) -> None:  # nur ausgeben
        self.Sessiontext = self._ensure_max_chars(self.Sessiontext + Logtext + "\n")
        print(Logtext)
    
    def log(self, Logtext) -> None:  # nur loggen
        entry = self.timestamp() + Logtext + "\n"
        self.Sessiontext = self._ensure_max_chars(self.Sessiontext + entry)
        self.Logfiletext = self._ensure_max_chars(self.Logfiletext + entry)

    def printlog(self, Logtext) -> None:  # ausgeben und loggen
        print(Logtext)
        entry = self.timestamp() + Logtext + "\n"
        self.Sessiontext = self._ensure_max_chars(self.Sessiontext + entry)
        self.Logfiletext = self._ensure_max_chars(self.Logfiletext + entry)
    
    def warning(self, Logtext) -> None:  # ausgeben und loggen
        Logtext = 'WARNUNG: ' + Logtext
        print(Logtext)
        entry = self.timestamp() + Logtext + "\n"
        self.Sessiontext = self._ensure_max_chars(self.Sessiontext + entry)
        self.Logfiletext = self._ensure_max_chars(self.Logfiletext + entry)
    
    def error(self, Logtext) -> None:  # ausgeben, loggen, in zusätzlicher Error-Datei speichern
        Logtext = 'FEHLER: ' + Logtext
        print(Logtext)
        self.errorcount += 1
        entry = self.timestamp() + Logtext + "\n"
        self.errorLogfiletext = self._ensure_max_chars(self.errorLogfiletext + entry)
        self.Sessiontext = self._ensure_max_chars(self.Sessiontext + entry)
        self.Logfiletext = self._ensure_max_chars(self.Logfiletext + entry)

    def loadOldLogfile(self, filename: str) -> str:
        old_log = ''
        try:
            old_log = Path(filename).read_text(encoding="UTF-8")
        except Exception as e:
            print(f'{filename} nicht vorhanden, wird ggf. neu erstellt, {str(e)}')
        return old_log
    
    def clear(self) -> None:
        self.errorcount = 0
        self.LogFileName = ""
        self.errorLogFilename = ""
        self.Logfiletext = ""
        self.errorLogfiletext = ""
        self.Sessiontext = ""
        


log = Logfiles() # pylint: disable=unused-variable

# def MsgBox(Message:str): 
#     rootWarning = tkinter.Tk()
#     rootWarning.withdraw() # Msgbox main window verstecken
#     messagebox.showwarning("Warnung", Message) 
#     rootWarning.destroy()