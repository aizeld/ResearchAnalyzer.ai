from pathlib import Path
import aiohttp
from fastapi import HTTPException
import fitz  # PyMuPDF

DOWNLOAD_FOLDER = Path("../Media")
DOWNLOAD_FOLDER.mkdir(exist_ok=True)

async def download_pdf(pdf_url: str, filename: str) -> Path:
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
