"""
Vercel Serverless entry point untuk JenteraPintar P170 Tuaran.
FastAPI app diimport dari backend/main.py
"""
import sys
import os

# Tambah root project ke sys.path supaya import backend/ berfungsi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Tambah juga path ke folder backend/ untuk import mutlak berfungsi
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.main import app