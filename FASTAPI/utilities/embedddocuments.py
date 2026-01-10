import json
from sentence_transformers import SentenceTransformer
from typing import List,Dict,Any
from langchain_core.documents import Document


with open("configfile.json" , "r") as dir :
    configfile = json.load(dir)

embedding_model_path = configfile["Embedding Model"]
embedding_model = SentenceTransformer(embedding_model_path)




async def embedd_documents(chunked_docs : List[Document]) -> List[Dict[str,Any]]:
 doc_contents = [chunk.page_content for chunk in chunked_docs]
 embedded_contents = embedding_model.encode(doc_contents)

 embedded_chunks = []

 for chunk , embedding in zip(chunked_docs , embedded_contents):
      embedded_chunks.append({
         "page_content": chunk.page_content,
         "metadata": chunk.metadata,
         "embedding": embedding
   })
   
 return embedded_chunks


async def embedd_prompts(prompt : str) :
   embedded_prompt = embedding_model.encode(prompt)
   return embedded_prompt




   """""
   embedded_chunk = dict(chunk)
   embedded_chunk['embedding'] = embedding
   embedded_chunks.append(embedded_chunk)
   """
