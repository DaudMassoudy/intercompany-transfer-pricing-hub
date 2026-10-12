# One-click Launcher Architecture
START_DEMO.bat validates Docker, provisions `.env`, builds/starts Docker Compose, waits for API health, imports versioned n8n workflow JSON, then opens the browser. Persistent volumes are preserved in normal mode.
