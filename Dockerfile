# campusfound - container image for Railway, Render, Fly.io, Koyeb or any Docker host.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_CONFIG=production \
    TRUST_PROXY=1 \
    DATA_DIR=/data

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /data

# The host sets PORT; 8080 is used when it doesn't.
ENV PORT=8080
EXPOSE 8080
CMD ["python", "run.py", "--no-browser"]
