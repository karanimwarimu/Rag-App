import json
import chromadb
import uuid
import logging
from typing import List, Dict, Any


with open("configfile.json" , "r" ) as confr :
    configfile = json.load(confr)

PERSISTENT_DB = configfile['Chroma DB']
client = chromadb.PersistentClient(path=PERSISTENT_DB)

COLLECTION_NAME = "my_default_collection_one"

#clean metadata , in ocr images 

def clean_metadata(meta: dict) -> dict:
    safe_meta = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)) or v is None:
            safe_meta[k] = v
        else:
            # Convert list/dict/points into a safe string
            safe_meta[k] = str(v)
    return safe_meta

async def store_embedded_files(embedded_chunks: List[Dict[str, Any]]) -> str:
    """Store embedded chunks in Chroma with safe IDs and metadata."""
    try:
        try:
            collection = client.get_collection(COLLECTION_NAME)
        except Exception:
            collection = client.create_collection(COLLECTION_NAME)

        # Prepare data
        ids, embeddings, documents, metadatas = [], [], [], []
        for chunk in embedded_chunks:
            chunk_id = chunk["metadata"]["chunk_uuid"] 
            ids.append(chunk_id)
            embeddings.append(chunk["embedding"].tolist() if hasattr(chunk["embedding"], "tolist") else chunk["embedding"])
            documents.append(chunk["page_content"])
            #sanitize metadata
            safe_metadata = clean_metadata(chunk.get("metadata" , {"no_metadata"}))
            metadatas.append(safe_metadata)

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas
        )
        logging.info(f"Stored {len(ids)} chunks in collection: {COLLECTION_NAME}")
        return f"Successfully stored {len(ids)} chunks in collection {COLLECTION_NAME}"

    except Exception as e:
        logging.error(f"Failed to store chunks: {e}")
        raise


def check_stored_embeddedchunks():
    client = chromadb.PersistentClient(path=PERSISTENT_DB)

    collection = client.get_collection(name="my_default_collection_one")
    result = collection.get()
    PEEK = collection.peek()
    #print(result)

    return f"  COLECTIONS :  {collection}   RESULTS IN THE COLLECTION :  {result}   PEEEK ::::::::::::: {PEEK}" 

async  def query_chroma(embedded_prompt) :
   client = chromadb.PersistentClient(path=PERSISTENT_DB)
   collection = client.get_collection("my_default_collection_one")
   if not isinstance(embedded_prompt[0], (list, tuple)):
      embedded_prompt = [embedded_prompt]

   chroma_results = collection.query(query_embeddings=embedded_prompt , n_results=4)
   return chroma_results
   

""""

async def store_embedded_files(embedded_chunks):
 #collection = client.get_or_create_collection("my_default_collecion_one")
 try:
    collection = client.get_collection("my_default_collection_one")
 except Exception:
    collection = client.create_collection("my_default_collection_one")

 for chunk in embedded_chunks:
    chunk["ID"] = str(uuid.uuid4())

 store_ID = [chunk["ID"] for chunk in embedded_chunks]
 embeddings = [chunk["embedding"] for chunk in embedded_chunks]
 chunk_content = [chunk["page_content"] for chunk in embedded_chunks]
 chunk_metadata = [chunk["metadata"] for chunk in embedded_chunks]

 collection.add(
    ids = store_ID ,
    embeddings = embeddings ,
    documents = chunk_content ,
    metadatas = chunk_metadata
  )
 return (f"successfully stored {embedded_chunks}")

 """