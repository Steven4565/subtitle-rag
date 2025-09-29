from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv
import requests

load_dotenv()

subtitle_dir = "./subtitles/"
videos = [subtitle_dir + vid for vid in os.listdir(subtitle_dir)]

client = Elasticsearch(
    os.getenv("ES_ENDPOINT"),
    api_key=os.getenv("API_KEY")
)

index_name = "search-test"

query = "How fast should voice agents respond?"

res = client.search(
    index=index_name,
    size=10,
    retriever={
        "rrf": {
            "retrievers": {
                "standard": {
                    "query": {
                        "match": {
                            "text": query
                        }
                    }
                },
                "standard": {
                    "query": {
                        "semantic": {
                            "field": "semantic",
                            "query": query
                        }
                    }
                }
            }
        }
    }
)

best_hit = res["hits"]["hits"][0]
hits = res["hits"]["hits"]

# Rerank hits

model_id = "cross-encoder/ms-marco-MiniLM-L-6-v2"

client.inference.put(
    task_type="rerank",
    inference_id="bge-m3-reranker-local",
    inference_config={
        "service": "elasticsearch",
        "service_settings": {
            "model_id": "baai__bge-reranker-v2-m3",
            "num_allocations": 1,
            "num_threads": 1
        }
    }
)


candidates = [hit["_source"]["text"] for hit in hits]

url = "http://localhost:8000/rerank"
payload = {
    "query": query, 
    "candidates": candidates
}

response = requests.post(url, json=payload)

if response.status_code == 200:
    result = response.json()
    print(result["reranked"])
else:
    print(f"Error {response.status_code}: {response.text}")
