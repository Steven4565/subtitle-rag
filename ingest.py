from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from collections import deque
import srt
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

# Config

max_lines_per_chunk = 11
overlap = 0.5 # 50%

step = max_lines_per_chunk - int(max_lines_per_chunk * overlap)

# Ingest

def format_chunk(buffer): 
    text = " ".join(map(lambda x: x["text"], buffer))
    return {
        "_index": index_name,
        "_source": {
            "text": text,
            "start": buffer[0]["start"].total_seconds(),
            "end": (buffer[-1]["end"].total_seconds())
        }
    }

chunks = []

buffer = deque()
for vid in videos: 
    with open(vid, 'r', encoding='utf-8') as f:
        subtitle_generator = srt.parse(f.read())
        subtitles = list(subtitle_generator)
        for sub in subtitles: 
            buffer.append({
                "text": sub.content,
                "end": sub.end,
                "start": sub.start
            })

            if (len(buffer) >= max_lines_per_chunk):
                chunks.append(format_chunk(list(buffer)))

                for _ in range(step): 
                    buffer.popleft()



bulk(client, chunks)
