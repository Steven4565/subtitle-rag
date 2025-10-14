import streamlit as st
import srt

index_name = "search-test"

st.title("Subtitle Based Video Retriever")

files = st.file_uploader(
    "Drop one or more .srt files here",
    type=["srt"],
    accept_multiple_files=True,
)

if not files:
    st.info("Upload .srt files to preview.")
    st.stop()

for upl in files:
    name = upl.name
    try:
        text = upl.getvalue().decode("utf-8", errors="replace")
        subs = list(srt.parse(text))

    except srt.SRTParseError as e:
        st.error(f"{name}: SRT parse error — {e}")
    except Exception as e:
        st.error(f"{name}: Unexpected error — {e}")

st.divider()

query = st.text_input("query")

