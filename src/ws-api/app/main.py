from fastapi import FastAPI
from app.routers import services
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fourier SOFT 2D API", 
    version="1.0.0",
    description="FastAPI service for image registration with Fourier Soft 2D and visualization tools"
)

@app.get("/")
def read_root():
    return {
        "message": "Workspace Fourier Soft 2D API", 
        "services": [
            "fourier-soft2d", 
            "image-stitching", 
            "plot-registration",
            "batch-fourier-soft2d",
            "batch-image-stitching"
        ]
    }

# Include routers
#app.include_router(items.router, prefix="/items", tags=["items"])
app.include_router(services.router, prefix="/services", tags=["services"])