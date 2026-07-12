from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import logging
logging.basicConfig(level=logging.INFO)

from utilities.embedddocuments import  embedd_prompts
from utilities.formatfromchroma import prepare_context
from utilities.results_reranker import rerank_chunks
from utilities.database.retrieve_DB import query_supabase
from utilities.llm.llm_manager import generate_answer, generate_answer_stream

router = APIRouter()

class PromptRequest(BaseModel) :
    prompt : str
    stream : bool = False
    user_id : str | None = None
    job_id : str | None = None

@router.post('/api/v1/chat')

async def  generate_response(request_data : PromptRequest) :
  logging.info(f"Received prompt: {request_data.prompt}")
  user_prompt = request_data.prompt

  embedded_prompt = await embedd_prompts(user_prompt)
  logging.info("prompt embedded")

  retrieved_chunks = await query_supabase(embedded_prompt)

  if not retrieved_chunks:
     return {
         "answer": "I couldn't find relevant information in your documents.",
         "sources": []
     }

  logging.info(f"RESULTXXXXXXXXXX :::::::::::::::::::::::::::::::::::::: {retrieved_chunks}")

  response_text = await prepare_context(retrieved_chunks)

  prepared_llm_context = await rerank_chunks(user_prompt , response_text)
  logging.info(f":::::::::::::FINAL FINALEEEE ::::::::{prepared_llm_context}")

  if isinstance(prepared_llm_context, list):
      context_str = "\n\n".join((c["text"] if isinstance(c, dict) else str(c)) for c in prepared_llm_context)
  else:
      context_str = str(prepared_llm_context)

  # Streaming path (Server-Sent Events). Each frame is JSON {"token": "..."},
  # matching the frontend chat.js SSE reader. Falls back to a single JSON
  # {RESULT} response when stream is False.
  if request_data.stream:
      async def event_stream():
          try:
              async for token in generate_answer_stream(user_prompt, context_str):
                  yield f"data: {json.dumps({'token': token})}\n\n"
          except Exception as e:
              logging.error(f"Stream error: {e}")
              yield f"data: {json.dumps({'token': '[error] ' + str(e)})}\n\n"
          yield "data: [DONE]\n\n"
      return StreamingResponse(event_stream(), media_type="text/event-stream")

  final_response_text = await generate_answer(prompt=user_prompt, context=context_str)
  logging.info(f"ASSISTANT RESULT : {final_response_text}")

  return {"RESULT":  final_response_text}
