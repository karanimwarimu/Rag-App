import logging 
logging.basicConfig(level=logging.INFO)
from fastapi import FastAPI ,Request , UploadFile , File , BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
#from text_generator import text_generator
#from chat_generator import add_chat_history , text_generator
from utilities.validateFile import Validate_uploaded_file

from utilities.extractmetada import extract_metadata
from documentloader import load_files
from chunkdocuments import chunk_loaded_documents
from utilities.embedddocuments import embedd_documents , embedd_prompts
from utilities.storeembeddedfiles import store_embedded_files , check_stored_embeddedchunks ,query_chroma
from utilities.formatfromchroma import prepare_context
from utilities.results_reranker import rerank_chunks
#from rag_textgenerator import text_Generator
import json
from datetime import datetime 

app = FastAPI()

# --- CORS settings ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing; replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


with open ('configfile.json') as conf :
    configfile = json.load(conf)

#get folders from  cofig files
Template_DIR = configfile["TemplatesFolder"]
StaticFiles_DIR = configfile["StaticFolder"]

#load files
templates = Jinja2Templates(directory= Template_DIR) 
app.mount("/static", StaticFiles(directory= StaticFiles_DIR) , name="static")

#::::::::::::::::::: LOAD WEB PAGES :::::::::::::::::::::::::
 
@app.get('/chatbot' , response_class=HTMLResponse)
async def load_RagChat(request : Request ):
    return templates.TemplateResponse("RagChatApp.html" , {"request" : request})
       
@app.get('/fileuploader' , response_class=HTMLResponse)
async def load_file_Uploader(request:Request):
   return templates.TemplateResponse("FileUploader.html" , {"request" : request})

#:::::::::: HANDLE THE USER INPUT :::::::::::::::::::::::     

class PromptRequest(BaseModel) :
    prompt : str 

@app.post('/send_prompt')
async def  generate_response(request_data : PromptRequest) :
 logging.info(f"Received prompt: {request_data.prompt}")
 user_prompt = request_data.prompt   
 #response_text = f"You sent : {user_prompt}" 
 #response = await loop.run_in_executor(None , text_generator , user_prompt)
 #role = "USER"
 #add_chat_history( role , user_prompt)
 embedded_prompt = await embedd_prompts(user_prompt)
 logging.info("prompt embedded")
 

 chroma_result = await query_chroma(embedded_prompt)
 #logging.info(f"RESULTXXXXXXXXXX :::::::::::::::::::::::::::::::::::::: {chroma_result}")

 response_text = await prepare_context(chroma_result)
 #logging.info(f"final RESULT :::::::::::::::::: {response_text}")

 prepared_llm_context = await rerank_chunks(user_prompt , response_text)
 logging.info(f":::::::::::::FINAL FINALEEEE ::::::::{prepared_llm_context}")

 final_response_text  = prepared_llm_context # await text_Generator(user_prompt , prepared_llm_context)
 logging.info(f"ASSISTANT RESULT : {final_response_text}")
  
 return {"RESULT":  final_response_text}
 

#::::::::::::::::: handle the file upload :::::::::::: 
   

async def uploaded_file_processing(loaded_document  , filename ):
    try:
    
        chunked_docs = await  chunk_loaded_documents(loaded_document)
        #print(f":::::::::::::::: chUNKED DOCS  {chunked_docs}" )
        logging.info(f"chunked {filename} successfully")

        embedded_chunks  = await embedd_documents(chunked_docs)
        #print(embedded_chunks)
        logging.info(f"Embedded  {filename} successfully")

        await store_embedded_files(embedded_chunks)
        strit = check_stored_embeddedchunks()
        #print(f"::::::::::::::::: embedded {strit}")
        logging.info(f"stored  {filename}  to chroma successfully")
    except Exception as e :
        print("ERROR :" , e)
        logging.error(f"Couldn't process the file : {filename}")


@app.post('/File_Upload')
async def handle_uploaded_files(background_tasks : BackgroundTasks ,file : UploadFile = File(...)) :
      logging.info(f"Received file: {file.filename}")
      file_upload_time = datetime.utcnow().isoformat()
      Validate_uploaded_file(file)
      logging.info(f"{file} meets standards!")
      #file_content = await file.read()

      #extract metadata
      file_metadata = await extract_metadata(file , file_upload_time)
      #load documents
      loaded_document = await load_files(file , file_metadata)
      print(loaded_document)
      logging.info(f"loaded {file.filename} successfully")
      #run the rest file processesses in the background
      background_tasks.add_task(uploaded_file_processing , loaded_document , file.filename)

      
      return {"message": f"File '{file.filename}' uploaded successfully."}
