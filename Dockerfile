# Railway: unpacks campusfound-github.zip (uploaded next to this file) and runs the app.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 FLASK_CONFIG=production TRUST_PROXY=1 DATA_DIR=/data
WORKDIR /build
COPY campusfound-github.zip .
RUN python -m zipfile -e campusfound-github.zip /build && mv /build/campusfound /app && rm -rf /build
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt && mkdir -p /data
ENV PORT=8080
EXPOSE 8080
CMD ["python", "run.py", "--no-browser"]
