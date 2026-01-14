from huggingface_hub import InferenceClient
import json 
from dotenv import load_dotenv
import os 
import sys 


load_dotenv()

api_key = os.getenv("Embedding_KEY")

if not api_key  :
    print("Check API key !!")
    sys.exit(1)
else :
    print("API key correct :) ")
    
with open("configfile.json") as red :
    configfile= json.load(red)


# Initialize once (at startup)
reranker_model = configfile["cross_encoder_reranker"]

reranker_client = InferenceClient(
    provider="hf-inference",
    api_key = api_key
)

import requests

HF_TOKEN = api_key
#RERANKER_MODEL = reranker_model

MODEL_ID = "BAAI/bge-reranker-large"
MODEL_ID_ENCODED = MODEL_ID.replace("/", "%2F")

API_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    f"{MODEL_ID_ENCODED}/pipeline/text-ranking"
)

HEADERS = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json",
}


"""""
async def rerank_chunks(chunks, query, top_k=2):
    pairs = [(query, c) for c in chunks]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
    return [c for c, _ in ranked[:top_k]]

"""


import tiktoken

async def split_large_chunk(text: str, max_tokens: int = 500, enc_name: str = "cl100k_base"):
    """
    Split a large text chunk into smaller chunks based on max_tokens.
    """
    enc = tiktoken.get_encoding(enc_name)
    tokens = enc.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens):
        sub_tokens = tokens[i:i + max_tokens]
        chunks.append(enc.decode(sub_tokens))
    return chunks

async def rerank_chunks(
    query: str,
    chunks: list,
    top_k: int = 2,
    min_score: float = 0.0,
):
    if not chunks:
        return []

    # Normalize chunks
    formatted_chunks = [
        {"text": c["text"], "metadata": c.get("metadata", {})}
        if isinstance(c, dict)
        else {"text": str(c), "metadata": {}}
        for c in chunks
    ]

    texts = [c["text"] for c in formatted_chunks]

    if not texts:
        return []

    payload = {
        "inputs": {
            "query": query,
            "texts": texts
        }
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload,
        timeout=60,
    )

    response.raise_for_status()
    results = response.json()

    ranked = []
    for r in results:
        if r["score"] >= min_score:
            ranked.append(formatted_chunks[r["index"]])
        if len(ranked) >= top_k:
            break

    return ranked



async def merge_chunks_for_llm(query: str, chunks: list, top_k: int = 5, max_tokens: int = 2000, split_chunk_tokens: int = 500):
    """
    Pre-splits large chunks, reranks, and merges them into a single text for LLM input.
    """
    # Step 1: Pre-split large chunks
    split_chunks = []
    for c in chunks:
        text = c["text"] if isinstance(c, dict) else str(c)
        metadata = c.get("metadata", {}) if isinstance(c, dict) else {}
        sub_texts = await split_large_chunk(text, max_tokens=split_chunk_tokens)
        for sub in sub_texts:
            split_chunks.append({"text": sub, "metadata": metadata})

    # Step 2: Rerank chunks
    reranked = await rerank_chunks(query, split_chunks, top_k=top_k)

    # Step 3: Merge while respecting max_tokens
    merged_text = ""
    total_tokens = 0
    enc = tiktoken.get_encoding("cl100k_base")
    
    for c in reranked:
        text = c["text"]
        tokens = len(enc.encode(text))
        if total_tokens + tokens > max_tokens:
            remaining = max_tokens - total_tokens
            text = enc.decode(enc.encode(text)[:remaining])
            merged_text += "\n" + text
            break
        merged_text += "\n" + text
        total_tokens += tokens

    return merged_text.strip()


