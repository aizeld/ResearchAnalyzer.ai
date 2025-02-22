import os

from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi import File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import aiohttp
import fitz  # PyMuPDF
from src.api_.clients.scihub import SciHubApi
from pgpt_python.client import PrivateGPTApi
import sqlite3

from src.consts import DB_PATH, DOWNLOAD_FOLDER
from src.api_.routers.main import router
from src.dependencies import pgpt_client


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS file_gpt_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            doc_id TEXT NOT NULL
        )
    """
    )
    conn.commit()
    conn.close()


init_db()


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # for frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router=router)
