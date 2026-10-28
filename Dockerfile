FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg git && rm -rf /var/lib/apt/lists/*
# yt-dlp ko YouTube ke liye JavaScript runtime (deno) chahiye
COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
