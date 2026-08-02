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
    
    def _get_disable_thinking_extra_body(self) -> dict | None:
        """Return provider-specific extra_body to disable thinking mode, or None if not needed."""
        url_lower = self.api_base_url.lower()
        if "deepseek" in url_lower:
            return {"thinking": {"type": "disabled"}}
        if any(local in url_lower for local in ("127.0.0.1", "localhost", "host.docker.internal")):
            return {
                "enable_thinking": False,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        return None  # OpenAI and others: send nothing (unknown params cause 400 errors)

    def _get_max_tokens_param_name(self) -> str:
        """Return the correct max-tokens parameter name for the provider.
        OpenAI gpt-5.x and DeepSeek require 'max_completion_tokens'.
        Local LM Studio / llama.cpp use 'max_tokens'."""
        url_lower = self.api_base_url.lower()
        if "api.openai.com" in url_lower or "deepseek" in url_lower:
            return "max_completion_tokens"
        return "max_tokens"

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
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": activepromptset.system_message},
                    {"role": "user", "content": requesttext}
                ],
                "stream": False,
                "seed": self.seed,
                "temperature": activepromptset.temperature,
                "top_p": activepromptset.top_p,
                self._get_max_tokens_param_name(): max_tokenoverride if max_tokenoverride > 0 else activepromptset.maxNewToken,
            }
            extra = self._get_disable_thinking_extra_body()
            if extra is not None:
                kwargs["extra_body"] = extra

            response = await self.async_llm.chat.completions.create(**kwargs)
            answer = response.choices[0].message.content
            if not answer:
                log.error('got Response, but Content was empty!')
                return None
            return answer
        except Exception as e:
            log.error(f'Llmcaller request_async error {str(e)}')
            return None

