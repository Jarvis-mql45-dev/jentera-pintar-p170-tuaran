"""
Vercel Serverless entry point untuk JenteraPintar P170 Tuaran.
FastAPI app diimport dari backend/main.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.main import app

@app.middleware("http")
async def clean_json_response(request, call_next):
    response = await call_next(request)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response