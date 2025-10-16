from opensearchpy import OpenSearch
from opensearch_py_ml.ml_commons import MLCommonClient

import os
from dotenv import load_dotenv

load_dotenv()


def setup_os(index_name, client, ml_client):
    if (client.indices.exists(index=index_name)):
        client.indices.delete(index=index_name)

    body = {
        "settings": {
            "index": {
                "knn": True
            }
        },
        "mappings": {
            "properties": {
                "dense": {
                    "type": "knn_vector",
                    "dimension": 384,
                    "space_type": "l2",
                    "mode": "on_disk",
                    "method": {
                        "name": "hnsw"
                    }
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
    }

    client.indices.create(index=index_name, body=body)

    embedder_id = ml_client.register_pretrained_model(
        model_name="huggingface/sentence-transformers/all-MiniLM-L6-v2",
        model_version="1.0.2",
        model_format="TORCH_SCRIPT",
        deploy_model=True,
        wait_until_deployed=True
    )

    crossenc_id = ml_client.register_pretrained_model(
        model_name="huggingface/cross-encoders/ms-marco-MiniLM-L-6-v2",
        model_version="1.0.2",
        model_format="ONNX",
        deploy_model=True,
        wait_until_deployed=True
    )

    client.ingest.put_pipeline(
        id="emb-minilm",
        body={
            "processors": [{
                "text_embedding": {
                    "model_id": embedder_id,
                    "field_map": {"text": "dense"}
                }
            }]
        }
    )

    def put_search_pipeline(pipeline_id: str, body: dict):
        client.transport.perform_request(
            method="PUT",
            url=f"/_search/pipeline/{pipeline_id}",
            body=body,
        )
        print(f"Created/updated search pipeline: {pipeline_id}")

    put_search_pipeline("hybrid-rrf-then-rerank", {
        "description": "Hybrid (RRF) + cross-encoder rerank",
        "request_processors": [
            {
                "neural_query_enricher": {
                    "default_model_id": embedder_id,
                    "neural_field_default_id": {
                        "dense": embedder_id 
                    }
                }
            }
        ],
        "phase_results_processors": [
            {
                "score-ranker-processor": {
                    "combination": { "technique": "rrf", "rank_constant": 60 }
                }
            }
        ],
        "response_processors": [
            {
                "rerank": {
                    "ml_opensearch": { "model_id": crossenc_id },
                    "context": { "document_fields": ["text"] }
                }
            }
        ]
    })

if __name__ == "__main__":
    client = OpenSearch(
        hosts=[{"host": os.getenv("HOST"), "port": os.getenv("PORT")}],
        http_auth=("admin", os.getenv("PASSWORD")),
        use_ssl=True,
        verify_certs=False,          # dev only; better: set ca_certs="path/to/root-ca.pem"
        ssl_assert_hostname=False,   # dev only
        ssl_show_warn=False          # hide warnings in dev
    )
    ml_client = MLCommonClient(client)
    index_name = "search-test"
    setup_os(index_name, client, ml_client)

