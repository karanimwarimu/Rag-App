from fastapi import APIRouter
from pydantic import BaseModel
import logging 
logging.basicConfig(level=logging.INFO)

from utilities.embedddocuments import  embedd_prompts
# from utilities.storeembeddedfiles import query_chroma
from utilities.formatfromchroma import prepare_context
from utilities.results_reranker import rerank_chunks
#from utilities.rag_textgenerator import text_Generator
from utilities.database.retrieve_DB import query_supabase

router = APIRouter()

class PromptRequest(BaseModel) :
    prompt : str 

@router.post('/send_prompt')

async def  generate_response(request_data : PromptRequest) :
 logging.info(f"Received prompt: {request_data.prompt}")
 user_prompt = request_data.prompt   
 #response_text = f"You sent : {user_prompt}" 
 #response = await loop.run_in_executor(None , text_generator , user_prompt)
 #role = "USER"
 #add_chat_history( role , user_prompt)
 embedded_prompt = await embedd_prompts(user_prompt)
 logging.info("prompt embedded")
 

 retrieved_chunks = await query_supabase(embedded_prompt)
 #chroma_result =  await query_chroma(embedded_prompt)
 
 if not retrieved_chunks:
    return {
        "answer": "I couldn't find relevant information in your documents.",
        "sources": []
    }
 
 logging.info(f"RESULTXXXXXXXXXX :::::::::::::::::::::::::::::::::::::: {retrieved_chunks}")

 response_text = await prepare_context(retrieved_chunks)
 #logging.info(f"final RESULT :::::::::::::::::: {response_text}")

 prepared_llm_context = await rerank_chunks(user_prompt , response_text)
 logging.info(f":::::::::::::FINAL FINALEEEE ::::::::{prepared_llm_context}")

 # Build a clean, human-readable context string from the reranked chunks.
 # LLM generation (text_Generator) is deferred to the local desktop build.
 if isinstance(prepared_llm_context, list):
     context_str = "\n\n".join((c["text"] if isinstance(c, dict) else str(c)) for c in prepared_llm_context)
 else:
     context_str = str(prepared_llm_context)

 final_response_text  =  context_str #await text_Generator(user_prompt, context_str)
 logging.info(f"ASSISTANT RESULT : {final_response_text}")
  
 return {"RESULT":  final_response_text}


