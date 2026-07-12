import tempfile
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_unstructured import UnstructuredLoader
import os
from dotenv import load_dotenv

# Optional scratch-space override; defaults to the OS temp dir when unset.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
STORAGE_DIR = os.getenv("STORAGE_DIR") or None

# Try to import docx2txt loader, fall back gracefully
try:
    from langchain_community.document_loaders import Docx2txtLoader as WordLoader
    DOCX_LOADER_AVAILABLE = True
except ImportError:
    from langchain_community.document_loaders import UnstructuredWordDocumentLoader as WordLoader
    DOCX_LOADER_AVAILABLE = False

async def load_files(file , metadata):

    file_extension= metadata['file_extension']
    
    with tempfile.NamedTemporaryFile(delete=False , suffix=file_extension , dir=STORAGE_DIR) as temp :
        temp.write(await file.read())
        temp_path = temp.name

        await file.seek(0)
       
    if file_extension == '.docx' :
      loader = WordLoader(temp_path)
    elif file_extension == '.pdf' :
       loader = PyPDFLoader(temp_path)
    elif file_extension == '.txt':
       loader = TextLoader(temp_path, encoding="utf-8")
    else :
       loader = UnstructuredLoader(temp_path ,  strategy="ocr_only" ,ocr_languages=["eng"])
            
    loaded_documents = loader.load()

    for doc in loaded_documents:
       doc.metadata["source"] = file.filename
       doc.metadata.update(metadata)

    os.remove(temp_path)

    return loaded_documents

