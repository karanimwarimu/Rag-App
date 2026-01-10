import json
from sentence_transformers import SentenceTransformer
from typing import List,Dict,Any
from langchain_core.documents import Document

import os
import sys
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
import numpy as np

load_dotenv()   

with open("configfile.json", "r") as dir:
  configfile = json.load(dir)

embedding_model_path = configfile["Embedding Model"]



api_key = os.getenv("Embedding_KEY")

if not api_key :
 print("Errorcode : check the api key !!")
 sys.exit(1)
else :
 print("apikey correct :) ")
 
 
client = InferenceClient(
    provider="hf-inference",
    api_key = api_key
)


#embedding_model = SentenceTransformer(embedding_model_path)


def encode(sentences, normalize_embeddings=True):
    embeddings = client.feature_extraction(
        sentences,
        model=embedding_model_path
    )

    embeddings = np.array(embeddings)

    if normalize_embeddings:
        if embeddings.ndim == 1:
            # single sentence
            embeddings = embeddings / np.linalg.norm(embeddings)
        else:
            # batch of sentences
            embeddings = embeddings / np.linalg.norm(
                embeddings, axis=1, keepdims=True
            )

    return embeddings




async def embedd_documents(chunked_docs : List[Document]) -> List[Dict[str,Any]]:
 doc_contents = [chunk.page_content for chunk in chunked_docs]
 embedded_contents = encode(doc_contents)

 embedded_chunks = []

 for chunk , embedding in zip(chunked_docs , embedded_contents):
      embedded_chunks.append({
         "page_content": chunk.page_content,
         "metadata": chunk.metadata,
         "embedding": embedding
   })
   
 return embedded_chunks


async def embedd_prompts(prompt : str) :
   embedded_prompt = encode(prompt)
   return embedded_prompt


