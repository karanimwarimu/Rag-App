from fastapi import APIRouter ,BackgroundTasks , UploadFile , File
import logging
from datetime import datetime 


from utilities.validateFile import Validate_uploaded_file
from utilities.extractmetada import extract_metadata
from utilities.documentloader import load_files
from utilities.chunkdocuments import chunk_loaded_documents
from utilities.embedddocuments import embedd_documents 
#from utilities.storeembeddedfiles import store_embedded_files , check_stored_embeddedchunks 
from utilities.database.store_DB import store_embedded_files


router = APIRouter()


#::::::::::::::::: handle the file upload :::::::::::: 
   

async def uploaded_file_processing(loaded_document  , filename ):
    try:
    
        chunked_docs = await  chunk_loaded_documents(loaded_document)
        print(f":::::::::::::::: chUNKED DOCS  {chunked_docs}" )
        logging.info(f"chunked {filename} successfully")

        embedded_chunks  = await embedd_documents(chunked_docs)
        print(embedded_chunks)
        logging.info(f"Embedded  {filename} successfully")

        await store_embedded_files(embedded_chunks)
        
        #strit = check_stored_embeddedchunks()
        #print(f"::::::::::::::::: embedded files (how stored){strit}")
        logging.info(f"stored  {filename}  to chroma successfully")
    except Exception as e :
        print("ERROR :" , e)
        logging.error(f"Couldn't process the file : {filename}")


@router.post('/File_Upload')
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
      logging.info(f"loaded {file.filename} successfully")
      #run the rest file processesses in the background
      background_tasks.add_task(uploaded_file_processing , loaded_document , file.filename)

      
      return {"message": f"File '{file.filename}' uploaded successfully."}