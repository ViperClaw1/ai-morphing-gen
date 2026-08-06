import redis
from rq import Queue

from app.core.config import get_settings

settings = get_settings()
redis_conn = redis.from_url(settings.redis_url)

# RQ has no priority field — priority is positional, set by worker startup order
# (`rq worker preview_gpu full_gpu` drains preview_gpu first). Preview jobs must win over
# full renders (CLAUDE.md architecture rule) — keep preview_queue first wherever a worker
# command is written, not just here.
preview_queue = Queue("preview_gpu", connection=redis_conn)
full_queue = Queue("full_gpu", connection=redis_conn)
