# PALATE — container image for Hugging Face Spaces (Docker SDK) or any Docker host.
# Zero dependencies: Python stdlib only.
FROM python:3.12-slim

# HF Spaces expects port 7860 by default; any host can override with $PORT.
ENV PORT=7860 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PALATE_MODE=auto

WORKDIR /app
COPY . /app

# Run as a non-root user.
RUN useradd -m -u 1000 palate && chown -R palate:palate /app
USER palate

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD python3 -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/healthz' % os.environ.get('PORT','7860'), timeout=3)"

CMD ["python3", "app.py"]
