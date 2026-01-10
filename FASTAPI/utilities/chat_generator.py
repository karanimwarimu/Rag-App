from llama_cpp import Llama
from collections import deque
from datetime import datetime 
import json
import logging
import uuid


with open('configfile.json') as conf:
    configfile = json.load(conf)

llama_pipeline = Llama(
    model_path = configfile['modelpath'],
    n_ctx = configfile['n_ctx'],
    n_threads = configfile['n_threads'],
    n_gpu_layers = configfile['n_gpu_layers']
)

#memory storage in a deque list
chat_history = deque(maxlen=25)

#generate a conversation id
conversation_Id = str(uuid.uuid4())

def add_chat_history(role : str , content : str) :
    chat_history.append({
        "conversation ID" : conversation_Id ,
        "timestamp" : datetime.utcnow().isoformat(),
        "role" : role ,
        "content" :content
    })

def get_chat_history():
    return list(chat_history)[-7:]

def text_generator(prompt: str) -> str :
    try:
        add_chat_history("USER" , prompt)
        context_messages =get_chat_history()
        full_prompt = "\n".join(f"<{msg['role'].upper()}>: {msg['content']}"  for msg in context_messages)
        final_prompt = f"[INST] {full_prompt} [/INST]"

        generate_text = llama_pipeline(prompt = final_prompt , **configfile['model_configuration'])
      
        bot_reply = generate_text['choices'][0]['text'].strip()
        add_chat_history("BOT" , bot_reply)
        return bot_reply
       
    except Exception as e :
        logging.error(f"Error in text_generator: {e}")
        return "Sorry, an error occurred while generating text."
