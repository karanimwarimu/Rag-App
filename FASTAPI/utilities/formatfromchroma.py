import logging
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sklearn.metrics.pairwise import cosine_similarity
from utilities.postprocessors import trim_chunks, rerank_chunks , filter_and_trim_chunks

# -------------------------
# Format and filter Chroma results (strict context)
# -------------------------
async def format_chroma_query(
    chroma_result,
    top_k=5,
    min_diff=0.01,
    max_len=500,
    include_metadata=True,
    filter_section=None,
):
    import json

    docs = chroma_result.get("documents", [[]])[0]
    distances = chroma_result.get("distances", [[]])[0]
    metadatas = chroma_result.get("metadatas", [[]])[0] if "metadatas" in chroma_result else [{}] * len(docs)

    ranked = sorted(zip(docs, distances, metadatas), key=lambda x: x[1])
    clean_docs, seen = [], []

    for doc, dist, meta in ranked:
        # 🔑 FIX: Postgres returns metadata as string
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}

        if any(abs(dist - d) < min_diff for d in seen):
            continue

        section = meta.get("section", "").lower()
        if filter_section and filter_section.lower() not in section:
            continue

        clean_doc = doc.strip()
        if len(clean_doc) > max_len:
            clean_doc = clean_doc[:max_len] + "..."

        minimal_meta = (
            {k: meta.get(k) for k in ["file name", "page", "page_label", "source", "section"] if k in meta}
            if include_metadata
            else {}
        )

        clean_docs.append({"text": clean_doc, "metadata": minimal_meta})
        seen.append(dist)

        if len(clean_docs) >= top_k:
            break

    logging.info(f"Fetched {len(clean_docs)} strict docs from Supabase.")
    return clean_docs


# -------------------------
# Token-aware chunking for LLM
# -------------------------
async def rechunk_docs(docs, chunk_size=150, chunk_overlap=15):
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    final_chunks = []
    for d in docs:
        raw_chunks = splitter.split_text(d["text"])
        for rc in raw_chunks:
            final_chunks.append({
                "text": rc,
                "metadata": d.get("metadata", {})
            })

    return final_chunks

# -------------------------
# Semantic deduplication
# -------------------------
async def deduplicate_chunks(chunks, embeddings_fn, similarity_threshold=0.85):
    if not chunks:
        return []

    texts = [c["text"] for c in chunks]
    embeddings = embeddings_fn(texts)

    keep, skip_indices = [], set()
    for i, emb in enumerate(embeddings):
        if i in skip_indices:
            continue
        keep.append(chunks[i])  # keep full dict
        sims = cosine_similarity([emb], embeddings[i+1:])[0]
        for j, sim in enumerate(sims):
            if sim >= similarity_threshold:
                skip_indices.add(i + 1 + j)

    return keep


# -------------------------
# Unified strict LLM-ready pipeline
# -------------------------
async def prepare_context(
    chroma_result,
    query_embedding=None,
    embeddings_fn=None,
    tokenizer=None,
    top_k=5,
    apply_rerank=True,
    apply_trim=True,
    max_tokens=1600,
    filter_section=None,
    deduplicate=True,
    dedup_threshold=0.85,
):
    # Step 1: retrieve & filter strictly from Chroma
    formatted = await format_chroma_query(
        chroma_result,
        top_k=top_k*2,
        max_len=max_tokens,
        filter_section=filter_section
    )

    # Step 2: chunk for LLM
    chunks = await rechunk_docs(formatted, chunk_size=150, chunk_overlap=15)

    # Step 3+5: combined rerank and trim
    """""
    if query_embedding is not None and embeddings_fn is not None and tokenizer is not None:
        chunks = await filter_and_trim_chunks(
            chunks,
            query_embedding,
            embeddings_fn,
            tokenizer,
            max_tokens=max_tokens,
            top_k=top_k,
            min_sim=0.7  # optional threshold
        )
     """
     #Step 3: optional rerank for relevance
    if apply_rerank and query_embedding is not None and embeddings_fn is not None:
        chunks = await rerank_chunks(chunks, query_embedding, embeddings_fn, top_k=top_k)

    # Step 4: semantic deduplication
    if deduplicate and embeddings_fn is not None:
        chunks = await deduplicate_chunks(chunks, embeddings_fn, similarity_threshold=dedup_threshold)

    # Step 5: trim strictly for token budget
    if apply_trim and tokenizer is not None:
        chunks = await trim_chunks(chunks, tokenizer, max_tokens=max_tokens)

    return chunks
