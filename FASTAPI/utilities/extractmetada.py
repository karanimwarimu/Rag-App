import logging
import os
from fastapi import File

async def extract_metadata(file , upload_time):
    logging.info(f"received {file.filename} :::::::: ready for metadata extraction ")
    upload_time = upload_time 
    file_name = file.filename.lower()
    file_extension = os.path.splitext(file_name)[1]
    content =  await file.read()
    file_size = len(content)
    await file.seek(0)
    logging.info(f"{file_name} metadata extracted")

    return {
        "upload_time" : upload_time ,
        "file_name": file_name ,
        "file_extension" :file_extension ,
        "file_size" : file_size // 1024
    } 