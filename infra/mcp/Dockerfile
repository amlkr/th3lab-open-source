FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY th3lab_mcp.py .

EXPOSE 8090

CMD ["uvicorn", "th3lab_mcp:app", "--host", "0.0.0.0", "--port", "8090"]
