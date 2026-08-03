"""LLM API caller module for making requests to various LLM providers.

This module provides the Llmcaller class which handles API calls to OpenAI-compatible
LLM providers including OpenAI, DeepSeek, and local models (LM Studio, llama.cpp).
"""

from __future__ import annotations  # pylint: disable=unused-variable

from openai import AsyncOpenAI, OpenAI

import config
from errorLog import log
from prompts import Promptset


class Llmcaller:  # pylint: disable=unused-variable
    """Handles API calls to LLM providers with support for multiple backends.
    
    Supports OpenAI, DeepSeek, and local LLM providers with automatic
    provider-specific configuration handling.
    """

    # Class constants for default values
    DEFAULT_SEED = 10
    DEFAULT_MAX_TOKENS = 500
    DEFAULT_TEMPERATURE = 0.2
    DEFAULT_TOP_P = 0.8

    def __init__(
        self,
        model: str = config.cfg.current_open_api_modelname,
        api_base_url: str = config.cfg.current_openai_api_base,
        api_key: str = config.cfg.current_openai_api_key,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        simulate: bool = False,
    ) -> None:
        """Initialize the LLM caller with API configuration.
        
        Args:
            model: The model name to use for API calls.
            api_base_url: The base URL for the API endpoint.
            api_key: The API key for authentication.
            max_tokens: Maximum tokens for the response.
            simulate: If True, return 'SIMOK' instead of making actual API calls.
        """
        self.max_tokens = max_tokens
        self.seed = self.DEFAULT_SEED
        self.model = model
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.temperature = self.DEFAULT_TEMPERATURE
        self.top_p = self.DEFAULT_TOP_P
        self.simulate = simulate

        self.sync_client = OpenAI(
            base_url=self.api_base_url,
            api_key=self.api_key,
            timeout=config.cfg.api_timeout,
        )
        self.async_client = AsyncOpenAI(
            base_url=self.api_base_url,
            api_key=self.api_key,
            timeout=config.cfg.api_timeout,
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

    async def request_async(
        self,
        instruct_text: str,
        activepromptset: Promptset | None,
        max_token_override: int = 0,
    ) -> str | None:
        """Make an async API request to the LLM provider.
        
        Args:
            instruct_text: The input text to process.
            activepromptset: The prompt set containing system message and pre/post prompts.
            max_token_override: Override the max tokens setting if > 0.
            
        Returns:
            The LLM response content, or None if an error occurred.
        """
        if self.simulate:
            return 'SIMOK'
        if activepromptset is None:
            log.error('Request activepromptset is None')
            return None
        if instruct_text == '' or instruct_text == '\n':
            return instruct_text  # skip translation if empty

        request_text = activepromptset.prePrompt + instruct_text + activepromptset.postPrompt
        try:
            kwargs = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": activepromptset.system_message},
                    {"role": "user", "content": request_text}
                ],
                "stream": False,
                "seed": self.seed,
                "temperature": activepromptset.temperature,
                "top_p": activepromptset.top_p,
                self._get_max_tokens_param_name(): (
                    max_token_override if max_token_override > 0 else activepromptset.maxNewToken
                ),
            }
            extra = self._get_disable_thinking_extra_body()
            if extra is not None:
                kwargs["extra_body"] = extra

            response = await self.async_client.chat.completions.create(**kwargs)
            answer = response.choices[0].message.content
            if not answer:
                log.error('got Response, but Content was empty!')
                return None
            return answer
        except Exception as e:
            log.error(f'Llmcaller request_async error {str(e)}')
            return None

