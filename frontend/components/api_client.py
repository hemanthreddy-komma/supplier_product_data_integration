import os
from typing import Any, Dict, List, Optional
import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


class APIClient:
    """REST Client for communication with the FastAPI Backend."""

    @staticmethod
    def get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            st.error(f"⚠️ Unable to reach Backend API at `{BACKEND_URL}`. Make sure FastAPI server is running (`uvicorn backend.main:app`).")
            return None
        except httpx.HTTPStatusError as ex:
            st.error(f"API Error ({ex.response.status_code}): {ex.response.text}")
            return None
        except Exception as ex:
            st.error(f"Request failed: {ex}")
            return None

    @staticmethod
    def post(endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Any:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, json=json_data)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            st.error(f"⚠️ Unable to reach Backend API at `{BACKEND_URL}`. Make sure FastAPI server is running (`uvicorn backend.main:app`).")
            return None
        except httpx.HTTPStatusError as ex:
            st.error(f"API Error ({ex.response.status_code}): {ex.response.text}")
            return None
        except Exception as ex:
            st.error(f"Request failed: {ex}")
            return None

    @staticmethod
    def upload_file(endpoint: str, file_bytes: bytes, filename: str) -> Any:
        url = f"{BACKEND_URL}{endpoint}"
        try:
            files = {"file": (filename, file_bytes)}
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, files=files)
                resp.raise_for_status()
                return resp.json()
        except httpx.ConnectError:
            st.error(f"⚠️ Unable to reach Backend API at `{BACKEND_URL}`. Make sure FastAPI server is running (`uvicorn backend.main:app`).")
            return None
        except Exception as ex:
            st.error(f"Upload failed: {ex}")
            return None
