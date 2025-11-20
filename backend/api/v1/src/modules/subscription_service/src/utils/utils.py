from fastapi import HTTPException
import httpx
import json
import os

BASE_URL = os.getenv("AUTOMATION_API_URL")


async def forward_post(endpoint: str, payload: dict):
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            res = await client.post(f"{BASE_URL}internal-quiz{endpoint}", json=payload)
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            try:
                err_json = e.response.json()
                detail = err_json.get("detail", str(err_json))
            except json.JSONDecodeError:
                detail = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


async def forward_get(endpoint: str):
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            res = await client.get(f"{BASE_URL}internal-quiz{endpoint}")
            res.raise_for_status()
            return res.json()
        except httpx.HTTPStatusError as e:
            try:
                err_json = e.response.json()
                detail = err_json.get("detail", str(err_json))
            except json.JSONDecodeError:
                detail = e.response.text
            raise HTTPException(status_code=e.response.status_code, detail=detail)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
