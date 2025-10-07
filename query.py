from opensearchpy import OpenSearch
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

    Context: {context}
    Query: {query}
    """
    return prompt


def send_query(client: OpenSearch, index_name: str, query: str):
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

def extract_subtitles(res):
# Find lines with ID
    sub_processed = []
    for hit in res: 
        sources = hit["sources"]
        sub_url = hit["video"]
        with open(sub_url, "r", encoding="utf-8") as f:
            subtitles = list(srt.parse(f.read()))

            sub_buffer = []
            for sub in subtitles: 
                if (sub.index in sources): 
                    sub_buffer.append(sub)
            sub_processed.append(sub_buffer)

    return sub_processed

def format_for_llm(sub_list: List[List[srt.Subtitle]]): 
    formatted = ""
    for video_sub in sub_list: 
        for sub in video_sub:
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
    trimmed = text.replace("<think>", "")
    trimmed = trimmed.replace("</think>", "")
    trimmed = trimmed.strip()

    start, end = trimmed.split(",")
    return int(start), int(end)


# Run Query

subtitle_dir = "./subtitles/"
videos = [subtitle_dir + vid for vid in os.listdir(subtitle_dir)]

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

res = send_query(client, index_name, query)

sub_extracted = extract_subtitles(res)

start, end = query_llm(get_llm_prompt(format_for_llm([sub_extracted[0]]), query)) # Start and end IDs
