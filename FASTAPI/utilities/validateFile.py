import json 
import logging
import os
from fastapi import HTTPException , UploadFile

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configfile.json")
with open(CONFIG_PATH , "r") as con :
  configfile = json.load(con)

  ALLOWED_EXTENSIONS = set(configfile['Allowed_Extensions'])
  
def Validate_uploaded_file(file : UploadFile):
   filename = file.filename.lower()
   _, extension = os.path.splitext(filename)
   logging.info(f"Validating extension: {extension}")
   if extension not in ALLOWED_EXTENSIONS:
    logging.error(f"Extension not allowed: {extension}")
    raise HTTPException(status_code=400 , detail = "File type not allowed!")
   else:
     logging.info(f"successfully uploaded : {filename}")