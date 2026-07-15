from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pytz
from open_webui.config import QUOTA_DEFAULT_DAILY_IMAGE_LIMIT, QUOTA_DEFAULT_DAILY_TOKEN_BUDGET_RMB
from open_webui.internal.db import get_async_db_context

log = logging.getLogger(__name__)

TZ = pytz.timezone('Asia/Shanghai')

IMAGE_QUOTA_EXCEEDED = '今日生图次数已用完（{current}/{limit}），请明天再试。'
TOKEN_QUOTA_EXCEEDED = '今日 Token 额度已用完（已用 ¥{current:.4f} / 限额 ¥{limit:.2f}），请明天再试。'

DEEPSEEK_PRICING = {
    'deepseek-v4-flash': {
        'cache_hit': 0.02,
        'cache_miss': 1.0,
        'output': 2.0,
    },
    'deepseek-v4-pro': {
        'cache_hit': 0.025,
        'cache_miss': 3.0,
        'output': 6.0,
    },
}

def _today_range():
    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def deepseek_cost(model_id: str, input_tokens: int, output_tokens: int, cache_hit_tokens: int = 0) -> float:
    pricing = DEEPSEEK_PRICING.get(model_id, DEEPSEEK_PRICING['deepseek-v4-flash'])
    cache_miss = max(0, input_tokens - cache_hit_tokens)
    cost = (
        cache_hit_tokens * pricing['cache_hit']
        + cache_miss * pricing['cache_miss']
        + output_tokens * pricing['output']
    ) / 1_000_000
    return cost


async def check_image_quota(user_id: str) -> tuple[bool, int, int]:
    start_ms, end_ms = _today_range()
    async with get_async_db_context() as db:
        from sqlalchemy import func, select
        from open_webui.models.chat_messages import ChatMessage

        result = await db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.user_id == user_id,
                ChatMessage.created_at >= start_ms,
                ChatMessage.created_at < end_ms,
                ChatMessage.model_id.like('seedream%'),
            )
        )
        current = result.scalar() or 0

    limit = QUOTA_DEFAULT_DAILY_IMAGE_LIMIT
    return current >= limit, current, limit


async def check_token_quota(user_id: str) -> tuple[bool, float, float]:
    start_ms, end_ms = _today_range()
    async with get_async_db_context() as db:
        from sqlalchemy import func, select
        from open_webui.models.chat_messages import ChatMessage

        result = await db.execute(
            select(ChatMessage.usage, ChatMessage.model_id).where(
                ChatMessage.user_id == user_id,
                ChatMessage.created_at >= start_ms,
                ChatMessage.created_at < end_ms,
                ChatMessage.usage.isnot(None),
            )
        )
        rows = result.all()

    total_cost = 0.0
    for usage, model_id in rows:
        if not usage:
            continue
        input_tokens = usage.get('input_tokens') or usage.get('prompt_tokens') or 0
        output_tokens = usage.get('output_tokens') or usage.get('completion_tokens') or 0
        cache_hit = _get_cache_hit(usage)
        total_cost += deepseek_cost(model_id or 'deepseek-v4-flash', input_tokens, output_tokens, cache_hit)

    budget = QUOTA_DEFAULT_DAILY_TOKEN_BUDGET_RMB
    return total_cost >= budget, total_cost, budget


def _get_cache_hit(usage: dict) -> int:
    if 'prompt_cache_hit_tokens' in usage:
        return usage['prompt_cache_hit_tokens']
    details = usage.get('prompt_tokens_details') or usage.get('input_tokens_details') or {}
    return details.get('cached_tokens', 0)
