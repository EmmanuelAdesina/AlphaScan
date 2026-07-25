"""AlphaScan FastAPI routes."""
from fastapi import FastAPI

app = FastAPI(title="AlphaScan API", version="0.5.1")


@app.get("/")
def root():
    return {"status": "ok", "service": "AlphaScan", "version": "0.5.1"}


@app.get("/health")
def health():
    return {"status": "healthy"}