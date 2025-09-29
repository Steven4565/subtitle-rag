from elasticsearch import Elasticsearch
import os
from dotenv import load_dotenv

load_dotenv()

client = Elasticsearch(
    os.getenv("ES_ENDPOINT"),
    api_key=os.getenv("API_KEY")
)


index_name = "search-test"

if (client.indices.exists(index=index_name)):
    client.indices.delete(index=index_name)
client.indices.create(index=index_name)

mappings = {
"properties": {
    "dense": {
        "type": "dense_vector",
        "dims": 384
    },
    "text": {
        "type": "text",
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
