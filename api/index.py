"""
Vercel Serverless entry point untuk JenteraPintar P170 Tuaran.
FastAPI app diimport dari backend/main.py
"""
import sys
import os

# Redirect stdout to stderr
_original_stdout = sys.stdout
sys.stdout = sys.stderr

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.responses import JSONResponse
from fastapi import Request
import traceback

try:
    from backend.main import app
except Exception as e:
    from fastapi import FastAPI
    app = FastAPI()
    error_detail = traceback.format_exc()
    
    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    async def catch_all_error(request: Request, path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(e),
                "traceback": error_detail.split('\n')
            }
        )

@app.middleware("http")
async def clean_json_response(request: Request, call_next):
    response = await call_next(request)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response