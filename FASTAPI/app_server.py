import logging 
logging.basicConfig(level=logging.INFO)
import os
from fastapi import FastAPI ,Request 
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import jinja2


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


# Use relative paths computed from this file's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
Template_DIR = os.path.join(BASE_DIR, "..", "TEMPLATE")
StaticFiles_DIR = os.path.join(BASE_DIR, "..", "STATIC")

#load files - use explicit loader with cache disabled to avoid Jinja2 LRUCache bug on Windows
jinja2_loader = jinja2.FileSystemLoader(Template_DIR, followlinks=True)
jinja2_env = jinja2.Environment(loader=jinja2_loader, auto_reload=False, enable_async=False, cache_size=0)
templates = Jinja2Templates(env=jinja2_env)


app.mount("/static", StaticFiles(directory= StaticFiles_DIR) , name="static")


#::::::::::::::::::: LOAD WEB PAGES :::::::::::::::::::::::::
 
@app.get('/chatbot' , response_class=HTMLResponse)
async def load_RagChat(request : Request ):
    return templates.TemplateResponse(
    request,                          # <-- Request object goes first
    "RagChatApp.html",
    {"request": request}
)
       
@app.get('/fileuploader' , response_class=HTMLResponse)
async def load_file_Uploader(request:Request):
   return templates.TemplateResponse(
    request,
    "FileUploader.html",
    {"request": request}
   )
 
app.include_router(chat_route , prefix="")
app.include_router(uploadfile_route , prefix="")