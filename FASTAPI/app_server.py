import logging 
logging.basicConfig(level=logging.INFO)
from fastapi import FastAPI ,Request 
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import json


from routes.fileupload import router as uploadfile_route
from routes.chatbot import router as chat_route

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
 
app.include_router(chat_route , prefix="")
app.include_router(uploadfile_route , prefix="")