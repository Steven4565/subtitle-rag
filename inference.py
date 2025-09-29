from sentence_transformers import SentenceTransformer
from FlagEmbedding import FlagReranker
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Tuple

sentences = ["This is an example sentence", "Each sentence is converted"]

embedding_model = SentenceTransformer('./all-MiniLM-L6-v2/')
reranker = FlagReranker('./bge-reranker-v2-m3/', use_fp16=True)

app = FastAPI()

print("Inference server started")

class RerankRequest(BaseModel):
    query: str
    candidates: List[str]

class RerankResponse(BaseModel):
    reranked: List[Tuple[str, float]]

class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]

class EmbeddingRequest(BaseModel):
    passages: List[str]

@app.post("/rerank", response_model=RerankResponse)
def rerank(request: RerankRequest):
    query = request.query
    candidates = request.candidates

    if not candidates:
        raise HTTPException(status_code=400, detail="Candidates list is empty.")

    input = [(query, c) for c in candidates]
    scores: List[float] = reranker.compute_score(input) # type: ignore

    ranked = zip(candidates, scores)
    ranked_sorted = sorted(ranked, key=lambda x: x[1], reverse=True)

    return RerankResponse(reranked=ranked_sorted)

@app.post("/dense", response_model=EmbeddingResponse)
def dense(request: EmbeddingRequest):
    passages = request.passages

    if not passages:
        raise HTTPException(status_code=400, detail="Passage list to embed is empty.")

    embeddings = embedding_model.encode(passages).tolist()

    return EmbeddingResponse(embeddings=embeddings)
