from __future__ import annotations # pylint: disable=unused-variable
from openai import OpenAI
from errorLog import log
from prompts import Promptset
import config

#from langchain_openai import ChatOpenAI
# from langchain_core.messages import HumanMessage, SystemMessage
# from langchain_core.prompts import PromptTemplate
# from langchain_core.prompts import ChatPromptTemplate
# from langchain_core.output_parsers import StrOutputParser
# from summary import getsummary
    
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
                    api_key=self.api_key
                )
        if config.cfg.llm_from_file:
            try:
                from llama_cpp import Llama
                model_path_str = "./" + self.model
                self.dllm = Llama(
                    model_path=model_path_str,
                    n_ctx=2048,          # Kontextlänge
                    n_gpu_layers=-1,     # Alle Layer auf der GPU (-1 = auto)
                    verbose=False
                )
            except Exception as e:
                log.error(f'Fehler beim laden von {model_path_str}, {str(e)}')
               
    def request(self, instructtext: str, activepromptset : Promptset | None, max_tokenoverride = 0) -> str | None:
        if self.simulate: return 'SIMOK'
        if activepromptset is None:
            log.error('Request activepromptset is None')
            return None
        requesttext = activepromptset.prePrompt + instructtext + activepromptset.postPrompt
        if config.cfg.llm_from_file: return self.directLLMfromFile(activepromptset.system_message, requesttext)        
        try:
            response = self.local_llm.chat.completions.create(
                model=self.model,
                messages=[
                            {"role": "system", "content": self.system_message},
                            {"role": "user", "content": instructtext}
                            ],
                stream=False,
                seed = self.seed,
                temperature = self.temperature,
                top_p = self.top_p, 
                max_tokens = max_tokenoverride if max_tokenoverride > 0 else self.max_tokens # allow override for heading
                )
            answer = response.choices[0].message.content
            return answer
        except Exception as e:
            log.error(f'Llmcaller requestOAi error {str(e)}')
            return None
        
    # def requestVialangchain(self, contentstr: str):
    #     print('langchain..')
       
    #     prompt = ChatPromptTemplate.from_messages([
    #         ("system", "{system}"),
    #         ("human", "{input}")
    #     ])
        
    #     chain2 = prompt | self.local_llm | StrOutputParser()
    #     self.history = chain2.invoke({'system': self.system_message,
    #                                   'input': contentstr })

    #     return self.history
    

    def directLLMfromFile(self, system_message: str, instructtext: str) -> str | None:
            try:
                promptstr = f"<|im_start|>system\n{system_message}<|im_end|>\n<|im_start|>user\n{instructtext}<|im_end|>\n<|im_start|>assistant\n"
                response = self.dllm.create_completion(
                    prompt = promptstr,
                    stream=False,
                    seed = self.seed,
                    temperature = self.temperature,
                    top_p = self.top_p,
                    max_tokens = self.max_tokens
                    )
                answer = response["choices"][0]["text"]
                return str(answer.strip())
            except Exception as e:
                log.error(f'Llmcaller directLLM error {str(e)}')
                return None

