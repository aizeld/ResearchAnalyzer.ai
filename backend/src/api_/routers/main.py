from bs4 import BeautifulSoup
from colorama import Back
from fastapi import APIRouter, HTTPException, BackgroundTasks, File, UploadFile
from fastapi.responses import FileResponse
import sqlite3
import os
from pydantic import BaseModel
from pathlib import Path

from src.api_.clients.scihub import SciHubApi
from src.consts import DOWNLOAD_FOLDER, DB_PATH
from src.dependencies import pgpt_client, summary_store
from src.services.summarization import (
    background_summarize,
    ingest_file_and_store,
)
from src.services.pdf import download_pdf
from src.crud.temp_cruds import get_mapping
from src.schemas.process_doi import ProcessDOISchema
from src.schemas.chat_request import ChatRequest

router = APIRouter()


@router.get("/files")
async def list_files():
    try:
        files = [
            {"name": file.name, "path": str(file.resolve())}
            for file in DOWNLOAD_FOLDER.iterdir()
            if file.is_file() and file.suffix == ".pdf"
        ]
        return {"files": files, "status_code": 200}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")


@router.get("/file/{file_name}")
async def get_file(file_name: str):
    file_path = DOWNLOAD_FOLDER / file_name
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/summarize/{file_name}")
async def summarize_pdf(file_name: str, background_tasks: BackgroundTasks):
    file_path = DOWNLOAD_FOLDER / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    background_tasks.add_task(
        background_summarize,
        pgpt_client,
        summary_store,
        file_path,
        file_name,
    )

    return {
        "message": "Summarization started, you will be notified when it's done.",
        "status_code": 202,
    }


@router.get("/summary/{file_name}")
async def get_summary(file_name: str):
    if file_name in summary_store:
        return summary_store[file_name]
    else:
        raise HTTPException(
            status_code=404, detail="Summary not found or still processing."
        )


@router.post("/process-doi")
async def process_doi(body: ProcessDOISchema, background_tasks: BackgroundTasks):
    try:
        if not body.doi:
            raise HTTPException(status_code=400, detail="Provide a DOI")

        _, html_content = await SciHubApi.get_page(body.doi)
        print(html_content)
        if not html_content:
            raise HTTPException(status_code=500, detail="Empty response content")

        soup = BeautifulSoup(html_content, "html.parser")
        embed_tag = soup.find("embed")
        if embed_tag and "src" in embed_tag.attrs:
            pdf_url = embed_tag["src"]
            
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
                
            pdf_filename = pdf_url.split("/")[-1].split("#")[0]
            file_path = await download_pdf(pdf_url, pdf_filename)
            background_tasks.add_task(ingest_file_and_store, pgpt_client, str(file_path), pdf_filename)
          
            if file_path:
                return {
                        "message": "PDF downloaded successfully. Processing in background.",
                        "file_path": str(file_path),
                    }

        raise HTTPException(
            status_code=404, detail="PDF download URL not found in the page content"
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.post("/process-pdf")
async def process_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(None),
):
    try:
        if not file:
            raise HTTPException(status_code=400, detail="Provide either a file.")

        if file:
            if file.content_type != "application/pdf":
                raise HTTPException(
                    status_code=400, detail="Uploaded file must be a PDF"
                )

            if file.filename is None:
                raise HTTPException(status_code=400, detail="Empty filename")

            file_path = DOWNLOAD_FOLDER / file.filename
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)

            # Queue background ingestion
            filename = file.filename
            if filename is not None and background_tasks:
                background_tasks.add_task(
                    ingest_file_and_store,
                    pgpt_client,
                    str(file_path),
                    filename,
                )

            return {
                "message": "PDF uploaded successfully. Processing in background.",
                "file_path": str(file_path),
            }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/mapping/{filename}")
def get_file_mapping(filename: str):
    """Fetch the GPT document ID for a given file."""
    doc_id = get_mapping(filename)
    return {"filename": filename, "doc_id": doc_id}


@router.get("/all_mapped")
def get_all_mapped():
    """Fetch all the GPT document IDs mapped to filenames."""
    return {"mappings": get_all_ingested()}


@router.get("/list_of_ingested")
def get_all_ingested():
    data = pgpt_client.ingestion.list_ingested().data
    return {"data": data}

@router.delete("/delete_ingested/{filename}")
async def delete_ingested(filename: str):
    try:
        # First, get the doc_id from the database
        doc_id = get_mapping(filename)
        if not doc_id:
            raise HTTPException(status_code=404, detail="File not found in database")

        # Delete from PrivateGPT
        try:
            pgpt_client.ingestion.delete_ingested(doc_id)
        except Exception as e:
            print(f"Error deleting from PrivateGPT: {e}")
            # Continue with other deletions even if PrivateGPT deletion fails

        # Delete from database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Delete from file_gpt_map
            cursor.execute("DELETE FROM file_gpt_map WHERE filename = ?", (filename,))
            # Delete associated conversations
            cursor.execute(
                """
                DELETE FROM conversation_history 
                WHERE file_id IN (SELECT id FROM file_gpt_map WHERE filename = ?)
                """, 
                (filename,)
            )
            conn.commit()
        finally:
            conn.close()

        # Delete the actual file
        file_path = DOWNLOAD_FOLDER / filename
        if file_path.exists():
            os.remove(file_path)  # Using os.remove instead of Path.unlink() for better error handling

        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete_all_ingested")
