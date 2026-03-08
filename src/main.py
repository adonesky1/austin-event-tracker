from fastapi import FastAPI

from src.config.settings import Settings

settings = Settings()

app = FastAPI(title="City Family Events Curator", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}
