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

    def saveFile (self) -> None:
        self._shortenifneeded()
        self.Logfiletext = self.Logfiletext[-self.maxChars:] # Text ggf. kürzen, damit Log-Datei nicht zu groß wird
        if self.LogFileName:
            with open(self.LogFileName, "w", encoding="utf-8") as text_file:
                text_file.write(self.Logfiletext)
                print(self.LogFileName + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')
        self.errorLogfiletext = self.errorLogfiletext[-self.maxChars:] # Text ggf. kürzen       
        if self.errorLogFilename and (self.errorcount > 0):
            with open(self.errorLogFilename, "w", encoding="utf-8") as text_file:
                text_file.write(self.errorLogfiletext)
                print(self.errorLogFilename + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')

    def timestamp(self) -> str:
        timestamptext = datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " | "
        return timestamptext
    
    def print(self,Logtext) -> None: # nur ausgeben
        self.Sessiontext += Logtext + "\n"
        print(Logtext)
    
    def log(self,Logtext) -> None: # nur loggen
        self.Sessiontext += (self.timestamp() + Logtext + "\n") 
        self.Logfiletext += (self.timestamp() + Logtext + "\n") 

    def printlog(self,Logtext) -> None: # ausgeben und loggen
        print(Logtext)
        self.Sessiontext += (self.timestamp() + Logtext + "\n")
        self.Logfiletext += (self.timestamp() + Logtext + "\n")
    
    def warning(self,Logtext) -> None: # ausgeben und loggen
        Logtext = 'WARNUNG: ' + Logtext
        print(Logtext)
        self.Sessiontext += (self.timestamp() + Logtext + "\n")
        self.Logfiletext += (self.timestamp() + Logtext + "\n")
    
    def error(self,Logtext) -> None: # ausgeben, logggen, in zusätzlicher Error-Datei speichern
        Logtext = 'FEHLER: ' + Logtext
        print(Logtext)
        self.errorcount += 1
        self.errorLogfiletext += (self.timestamp() + Logtext + "\n")
        self.Sessiontext +=  (self.timestamp() + Logtext + "\n")
        self.Logfiletext +=  (self.timestamp() + Logtext + "\n")

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
        
    def _shortenifneeded(self) -> None:
        self.errorLogfiletext = self.errorLogfiletext[-self.maxChars:]
        self.Sessiontext = self.Sessiontext[-self.maxChars:]
        self.Logfiletext = self.Logfiletext[-self.maxChars:]
        


log = Logfiles() # pylint: disable=unused-variable

# def MsgBox(Message:str): 
#     rootWarning = tkinter.Tk()
#     rootWarning.withdraw() # Msgbox main window verstecken
#     messagebox.showwarning("Warnung", Message) 
#     rootWarning.destroy()