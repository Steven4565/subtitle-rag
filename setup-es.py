from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

client = Elasticsearch(
    os.getenv("ES_ENDPOINT"),
    api_key=os.getenv("API_KEY")
)


index_name = "search-test"

if (not client.indices.exists(index=index_name)):
    client.indices.create(index=index_name)
else: 
    client.indices.delete(index=index_name)
    client.indices.create(index=index_name)

mappings = {
"properties": {
    "semantic": {
        "type": "semantic_text",
    },
    "text": {
        "type": "text",
        "copy_to": "semantic"
    },
    "video": {
        "type": "text",
        "index": False
    },
    "sources": {
        "type": "object",
        "enabled": False
    }
}
 }

client.indices.put_mapping(index=index_name, body=mappings)
