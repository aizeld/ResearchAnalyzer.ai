from pathlib import Path
from pgpt_python.client import PrivateGPTApi

from src.services.pdf import extract_text_from_pdf
from src.crud.temp_cruds import insert_mapping
from src.services.helper import split_text_into_chunks


async def summarize_text(pgpt_client: PrivateGPTApi, text: str) -> str:
    chunks = split_text_into_chunks(text)
    summaries = []
    try:

        for chunk in chunks:
            response = pgpt_client.contextual_completions.prompt_completion(
                prompt=f"Summarize this document:\n{chunk}"
            )
            if response.choices[0].message is not None:
                print(response.choices[0].message.content)

            if response.choices[0].message is not None:
                summaries.append(response.choices[0].message.content)
            return " ".join(summaries)

    except Exception as e:
        print(f"An error occurred during summarization: {str(e)}")
        summaries.append(f"An error occurred during summarization. {str(e)}")
    return " ".join(summaries)


async def background_summarize(
    pgpt_client: PrivateGPTApi,
    summary_store: dict,
    file_path: Path,
    file_name: str,
):
    text = extract_text_from_pdf(file_path)
    if not text.strip():
        raise ValueError("No text extracted from PDF.")
    summary = await summarize_text(pgpt_client, text)
    summary_store[file_name] = {"summary": summary, "status": "completed"}

    print(f"Summary for {file_path.name}: {summary}")


def ingest_file_and_store(pgpt_client: PrivateGPTApi, file_path: str, filename: str):
    with open(file_path, "rb") as f:
        ingested_file_doc_id = (
            pgpt_client.ingestion.ingest_file(file=f, timeout=500).data[0].doc_id
        )
    print(f"Ingested file doc_id: {ingested_file_doc_id}")
    insert_mapping(filename, ingested_file_doc_id)
