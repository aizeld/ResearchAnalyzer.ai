from pathlib import Path

from fastapi import HTTPException
import aiohttp
import fitz
import test

from src.consts import DOWNLOAD_FOLDER


def extract_text_from_pdf(file_path: Path) -> str:
    text = ""
    with fitz.open(file_path) as pdf:
        for page in pdf:
            page_text = page.get_text()
            text += page_text
    return text


async def download_pdf(pdf_url: str, filename: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(pdf_url) as response:
                print(pdf_url)
                if response.status == 200:
                    file_path = DOWNLOAD_FOLDER / filename
                    with open(file_path, "wb") as f:
                        text = await response.read()
                        print(str(text))
                        f.write(text)
                    return file_path
                else:
                    raise HTTPException(
                        status_code=404, detail="Failed to download PDF"
                    )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error occurred: {str(e)}")
