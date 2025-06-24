from fastapi import APIRouter, HTTPException
from app.schemas import (
    ServiceResponse, 
    FourierSoft2DRequest, 
    ImageStitchingRequest, 
    PlotRegistrationRequest
)
from app.services.executor import WorkspaceServiceExecutor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
executor = WorkspaceServiceExecutor()

@router.post("/fourier-soft2d", response_model=ServiceResponse)
async def run_fourier_soft2d(request: FourierSoft2DRequest):
    """
    Execute fourier_soft2D C++ program for image registration
    
    - **first_image**: Path to first image
    - **second_image**: Path to second image  
    - **output_dir**: Optional output directory name (default: current UNIX timestamp)
    - **dimensions**: Optional image dimensions (must be power of 2, default: auto-detect)
    - **debug**: Enable debug mode (default: false)
    """
    logger.info(f"Executing Fourier Soft 2D with images: {request.first_image}, {request.second_image}")
    
    result = await executor.run_fourier_soft2d(request)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    
    return ServiceResponse(**result)

@router.post("/image-stitching", response_model=ServiceResponse)
async def run_image_stitching(request: ImageStitchingRequest):
    """
    Execute imageStitching.py for image stitching operations
    
    - **image1_path**: Path to first image relative to /workspace/input
    - **image2_path**: Path to second image relative to /workspace/input
    - **csv_dir_path**: Optional path to directory containing CSV file
    - **solution_index**: Solution index (default: 0)
    - **inverse**: Apply inverse transformation (default: false)
    - **adjust_canvas**: Adjust canvas size to fit full transformation (default: false)
    """
    logger.info(f"Executing Image Stitching with images: {request.image1_path}, {request.image2_path}")
    
    result = await executor.run_image_stitching(request)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    
    return ServiceResponse(**result)

@router.post("/plot-registration", response_model=ServiceResponse)
async def run_plot_registration(request: PlotRegistrationRequest):
    """
    Execute plotRegistrationSolution.py for plotting registration solutions
    
    - **folder_name**: Optional name of folder under /workspace/output 
                      (if not provided, uses folder with latest UNIX timestamp)
    """
    folder_info = f" for folder: {request.folder_name}" if request.folder_name else " (latest folder)"
    logger.info(f"Executing Plot Registration Solution{folder_info}")
    
    result = await executor.run_plot_registration(request)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    
    return ServiceResponse(**result)

@router.get("/health")
async def check_workspace_health():
    """Check if all workspace executables and directories are accessible"""
    return executor.check_executables()