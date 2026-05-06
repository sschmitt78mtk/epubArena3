from __future__ import annotations # pylint: disable=unused-variable
from openai import OpenAI, AsyncOpenAI
from errorLog import log
from prompts import Promptset
import config
    
class Llmcaller: # pylint: disable=unused-variable
    def __init__(self, model = config.cfg.current_open_api_modelname, api_base_url = config.cfg.current_openai_api_base,
                 api_key = config.cfg.current_openai_api_key, max_tokens = 500, simulate = False):
        self.max_tokens = max_tokens
        self.seed = 10
        self.mode = 'instruct'
        self.model = model
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.history3 = ''
        self.history2 = ''
        self.history = ['Bisher keine Zusammenfassung.']
        self.system_message = ''
        self.temperature = 0.2
        self.top_p = 0.8
        self.simulate = simulate
        self.local_llm = OpenAI(
                    base_url=self.api_base_url,
                    api_key=self.api_key,
                    timeout=config.cfg.api_timeout
                )
        self.async_llm = AsyncOpenAI(
                    base_url=self.api_base_url,
                    api_key=self.api_key,
                    timeout=config.cfg.api_timeout
                )
    
    async def request_async(self, instructtext: str, activepromptset: Promptset | None, max_tokenoverride=0) -> str | None:
        """Async version of request method for parallel processing"""
        if self.simulate:
            return 'SIMOK'
        if activepromptset is None:
            log.error('Request activepromptset is None')
            return None
        if instructtext == '' or instructtext == '\n':
            return instructtext # skip translation if empty
        
        requesttext = activepromptset.prePrompt + instructtext + activepromptset.postPrompt
        try:
            response = await self.async_llm.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": activepromptset.system_message},
                    {"role": "user", "content": requesttext}
                ],
                stream=False,
                seed=self.seed,
                temperature=activepromptset.temperature,
                top_p=activepromptset.top_p,
                #extra_body={"thinking": {"type": "disabled"}}, # enabled/disabled
                #extra_body={"enable_thinking": False},  # Reasoning-Mode deaktivieren
                #extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                max_tokens=max_tokenoverride if max_tokenoverride > 0 else activepromptset.maxNewToken
            )
            answer = response.choices[0].message.content
            return answer
        except Exception as e:
            log.error(f'Llmcaller request_async error {str(e)}')
            return None

