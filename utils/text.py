from curses import intrflush

import tiktoken
def get_tokenizer(model : str):
    try:
        encoding = tiktoken.encoding_for_model(model)
        return encoding.encode
    except Exception:
        encoding = tiktoken.get_encoding('cl100k_base')
        return encoding.encode
    
    
def count_tokens(text : str, model : str) -> int:
    
    tokenizer = get_tokenizer(model)
    if tokenizer:
        return len(tokenizer(text))
    
    return estimate_tokens(text)
    
    
def estimate_tokens(text):
    # as 4 character is 1 token
    return max(1,len(text)//4)