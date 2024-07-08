import asyncio
import hashlib

from fastapi import  Request
from redis import asyncio as aioredis
from starlette.templating import Jinja2Templates

redis = aioredis.from_url("redis://localhost:6379", encoding="utf-8", decode_responses=True)

# Подключаем Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Функция для генерации ключа кэша
def generate_cache_key(request: Request) -> str:
    url = str(request.url)
    return hashlib.md5(url.encode()).hexdigest()

# Асинхронная функция для рендеринга шаблонов
async def render_template(template_name: str, context: dict) -> str:
    loop = asyncio.get_event_loop()
    content = await loop.run_in_executor(None, templates.get_template(template_name).render, context)
    return content