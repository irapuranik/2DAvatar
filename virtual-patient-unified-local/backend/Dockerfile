FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . .

# Create directories for runtime data and set up non-root user
RUN mkdir -p /data/uploads/avatars && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /data

USER appuser

# Railway injects PORT at runtime; default to 5001 for local dev
EXPOSE 5001

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-5001}"]
