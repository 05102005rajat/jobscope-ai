import os

from fastapi import Header, HTTPException


def verify_api_key(x_api_key: str = Header(default=None)):
    expected = os.environ.get("API_KEY")
    if not expected:
        # No key configured (e.g. local dev) -- leave the API open.
        return
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
