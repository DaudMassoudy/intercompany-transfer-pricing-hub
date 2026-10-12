FROM python:3.12.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN groupadd -r otp && useradd -r -g otp -d /app otp
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN chmod +x start.sh && mkdir -p /data/uploads && chown -R otp:otp /app /data
USER otp
EXPOSE 8000
CMD ["./start.sh"]
