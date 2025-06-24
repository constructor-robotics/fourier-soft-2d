from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.schemas import ServiceRequest, ServiceResponse
from app.services.executor import ServiceExecutor
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
executor = ServiceExecutor()

@router.post("/cpp", response_model=ServiceResponse)
async def run_cpp_service(request: ServiceRequest):
    """Execute C++ program with string and int parameters"""
    logger.info(f"Executing C++ service with params: {request.string_param}, {request.int_param}")
    
    result = await executor.run_cpp_service(request.string_param, request.int_param)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    
    return ServiceResponse(**result)

@router.post("/python", response_model=ServiceResponse)
async def run_python_service(request: ServiceRequest):
    """Execute Python script with string and int parameters"""
    logger.info(f"Executing Python service with params: {request.string_param}, {request.int_param}")
    
    result = await executor.run_python_service(request.string_param, request.int_param)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result)
    
    return ServiceResponse(**result)

@router.post("/cpp/async")
async def run_cpp_service_async(request: ServiceRequest, background_tasks: BackgroundTasks):
    """Execute C++ program asynchronously (fire and forget)"""
    background_tasks.add_task(executor.run_cpp_service, request.string_param, request.int_param)
    return {"message": "C++ service started in background"}

@router.post("/python/async")
async def run_python_service_async(request: ServiceRequest, background_tasks: BackgroundTasks):
    """Execute Python script asynchronously (fire and forget)"""
    background_tasks.add_task(executor.run_python_service, request.string_param, request.int_param)
    return {"message": "Python service started in background"}

@router.get("/health")
async def check_services_health():
    """Check if both executables are accessible"""
    return executor.check_executables()
