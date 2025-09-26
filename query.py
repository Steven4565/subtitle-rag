from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from collections import deque
import os
from dotenv import load_dotenv

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


for hit in hits: 
    print()
    print(hit["_source"]["text"])
    print(hit["_score"])
