from opensearchpy import OpenSearch
import os
from dotenv import load_dotenv

load_dotenv()

subtitle_dir = "./subtitles/"
videos = [subtitle_dir + vid for vid in os.listdir(subtitle_dir)]

MODEL_ID = "c3sXuJkBnoPkpWRkhFjQ"

client = OpenSearch(
    hosts=[{"host": "desktop", "port": 9200}],
    http_auth=("admin", os.getenv("PASSWORD")),
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

index_name = "search-test"

query = "How fast should voice agents respond?"

body = {
  "size": 10,
  "query": {
    "hybrid": {
      "queries": [
        {
            "match": {"text": query}
        },
        {
            "neural": {
                "dense": {
                    "query_text": query,
                    "model_id": MODEL_ID,
                    "k": 50
                }
            }
         }
      ]
    }
  },
  "ext": {
    "rerank": {
      "query_context": {
        "query_text": query
      }
    }
  },
  "_source": {"exclude": ["dense"]}
}

res = client.search(index="search-test", body=body,
                     params={"search_pipeline": "hybrid-rrf-then-rerank"})
hits = res["hits"]["hits"]
candidates = [hit["_source"]["text"] for hit in hits]
for c in candidates: 
    print(c)
    print()
