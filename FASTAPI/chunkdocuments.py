from langchain_text_splitters import RecursiveCharacterTextSplitter
import uuid 


def get_chunk_size(text_length):
    if text_length > 5000 :
        return 800
    elif text_length > 2000 :
        return 600
    else :
        return 400
    
async def chunk_loaded_documents(loaded_documents):
    documents_chunks = []
    chunk_counter = 1

    for doc_index, doc in enumerate(loaded_documents):

        text = doc.page_content
        if not text or not isinstance(text,  str):
           text = "[No text extracted from this image.]"
           doc.metadata["empty_ocr"] = True
           doc.metadata["reason"] = "No text extracted from this image"
        doc.page_content = text

        doc_size = len(text)

        CHUNK_SIZE =  get_chunk_size(doc_size)
        CHUNK_OVERLAP = CHUNK_OVERLAP = int(CHUNK_SIZE * 0.2)  # 20% overlap for context

        doc_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size = CHUNK_SIZE ,
            chunk_overlap = CHUNK_OVERLAP
        )

        raw_chunks = doc_splitter.split_documents([doc])
        raw_chunks_size = len(raw_chunks)

        for i , chunk in enumerate(raw_chunks):
            chunk.metadata.update({
                "chunk_id" : chunk_counter,
                "chunk_uuid": f"{doc.metadata.get('source', f'doc_{doc_index}')}_{str(uuid.uuid4())}" ,
                "chunk_size": raw_chunks_size ,
                "source": doc.metadata.get("source", f"doc_{doc_index}"),
                "original_size": doc_size
            }) 
            chunk_counter +=1 
        documents_chunks.extend(raw_chunks)
            

    return documents_chunks