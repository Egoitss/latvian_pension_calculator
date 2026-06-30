# Production image for the pension calculator (Flask + gunicorn).
# WeasyPrint needs Pango/Cairo/GDK-Pixbuf system libraries; install
# them here so PDF report generation works on Linux hosts.
FROM python:3.12-slim

WORKDIR /app

# The PDF report bundles its own fonts (woff2 via @font-face), so no
# system fonts are needed — just WeasyPrint's native rendering libs.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
      libffi-dev libcairo2 libharfbuzz0b \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

# Run as a non-root user so a runtime flaw can't act as root in the
# container. The app writes budget/counter files under /app and /data,
# so both must be owned by the runtime user.
RUN useradd -u 10001 -m app \
  && mkdir -p /data \
  && chown -R app /app /data
USER app

# Hosts (Render, etc.) inject $PORT; default to 5001 for local docker run.
EXPOSE 5001
CMD ["sh", "-c", "gunicorn -w 2 -t 120 -b 0.0.0.0:${PORT:-5001} app:app"]
