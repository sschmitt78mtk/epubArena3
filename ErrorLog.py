from datetime import datetime
from pathlib import Path
#import tkinter
#from tkinter import messagebox 

class Logfiles:
    def __init__(self):
        self.errorcount = 0
        self.LogFileName = ""
        self.ErrorLogFilename = ""
        self.Logfiletext = ""
        self.ErrorLogfiletext = ""
        self.Sessiontext = ""
        self.maxChars = 10000000 # ca 10MB

    def setFilename (self, LogFileName, ErrorLogFilename) -> None:
        self.LogFileName = LogFileName
        self.ErrorLogFilename = ErrorLogFilename
        self.Logfiletext = self.loadOldLogfile(LogFileName)
        self.Sessiontext += self.Logfiletext
        self.ErrorLogfiletext = self.loadOldLogfile(ErrorLogFilename) 

    def saveFile (self) -> None:
        self._shortenifneeded()
        self.Logfiletext = self.Logfiletext[-self.maxChars:] # Text ggf. kürzen, damit Log-Datei nicht zu groß wird
        if self.LogFileName:
            with open(self.LogFileName, "w", encoding="utf-8") as text_file:
                text_file.write(self.Logfiletext)
                print(self.LogFileName + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')
        self.ErrorLogfiletext = self.ErrorLogfiletext[-self.maxChars:] # Text ggf. kürzen       
        if self.ErrorLogFilename and (self.errorcount > 0):
            with open(self.ErrorLogFilename, "w", encoding="utf-8") as text_file:
                text_file.write(self.ErrorLogfiletext)
                print(self.ErrorLogFilename + ' gespeichert. (' + str(self.errorcount) + ' Fehler)')

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
        self.ErrorLogfiletext += (self.timestamp() + Logtext + "\n")
        self.Sessiontext +=  (self.timestamp() + Logtext + "\n")
        self.Logfiletext +=  (self.timestamp() + Logtext + "\n")

    def loadOldLogfile(self, filename: str) -> str:
        old_log = ''
        try:
            old_log = Path(filename).read_text(encoding="UTF-8")
        except Exception as e:
            print(f'{filename} nicht vorhanden, wird ggf. neu erstellt, {str(e)}')
        # with open(filename, 'r') as file:
        #     old_log = file.readlines()
        return old_log
    
    def clear(self) -> None:
        self.errorcount = 0
        self.LogFileName = ""
        self.ErrorLogFilename = ""
        self.Logfiletext = ""
        self.ErrorLogfiletext = ""
        self.Sessiontext = ""
        
    def _shortenifneeded(self) -> None:
        self.ErrorLogfiletext = self.ErrorLogfiletext[-self.maxChars:]
        self.Sessiontext = self.Sessiontext[-self.maxChars:]
        self.Logfiletext = self.Logfiletext[-self.maxChars:]
        


log = Logfiles() # pylint: disable=unused-variable

# def MsgBox(Message:str): 
#     rootWarning = tkinter.Tk()
#     rootWarning.withdraw() # Msgbox main window verstecken
#     messagebox.showwarning("Warnung", Message) 
#     rootWarning.destroy()