from __future__ import annotations # pylint: disable=unused-variable
from typing import Any
import json

class promptset:
    def __init__(self, PromptID: int, system_message: str, prePrompt: str, postPrompt: str, infostr: str, 
                 allowLongAnswer = True, temperature = 0.2, top_p = 0.8, maxNewToken = 500, targetlanguage = 'DE', AIasJudge = False):
        self.PromptID = PromptID
        self.history = False
        self.system_message = system_message
        self.prePrompt = prePrompt
        self.postPrompt = postPrompt
        self.infostr = infostr
        self.allowLongAnswer = allowLongAnswer
        self.temperature = temperature
        self.top_p = top_p
        self.maxNewToken = maxNewToken
        self.targetlanguage = targetlanguage or 'DE'
        self.AIasJudge = AIasJudge
        
    def __getstate__(self) -> dict[str,Any]: # ermöglicht Laden von alten PKL (bei denen targetlanguage fehlte)
        return self.__dict__
    
    def __setstate__(self, state) -> None: # ermöglicht Laden von alten PKL (bei denen targetlanguage fehlte)
        # Alte Objekte haben neues_attr nicht
        if 'targetlanguage' not in state:
            state['targetlanguage'] = "DE"
        if 'AIasJudge' not in state:
            state['AIasJudge'] = "false"
        self.__dict__ = state    
        
    def info(self) -> str:
        info = f'ID{self.PromptID} system_message: "{self.system_message}" / prePrompt : "{self.prePrompt}" / ' + \
                f'postPrompt : "{self.postPrompt}" / info: "{self.infostr}" / allowLongAnswer {str(self.allowLongAnswer)} / ' + \
                f'maxNewToken {str(self.maxNewToken)} / Temp {self.temperature} / top_p {self.top_p} / {self.targetlanguage} / ' + \
                f'AIasJudge {str(self.AIasJudge)}'
        return info

    def to_dict(self) -> dict[str,Any]:
        """Konvertiert PromptSet zu Dictionary"""
        return {
            'PromptID': self.PromptID,
            'system_message': self.system_message,
            'prePrompt': self.prePrompt,
            'postPrompt': self.postPrompt,
            'infostr': self.infostr,
            'allowLongAnswer': self.allowLongAnswer,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'maxNewToken': self.maxNewToken,
            'targetlanguage': self.targetlanguage,
            'AIasJudge': self.AIasJudge
        }
    
    @classmethod
    def from_dict(cls, data):
        """Erstellt PromptSet aus Dictionary"""
        return cls(
            PromptID=data['PromptID'],
            system_message=data['system_message'],
            prePrompt=data['prePrompt'],
            postPrompt=data['postPrompt'],
            infostr=data['infostr'],
            allowLongAnswer=data.get('allowLongAnswer', True),
            temperature=data.get('temperature', 0.2),
            top_p=data.get('top_p', 0.8),
            maxNewToken=data.get('maxNewToken', 500),
            targetlanguage=data.get('targetlanguage', 'DE'),
            AIasJudge=data.get('AIasJudge', 'DE')
        )

def save_promptsets(promptsets: list[promptset], filename: str) -> None: # pylint: disable=unused-variable
    """Speichert PromptSets als JSON"""
    data = [ps.to_dict() for ps in promptsets]
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_promptsets(filename: str) -> list[promptset]: # pylint: disable=unused-variable
    """Lädt PromptSets aus JSON"""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return [promptset.from_dict(item) for item in data]

def get_promptsetByID (Promptsetlist: list[promptset], PromptID: int) -> promptset | None: # pylint: disable=unused-variable
    for pset in Promptsetlist:
        if pset.PromptID == PromptID: return pset
    return None