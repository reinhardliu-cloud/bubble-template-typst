import os
import uuid
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from converter import convert, list_templates, get_session_dir

SESSIONS_DIR = Path("/sessions")
SESSION_TTL_MINUTES = 30

# In-memory record of session creation times
session_registry: dict[str, datetime] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    task = asyncio.create_task(cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="MD→Typst Converter", lifespan=lifespan)


async def cleanup_loop():
    """Background task: every 5 minutes, delete sessions older than 30 minutes."""
    while True:
        await asyncio.sleep(300)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_TTL_MINUTES)
        expired = [sid for sid, ts in list(session_registry.items()) if ts < cutoff]
        for sid in expired:
            session_dir = get_session_dir(sid)
            if session_dir.exists():
                shutil.rmtree(session_dir, ignore_errors=True)
            session_registry.pop(sid, None)


@app.get("/api/templates")
def api_templates():
    return list_templates()


@app.post("/api/convert")
async def api_convert(
    md_file: UploadFile = File(...),
    template_id: str = Form(...),
    params: str = Form(default="{}"),
    logo_file: UploadFile = File(default=None),
):
    md_content = (await md_file.read()).decode("utf-8")
    params_dict = json.loads(params)

    logo_bytes = None
    logo_filename = None
    if logo_file and logo_file.filename:
        logo_bytes = await logo_file.read()
        logo_filename = logo_file.filename

    session_id = str(uuid.uuid4())
    session_registry[session_id] = datetime.now(timezone.utc)

    try:
        files = convert(
            session_id=session_id,
            md_content=md_content,
            template_id=template_id,
            params_override=params_dict,
            logo_bytes=logo_bytes,
            logo_filename=logo_filename,
        )
    except RuntimeError as e:
        shutil.rmtree(get_session_dir(session_id), ignore_errors=True)
        session_registry.pop(session_id, None)
        raise HTTPException(status_code=422, detail=str(e))

    return JSONResponse({
        "session_id": session_id,
        "files": {
            "pdf":  f"/api/session/{session_id}/output.pdf",
            "docx": f"/api/session/{session_id}/output.docx",
            "odt":  f"/api/session/{session_id}/output.odt",
        }
    })


@app.get("/api/session/{session_id}/{filename}")
def api_download(session_id: str, filename: str):
    allowed = {"output.pdf", "output.docx", "output.odt"}
    if filename not in allowed:
        raise HTTPException(status_code=404)
    path = get_session_dir(session_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found or expired")
    media_types = {
        "output.pdf":  "application/pdf",
        "output.docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "output.odt":  "application/vnd.oasis.opendocument.text",
    }
    return FileResponse(str(path), media_type=media_types[filename], filename=filename)


# Serve static frontend
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")
