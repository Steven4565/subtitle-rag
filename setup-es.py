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

mappings = {
"properties": {
    "text": {
        "type": "semantic_text"
    },
    "start": {
        "type": "text",
        "index": False
    },
    "end": {
        "type": "text",
        "index": False
    }
}
 }

client.indices.put_mapping(index=index_name, body=mappings)
