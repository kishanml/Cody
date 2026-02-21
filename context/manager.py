from typing import Any

from prompts.system import get_system_prompt
from dataclasses import dataclass

from utils.text import count_tokens
@dataclass
class MessageItem:
    role : str
    content : str
    token_count : int | None = None
    
    
    def to_dict(self) -> dict[str,Any]:
        result  = {"role":self.role}
        
        if self.content:
            result['content'] = self.content
        return result

class ContextManager:
    def __init__(self) -> None:
        
        # tells ai how to behave
        self.system_prompt = get_system_prompt()
        self.model_name = "arcee-ai/trinity-large-preview:free"
        self._messages : list[MessageItem] = []
        
    def add_user_(self,content : str ) -> None:
        
        item = MessageItem(role='user',
                           content = content,
                           token_count =count_tokens(content,self.model_name))
        self._messages.append(item)
        
    
    def add_assistant_messages(self,content : str ) -> None:
        
        item = MessageItem(role='assitant',
                           content = content or "",
                           token_count =count_tokens(content,self.model_name))
        self._messages.append(item)
        
    
    def get_messages(self):
        messages = []
        
        if self.system_prompt:
            messages.append({"role":"system","content": self.system_prompt})
        for item in self._messages:
            messages.append(item.to_dict())
            
        return messages
        