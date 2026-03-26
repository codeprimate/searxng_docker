FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY server.py .
COPY searxng_mcp ./searxng_mcp
CMD ["python", "server.py", "--web"]
