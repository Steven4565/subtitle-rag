import requests

def test_rerank(): 
    url = "http://localhost:8000/rerank"

    payload = {
        "query": "what is a cat?", 
        "candidates": [
            "a cat is an animal",
            "I love spaceships",
            "cats are actually monkeys"
        ]
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        result = response.json()
        print(result["reranked"])
    else:
        print(f"Error {response.status_code}: {response.text}")

def test_dense(): 
    url = "http://localhost:8000/dense"

    payload = {
        "passages": [
            "a cat is an animal",
            "I love spaceships",
            "cats are actually monkeys"
        ]
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        result = response.json()
        print(result["embeddings"])
    else:
        print(f"Error {response.status_code}: {response.text}")


test_dense()