def delete_all_ingested():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM file_gpt_map")
    conn.commit()
    conn.close()
    
    for file in DOWNLOAD_FOLDER.iterdir():
        if file.is_file() and file.suffix == ".pdf":
            file.unlink()

    list_ids = get_all_ingested()
    list_ids = list_ids["data"]
    for doc in list_ids:
        pgpt_client.ingestion.delete_ingested(doc.doc_id)
        
    return {"message": "All ingested files deleted successfully"}



@router.post("/chat-with-doc")
async def chat_with_doc(request: ChatRequest):
    """Use GPT for contextual completion with a specific document."""
    filename = request.filename
    prompt = request.prompt
    print(filename)

    doc_id = get_mapping(filename)
    if not doc_id:
        raise HTTPException(
            status_code=404, detail="Document ID not found for the given file"
        )
    
    list_ids = get_all_ingested()
    list_ids = list_ids["data"]
    
    found = False
    for doc in list_ids:
        if doc.doc_id == doc_id:
            print(f"found {doc_id}")
            found = True
            break
        
    if found == False:
        return
    
    try:
        result = pgpt_client.contextual_completions.prompt_completion(
            prompt=prompt,
            use_context=True,
            context_filter={"docs_ids": [doc_id]},
            include_sources=True,
        )
        print(result)
        result = result.choices[0]
        
        # Store conversation in the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Get file_id from filename
            cursor.execute("SELECT id FROM file_gpt_map WHERE filename = ?", (filename,))
            file_id_result = cursor.fetchone()
            if file_id_result:
                file_id = file_id_result[0]
                cursor.execute(
                    """
                    INSERT INTO conversation_history (file_id, question, answer)
                    VALUES (?, ?, ?)
                    """,
                    (file_id, prompt, result.message.content)
                )
                conn.commit()
        finally:
            conn.close()
        
        return {
            "response": result.message.content,
            "source": result.sources[0].document.doc_metadata["file_name"],
        }
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail=f"Error during chat: {str(e)}")


@router.get("/chat-history/{filename}")
async def get_chat_history(filename: str):
    """Get chat history for a specific file"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT ch.question, ch.answer, ch.timestamp
            FROM conversation_history ch
            JOIN file_gpt_map fm ON ch.file_id = fm.id
            WHERE fm.filename = ?
            ORDER BY ch.timestamp ASC
            """,
            (filename,)
        )
        rows = cursor.fetchall()
        return [
            {
                "question": row[0],
                "answer": row[1],
                "timestamp": row[2]
            }
            for row in rows
        ]
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/file-id/{filename}")
async def get_file_id(filename: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM file_gpt_map WHERE filename = ?",
            (filename,)
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        return {"id": result[0]}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


class RenameRequest(BaseModel):
    new_filename: str

@router.put("/rename-file/{filename}")
async def rename_file(filename: str, request: RenameRequest):
    try:
        # Ensure new filename has .pdf extension
        if not request.new_filename.lower().endswith('.pdf'):
            request.new_filename += '.pdf'

        # Get the file paths
        old_file_path = DOWNLOAD_FOLDER / filename
        new_file_path = DOWNLOAD_FOLDER / request.new_filename

        # Check if source file exists
        if not old_file_path.exists():
            raise HTTPException(status_code=404, detail="Source file not found")

        # Check if destination filename already exists
        if new_file_path.exists():
            raise HTTPException(status_code=400, detail="A file with this name already exists")

        # Get the doc_id before updating the database
        doc_id = get_mapping(filename)
        if not doc_id:
            raise HTTPException(status_code=404, detail="File not found in database")

        # Update the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            # Update file_gpt_map table
            cursor.execute(
                "UPDATE file_gpt_map SET filename = ? WHERE filename = ?",
                (request.new_filename, filename)
            )
            
            # Update conversation_history table references if needed
            cursor.execute(
                """
                UPDATE conversation_history 
                SET file_id = (SELECT id FROM file_gpt_map WHERE filename = ?)
                WHERE file_id = (SELECT id FROM file_gpt_map WHERE filename = ?)
                """,
                (request.new_filename, filename)
            )
            
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            conn.close()

        # Rename the actual file
        try:
            os.rename(old_file_path, new_file_path)
        except OSError as e:
            # If file rename fails, revert database changes
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "UPDATE file_gpt_map SET filename = ? WHERE filename = ?",
                    (filename, request.new_filename)
                )
                conn.commit()
            finally:
                conn.close()
            raise HTTPException(status_code=500, detail=f"Failed to rename file: {str(e)}")

        return {
            "message": "File renamed successfully",
            "old_name": filename,
            "new_name": request.new_filename
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
