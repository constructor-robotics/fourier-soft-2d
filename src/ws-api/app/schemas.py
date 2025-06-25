from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class ServiceResponse(BaseModel):
    success: bool
    message: str
    logs_output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

class FourierSoft2DResponse(BaseModel):
    success: bool
    message: str
    solution_index: Optional[int] = None  # Best solution index
    logs_output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

# Fourier Soft 2D Schemas
class FourierSoft2DRequest(BaseModel):
    image1_path: str  # Path to first image
    image2_path: str  # Path to second image
    output_dir: Optional[str] = None  # Optional output directory name
    dimensions: Optional[int] = None  # Image dimensions (must be power of 2)
    debug: Optional[bool] = False  # Enable debug mode

# Image Stitching Schemas
class ImageStitchingRequest(BaseModel):
    image1_path: str  # Path to first image relative to /workspace/input
    image2_path: str  # Path to second image relative to /workspace/input
    csv_dir_path: Optional[str] = None  # Path to directory containing CSV file
    solution_index: Optional[int] = 0  # Solution index (default: 0)
    inverse: Optional[bool] = False  # Apply inverse transformation
    adjust_canvas: Optional[bool] = False  # Adjust canvas size

    #New scalinng functionality
    doscale: Optional[bool] = False  # Enable scaling compensation (default: false)
    sx: Optional[float] = None  # Manual scaling factor in x direction (optional)
    sy: Optional[float] = None  # Manual scaling factor in y direction (optional)

# Plot Registration Solution Schemas
class PlotRegistrationRequest(BaseModel):
    folder_name: Optional[str] = None  # Folder name under /workspace/output

# Health check response
class HealthCheckResponse(BaseModel):
    status: str
    executables: dict
    timestamp: Optional[str] = None