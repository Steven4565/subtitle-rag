import streamlit as st
import os
from opensearchpy import OpenSearch
from ingest import chunk_and_send
from query import query_os
import srt

index_name = "search-test"
subtitle_folder = "/saved_subtitles/"
current_directory_abspath = os.path.abspath(os.getcwd())
subtitle_dir = current_directory_abspath + subtitle_folder

if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0 
if "to_ingest" not in st.session_state:
    st.session_state.to_ingest = []
if "query" not in st.session_state:
    st.session_state.query = ""

st.title("Subtitle Based Video Retriever")

@st.cache_resource
def get_client(): 
    client = OpenSearch(
        hosts=[{"host": os.getenv("HOST"), "port": os.getenv("PORT")}],
        http_auth=("admin", os.getenv("PASSWORD")),
        use_ssl=True,
        verify_certs=False,          # dev only; better: set ca_certs="path/to/root-ca.pem"
        ssl_assert_hostname=False,   # dev only
        ssl_show_warn=False          # hide warnings in dev
    )
    return client

def handle_submit(files):
    os.makedirs(subtitle_dir, exist_ok=True)

    items = st.session_state.get("to_ingest", [])
    if not items:
        st.warning("No parsed subtitle files to ingest.")
        return

    try:
        # Save file locally
        os.makedirs("saved_subtitles", exist_ok=True)
        for file in files: 
            file_path = subtitle_dir + file.name
            with open(file_path, "wb") as f: 
                f.write(file.getbuffer())


        chunk_and_send(get_client(), items, index_name)
        st.success(f"Ingested {len(items)} file(s).")

        st.session_state.to_ingest = []
        st.session_state.uploader_key += 1
    except Exception as e:
        st.error(f"Ingest failed — {e}")

def handle_query_change():
    q = st.session_state.get("query", "").strip()
    if not q:
        return
    try:
        start, end= query_os(get_client(), index_name, q)
        st.write("**Query Result:**")
        st.write(start, end) # TODO: write this in human readable format
    except Exception as e:
        st.error(f"Query error — {e}")

files = st.file_uploader(
    "Drop one or more .srt files here",
    type=["srt"],
    accept_multiple_files=True,
    key=f"uploader-{st.session_state.uploader_key}",
)

if not files and not st.session_state.to_ingest:
    st.info("Upload .srt files to preview.")
else:
    existing_names = {item["name"] for item in st.session_state.to_ingest}
    for upl in files or []:
        name = upl.name
        if name in existing_names:
            continue
        try:
            file_path = subtitle_dir + name
            text = upl.getvalue().decode("utf-8", errors="replace")
            subs = list(srt.parse(text))
            st.session_state.to_ingest.append({"name": file_path, "subs": subs})
        except Exception as e:
            st.error(f"{name}: Unexpected error — {e}")

st.button("Submit", on_click=lambda: handle_submit(files))
st.divider()

st.text_input("query", key="query", on_change=handle_query_change)
