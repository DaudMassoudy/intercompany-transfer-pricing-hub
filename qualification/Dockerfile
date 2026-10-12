FROM mcr.microsoft.com/playwright:v1.55.0-noble
USER root
RUN apt-get update && apt-get install -y --no-install-recommends socat curl ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /qualification
COPY qualification/package.json ./
RUN npm install --no-audit --no-fund
COPY qualification/playwright.config.ts ./
COPY qualification/tests ./tests
COPY qualification/entrypoint.sh ./
COPY sample_data ./sample_data
RUN chmod +x entrypoint.sh && mkdir -p /qualification/results
ENTRYPOINT ["/qualification/entrypoint.sh"]
