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

res = client.search(
    index=index_name, 
    size=10, 
    query={
        "semantic": {
            "field": "text",
            "query": "documentations hinders work performance"
        }
    }
)

best_hit = res["hits"]["hits"][0]

print(best_hit["_source"]["text"])
