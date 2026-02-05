#!/usr/bin/env python3
"""
Run script for the AI-Agent FastAPI application.
Simply execute: python run.py
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
