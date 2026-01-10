import logging
logging.basicConfig(level=logging.INFO)
from llama_cpp import Llama
import json 


with open('configfile.json') as conf:
    configfile = json.load(conf)

llama_pipeline = Llama(
    model_path = configfile['modelpath'],
    n_ctx = configfile['n_ctx'],
    n_threads = configfile['n_threads'],
    n_gpu_layers = configfile['n_gpu_layers']
)

async def text_Generator(prompt : str , retrieved_context : str = "" ) -> str:
    try:
        if retrieved_context:
          full_promp = f"[INST] AS  a powerful and intelligent virtual assistant  Use the following context to answer:\n\n{retrieved_context}\n\nQuestion: {prompt} [/INST]"
          full_prompt = f"""[INST] Use the following context to answer the question concisely:
                                        {retrieved_context}
                  User: {prompt}
                  [/INST] """
        else :
         full_prompt = f"[INST] AS  a powerful and intelligent virtual assistant  answer the following question : \n\n {prompt} [/INST]"

        generated_text = llama_pipeline(prompt = full_prompt , **configfile['model_configuration'])
        return generated_text["choices"][0]["text"].strip()
    except Exception as e:
        logging.error(f"Error in text_generator: {e}")
        return "Sorry, an error occurred while generating text."
    


    