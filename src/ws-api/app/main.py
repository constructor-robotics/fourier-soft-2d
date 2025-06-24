from fastapi import FastAPI
from app.routers import items, services
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Fourier SOFT API", version="1.0.0")

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Include routers
#app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(services.router, prefix="/services", tags=["services"])