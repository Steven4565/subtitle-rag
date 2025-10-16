from opensearchpy import OpenSearch
import re
import openai
import os
from dotenv import load_dotenv
from typing import List
import srt

load_dotenv()

server_url = os.getenv("LLM_SERVER_URL")
model_name = os.getenv("MODEL_NAME") or "hf.co/Qwen/Qwen3-8B-GGUF:Q5_K_M"

llm = openai.OpenAI(base_url=server_url, api_key="dummy")

def get_llm_prompt(context: str, query: str):
    prompt = f"""
You are an agent for extracting video segments using the given query. Your task is to figure out which chunk of the passage can answer the user's query. You need to output the ID of two timestamps: the start of the chunk that contains the information and the end of the chunk that contains the information.

Context: 
{context}
Query: {query}
    """
    return prompt


def send_query(client: OpenSearch, index_name: str, query: str):
    body = {
    "size": 1,
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

    res = client.search(index=index_name, body=body,
                        params={"search_pipeline": "hybrid-rrf-then-rerank"})
    hits = res["hits"]["hits"]
    hits = [hit["_source"] for hit in hits]
    return hits

def extract_subtitles(res, subtitle_list: List[srt.Subtitle]):
    sub_processed = []
    ids = res[0]['sources']

    sub_buffer = []
    for sub in subtitle_list: 
        if (sub.index in ids): 
            sub_buffer.append(sub)
    sub_processed.append(sub_buffer)

    return sub_processed

def format_for_llm(sub_list: List[srt.Subtitle]): 
    formatted = ""
    for sub in sub_list:
        print(sub)
        formatted +=  f"{sub.index}: {sub.content}\n"

    return formatted

def query_llm(prompt: str):
    text = llm.chat.completions.create(
        model=model_name,
        stream=False,
        messages=[{"role": "user", "content": prompt}],
        temperature=1,
        max_tokens=4096,
    )
    text = text.choices[0].message.content

    if (not text): 
        raise ValueError("LLM did not generate text")

    trimmed = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    start, end = trimmed.split(",")
    return int(start), int(end)

def get_subtitle(sub_url): 
    with open(sub_url, "r", encoding="utf-8") as f:
        subtitles = list(srt.parse(f.read()))
        return subtitles

def query_os(client, index_name, query):
    res = send_query(client, index_name, query)

    subtitle_list = get_subtitle(res[0]["video"])
    sub_extracted = extract_subtitles(res, subtitle_list)[0]

    formatted = format_for_llm(sub_extracted)
    llm_prompt = get_llm_prompt(formatted, query)

    start, end = query_llm(llm_prompt) # Start and end IDs
    start_timestamp = None
    end_timestamp = None
    for sub in subtitle_list:
        if (sub.index == start):
            start_timestamp = sub.start
        if (sub.index == end):
            start_timestamp = sub.end

    return start_timestamp, end_timestamp


# Run Query
if __name__ == "__main__":
    client = OpenSearch(
        hosts=[{"host": os.getenv("HOST"), "port": os.getenv("PORT")}],
        http_auth=("admin", os.getenv("PASSWORD")),
        use_ssl=True,
        verify_certs=False,          # dev only; better: set ca_certs="path/to/root-ca.pem"
        ssl_assert_hostname=False,   # dev only
        ssl_show_warn=False          # hide warnings in dev
    )

    index_name = "search-test"

    query_text = "How fast should voice agents respond?"
    print(query_os(client, index_name, query_text))
