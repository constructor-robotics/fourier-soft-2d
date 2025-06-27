from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum

class ServiceResponse(BaseModel):
    success: bool
    message: str
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

class FourierSoft2DResponse(BaseModel):
    success: bool
    message: str
    solution_index: Optional[int] = None  # Best solution index
    logs_output: Optional[str] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


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

### --- BATCH SERVICES --- ###
class BatchResult(BaseModel):
    pair_id: str
    image1_path: str
    image2_path: str
    image1_index: int
    image2_index: int
    success: bool
    message: str
    output_dir: Optional[str] = None
    solution_index: Optional[int] = None
    execution_time: Optional[float] = None
    error: Optional[str] = None

class BatchFourierSoft2DRequest(BaseModel):
    input_directory: str  # Directory containing image files (relative to /workspace/input)
    output_dir: str  # Output directory name (will be created under /workspace/output)
    base_pattern: str  # Base pattern of image names (e.g., 'image_', 'frame_', 'slice_')
    image_format: str  # Image format/extension (e.g., 'png', 'jpg', 'tiff')
    dimensions: int  # Image dimensions (must be power of 2) - REQUIRED for batch processing
    start_index: Optional[int] = None  # Starting image index (auto-detect if not provided)
    end_index: Optional[int] = None    # Ending image index (auto-detect if not provided)
    max_concurrent: Optional[int] = 3  # Maximum concurrent processes

class BatchFourierSoft2DResponse(BaseModel):
    success: bool
    message: str
    total_pairs: int
    successful_pairs: int
    failed_pairs: int
    output_dir: str  # Final output directory containing merged results
    merged_csv_path: Optional[str] = None  # Path to batch_registration_solutions.csv
    merged_logs_csv_path: Optional[str] = None  # Path to batch_experiment_task_logs.csv
    results: List[BatchResult]
    total_execution_time: float
    image_sequence_info: Optional[Dict[str, Any]] = None
    logs_output: Optional[str] = None

### --- HEALTH CHECK --- ###

# Health check response
class HealthCheckResponse(BaseModel):
    status: str
    executables: dict
    timestamp: Optional[str] = None