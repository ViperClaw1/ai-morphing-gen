FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app app

# Railway injects $PORT; shell form so it expands. Same image runs the worker too —
# override the Start Command on that Railway service (see backend/README.md).
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
