import os
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import aiohttp
import fitz  # PyMuPDF
from src.Api.api import Api
from pgpt_python.client import PrivateGPTApi

app = FastAPI()
summaries_store = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # for frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOAD_FOLDER = Path("../Media")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

# Initialize PrivateGPT client
pgpt_client = PrivateGPTApi(base_url="http://localhost:8001")

async def download_pdf(pdf_url: str, filename: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as response:
                if response.status == 200:
                    file_path = DOWNLOAD_FOLDER / filename
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())
                    return file_path
                else:
                    raise HTTPException(status_code=404, detail="Failed to download PDF")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")

def extract_text_from_pdf(file_path: Path) -> str:
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            page_text = page.get_text()
            text += page_text
    return text

def split_text_into_chunks(text: str, chunk_size: int = 2048) -> list:
    """Split text into manageable chunks."""
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


import concurrent.futures
def summarize_text(text: str) -> str:
    chunks = split_text_into_chunks(text)
    summaries = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for chunk in chunks:
            future = executor.submit(pgpt_client.contextual_completions.prompt_completion, prompt=f"Summarize this document:\n{chunk}")
            try:
                response = future.result(timeout=600)  # Set a 10-minute timeout
                if response.choices:
                    summaries.append(response.choices[0].message.content)
                    print(response.choices[0].message.content)
            except concurrent.futures.TimeoutError:
                print("Summarization request timed out.")
                summaries.append("Summarization request timed out.")
            except Exception as e:
                print(f"An error occurred during summarization: {str(e)}")
                summaries.append("An error occurred during summarization.")
    return " ".join(summaries)

async def background_summarize(file_path: Path, file_name: str):
    text = extract_text_from_pdf(file_path)
    if not text.strip():
        raise ValueError("No text extracted from PDF.")
    summary = await summarize_text(text)
    # You can store the summary in a database or a temporary file for retrieval
    print(f"Summary for {file_path.name}: {summary}")
    summary = await summarize_text(text)
    summaries_store[file_name] = {"summary": summary, "status": "completed"}

@app.get("/files")
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

@app.get("/file/{file_name}")
async def get_file(file_name: str):
    file_path = DOWNLOAD_FOLDER / file_name  
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/summarize/{file_name}")
async def summarize_pdf(file_name: str, background_tasks: BackgroundTasks):
    file_path = DOWNLOAD_FOLDER / file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # Add the summarization task to the background, passing both arguments
    background_tasks.add_task(background_summarize, file_path, file_name)
    
    return {"message": "Summarization started, you will be notified when it's done.", "status_code": 202}


@app.get("/summary/{file_name}")
async def get_summary(file_name: str):
    if file_name in summaries_store:
        return summaries_store[file_name]
    else:
        raise HTTPException(status_code=404, detail="Summary not found or still processing.")


@app.get("/place-pdf")
async def download_scihub_pdf(doi: str):
    try:
        _, html_content = await Api.get_page(doi)
        
        if not html_content:
            raise HTTPException(status_code=500, detail="Empty response content")
        
        soup = BeautifulSoup(html_content, 'html.parser')
        embed_tag = soup.find("embed")
        
        if embed_tag and 'src' in embed_tag.attrs:
            pdf_url = embed_tag['src']
            if pdf_url.startswith("//"):
                pdf_url = "https:" + pdf_url
            pdf_filename = pdf_url.split("/")[-1].split("#")[0]
            
            file_path = await download_pdf(pdf_url, pdf_filename)
            return {"message": "PDF downloaded", "file_path": str(file_path), "status_code": 200}
        else:
            raise HTTPException(status_code=404, detail="PDF link not found in the page content")
    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
