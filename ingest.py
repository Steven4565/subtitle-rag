from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from collections import deque
import srt
import os
from dotenv import load_dotenv
load_dotenv()

# Config

index_name = "search-test"
max_words_per_chunk = 200
overlap = 0.3
subtitle_dir = "/subtitles/"


# Get subtitles

current_directory_abspath = os.path.abspath(os.getcwd())
joined_dir = current_directory_abspath + subtitle_dir 
videos = [joined_dir + vid for vid in os.listdir(joined_dir)]

client = OpenSearch(
    hosts=[{"host": "desktop", "port": 9200}],
    http_auth=("admin", os.getenv("PASSWORD")),
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

step = max_words_per_chunk - int(max_words_per_chunk * overlap)

# Ingest
def chunk_subtitles_by_words(videos, max_words_per_chunk=120, overlap_words=20):
    assert max_words_per_chunk > 0, "max_words_per_chunk must be > 0"
    assert 0 <= overlap_words < max_words_per_chunk, "0 <= overlap_words < max_words_per_chunk"

    chunks = []
    buffer_slices = deque()  
    current_words = 0

    def slice_len(s):
        return s["word_span"][1] - s["word_span"][0]

    def emit_chunk():
        nonlocal buffer_slices, current_words
        if current_words == 0:
            return

        parts = []
        sources = []
        for sl in buffer_slices:
            w0, w1 = sl["word_span"]
            parts.append(" ".join(sl["words"][w0:w1]))

            sources.append(sl["index"])

        chunk_text = " ".join([p for p in parts if p])
        chunks.append(
            {
                "_op_type": "index",
                "_index": index_name,
                "pipeline": "emb-minilm",
                "_source": {
                    "text": chunk_text,
                    "video": buffer_slices[0]["video"],
                    "sources": sources
                }
            },
        )

        if overlap_words == 0:
            buffer_slices.clear()
            current_words = 0
            return

        need = overlap_words
        new_buf = deque()
        for sl in reversed(buffer_slices):
            if need <= 0:
                break
            sl_len = slice_len(sl)
            if sl_len <= need:
                new_buf.appendleft(sl)
                need -= sl_len
            else:
                w0, w1 = sl["word_span"]
                trimmed = dict(sl)
                trimmed["word_span"] = [w1 - need, w1]
                new_buf.appendleft(trimmed)
                need = 0

        buffer_slices = new_buf
        current_words = sum(slice_len(s) for s in buffer_slices)

    def add_slice(video, sub, words, start_w, end_w):
        """Add a slice of a subtitle (by word indices) to the rolling buffer."""
        nonlocal current_words
        sl = {
            "video": video,
            "index": sub.index,
            "start": sub.start,
            "end": sub.end,
            "content": sub.content,
            "words": words,
            "word_span": [start_w, end_w],
        }
        buffer_slices.append(sl)
        current_words += (end_w - start_w)

    for vid in videos:
        with open(vid, "r", encoding="utf-8") as f:
            subtitles = list(srt.parse(f.read()))

        for sub in subtitles:
            words = sub.content.split()
            i = 0
            n = len(words)

            while i < n:
                remaining_cap = max_words_per_chunk - current_words
                take = min(remaining_cap, n - i)

                if take == 0:
                    emit_chunk()
                    continue

                if current_words == 0 and (n - i) > max_words_per_chunk:
                    add_slice(vid, sub, words, i, i + max_words_per_chunk)
                    i += max_words_per_chunk
                    emit_chunk() 
                    continue

                add_slice(vid, sub, words, i, i + take)
                i += take

                if current_words >= max_words_per_chunk:
                    emit_chunk()

    if current_words > 0:
        emit_chunk()

    return chunks

chunks = chunk_subtitles_by_words(videos)

bulk(client, actions=chunks)
