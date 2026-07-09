"""
Vercel Serverless entry point untuk JenteraPintar P170 Tuaran.
FastAPI app diimport dari backend/main.py
"""
import sys
import os

# Redirect stdout to stderr SUPAYA print() TIDAK cemarkan response JSON
_original_stdout = sys.stdout
sys.stdout = sys.stderr

from fastapi.responses import JSONResponse
from fastapi import Request
import traceback

# Tambah root project ke sys.path supaya import backend/ berfungsi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Tambah juga path ke folder backend/ untuk import mutlak berfungsi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from backend.main import app
except Exception as e:
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
    async def catch_all_error(request: Request, path: str):
        error_detail = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(e),
                "traceback": error_detail
            }
        )

# Tambah middleware untuk paksa Content-Type JSON dan bersihkan response
@app.middleware("http")
async def clean_json_response(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response
