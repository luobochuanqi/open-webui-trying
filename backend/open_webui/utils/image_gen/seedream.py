from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

import aiohttp
from open_webui.config import SEEDREAM_API_KEY, SEEDREAM_BASE_URL, SEEDREAM_MODEL, SEEDREAM_SIZE
from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL

log = logging.getLogger(__name__)


async def seedream_generate(
    prompt: str,
    n: int = 1,
    size: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    base_url: str | None = None,
) -> list[dict]:
    key = api_key or SEEDREAM_API_KEY
    url = (base_url or SEEDREAM_BASE_URL).rstrip('/')
    model_id = model or SEEDREAM_MODEL
    image_size = size or SEEDREAM_SIZE

    headers = {
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }

    payload = {
        'model': model_id,
        'prompt': prompt,
        'n': n,
        'size': image_size,
        'response_format': 'url',
        'watermark': False,
        'stream': False,
    }

    timeout = aiohttp.ClientTimeout(total=120)

    async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
        async with session.post(
            f'{url}/images/generations',
            json=payload,
            headers=headers,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as r:
            r.raise_for_status()
            result = await r.json(content_type=None)

    images = []
    for item in result.get('data', []):
        url_val = item.get('url', '')
        revised_prompt = item.get('revised_prompt', '')
        images.append({'url': url_val, 'revised_prompt': revised_prompt})

    return images


async def seedream_models(api_key: str | None = None, base_url: str | None = None) -> list[dict]:
    return [
        {'id': SEEDREAM_MODEL, 'name': 'Seedream 5.0 Lite'},
    ]
