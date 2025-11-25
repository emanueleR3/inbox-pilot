"""Utility functions for forwarding requests to Jerry automations service."""

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import httpx
import json
import os

# Base URL for the automations service (Jerry chatbot running on port 8010)
JERRY_BASE_URL = os.getenv("JERRY_API_URL", "http://automations:8010")


async def forward_post(endpoint: str, payload: dict):
    """
    Forward a POST request to the Jerry automations service.
    
    Args:
        endpoint: The API endpoint (e.g., "/thread/create")
        payload: The JSON payload to send
        
    Returns:
        The JSON response from the service
    """
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            url = f"{JERRY_BASE_URL}/jerry{endpoint}"
            res = await client.post(url, json=payload)
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
    """
    Forward a GET request to the Jerry automations service.
    
    Args:
        endpoint: The API endpoint (e.g., "/tools")
        
    Returns:
        The JSON response from the service
    """
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            url = f"{JERRY_BASE_URL}/jerry{endpoint}"
            res = await client.get(url)
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


async def forward_delete(endpoint: str):
    """
    Forward a DELETE request to the Jerry automations service.
    
    Args:
        endpoint: The API endpoint (e.g., "/thread/{thread_id}")
        
    Returns:
        The JSON response from the service
    """
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            url = f"{JERRY_BASE_URL}/jerry{endpoint}"
            res = await client.delete(url)
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


async def forward_stream(endpoint: str, payload: dict):
    """
    Forward a streaming POST request to the Jerry automations service.
    
    Args:
        endpoint: The API endpoint (e.g., "/message/stream")
        payload: The JSON payload to send
        
    Yields:
        Streaming response chunks
    """
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            url = f"{JERRY_BASE_URL}/jerry{endpoint}"
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    yield chunk
        except httpx.HTTPStatusError as e:
            try:
                err_json = e.response.json()
                detail = err_json.get("detail", str(err_json))
            except json.JSONDecodeError:
                detail = e.response.text
            error_data = {"error": detail, "type": "error"}
            yield f"data: {json.dumps(error_data)}\n\n"
        except Exception as e:
            error_data = {"error": str(e), "type": "error"}
            yield f"data: {json.dumps(error_data)}\n\n"
