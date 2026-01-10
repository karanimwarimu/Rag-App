import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader, Docx2txtLoader 
from langchain_unstructured import UnstructuredLoader
import os

async def load_files(file , metadata):

    file_extension= metadata['file_extension']
    
    with tempfile.NamedTemporaryFile(delete=False , suffix=file_extension) as temp :
        temp.write(await file.read())
        temp_path = temp.name

        await file.seek(0)
       
    if file_extension == '.docx' :
      loader = Docx2txtLoader(temp_path) 
    elif file_extension == '.pdf' :
       loader = PyPDFLoader(temp_path)
    elif file_extension == '.txt':
       loader = TextLoader(temp_path)
    else :
       loader = UnstructuredLoader(temp_path ,  strategy="ocr_only" ,ocr_languages=["eng"])
           
    loaded_documents = loader.load()

    for doc in loaded_documents:
       doc.metadata["source"] = file.filename
       doc.metadata.update(metadata)

    os.remove(temp_path)

    return loaded_documents

