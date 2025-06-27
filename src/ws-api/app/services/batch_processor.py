"""
Focused batch processing service for sequential fourier-soft2d operations
"""

import asyncio
import time
import logging
import pandas as pd
import shutil
import uuid
from typing import List, Dict, Any, Tuple
from pathlib import Path

from app.schemas import (
    BatchFourierSoft2DRequest, 
    BatchFourierSoft2DResponse,
    BatchResult,
    FourierSoft2DRequest
)
from app.services.executor import WorkspaceServiceExecutor
from app.services.utils import (
    detect_numbered_images,
    create_sequential_pairs, 
    generate_sequential_pair_id,
    validate_workspace_directories,
    get_sequence_summary
)

logger = logging.getLogger(__name__)

class BatchProcessor:
    def __init__(self):
        self.executor = WorkspaceServiceExecutor()
    
    async def process_batch_fourier_soft2d(self, request: BatchFourierSoft2DRequest) -> Dict[str, Any]:
        """
        Process sequential image pairs through fourier-soft2d with UUID-based CSV merging
        
        Args:
            request: Batch processing request parameters
            
        Returns:
            Dictionary containing batch processing results with merged CSVs
        """
        start_time = time.time()
        
        try:
            # Validate workspace
            validate_workspace_directories()
            
            # Create main output directory
            main_output_dir = Path("/workspace/output") / request.output_dir
            if main_output_dir.exists():
                logger.warning(f"Output directory {main_output_dir} already exists, contents may be overwritten")
            main_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Detect numbered images
            detected_info = detect_numbered_images(
                request.input_directory, 
                request.base_pattern, 
                request.image_format
            )
            
            sequence_summary = get_sequence_summary(detected_info)
            logger.info(f"Image sequence detected: {sequence_summary}")
            
            # Create sequential pairs
            image_pairs = create_sequential_pairs(
                detected_info, 
                request.start_index, 
                request.end_index
            )
            
            logger.info(f"Starting batch processing of {len(image_pairs)} pairs with dimensions {request.dimensions}")
            
            # Process pairs with concurrency control
            semaphore = asyncio.Semaphore(request.max_concurrent)
            tasks = []
            
            for img1_path, img2_path, idx1, idx2 in image_pairs:
                task = self._process_single_fourier_pair(
                    semaphore, img1_path, img2_path, idx1, idx2, request, main_output_dir
                )
                tasks.append(task)
            
            # Execute all tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            batch_results = []
            successful_pairs = 0
            failed_pairs = 0
            temp_directories = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle exceptions
                    _, _, idx1, idx2 = image_pairs[i]
                    pair_id = generate_sequential_pair_id(request.base_pattern, idx1, idx2)
                    batch_result = BatchResult(
                        pair_id=pair_id,
                        image1_path=image_pairs[i][0],
                        image2_path=image_pairs[i][1],
                        image1_index=idx1,
                        image2_index=idx2,
                        success=False,
                        message="Exception occurred during processing",
                        error=str(result)
                    )
                    failed_pairs += 1
                else:
                    batch_result = BatchResult(**result)
                    if batch_result.success:
                        successful_pairs += 1
                        # Track temporary directory for later CSV merging
                        temp_directories.append(result["temp_output_dir"])
                    else:
                        failed_pairs += 1
                
                batch_results.append(batch_result)
            
            # Merge CSV files if we have successful results
            merged_csv_paths = {}
            if successful_pairs > 0:
                try:
                    merged_csv_paths = await self._merge_csv_files(
                        temp_directories, main_output_dir
                    )
                    logger.info(f"Successfully merged CSV files from {successful_pairs} pairs")
                    
                    # Clean up temporary directories
                    await self._cleanup_temp_directories(temp_directories)
                    logger.info(f"Cleaned up {len(temp_directories)} temporary directories")
                    
                except Exception as e:
                    logger.error(f"Failed to merge CSV files: {str(e)}")
                    # Don't fail the entire batch if CSV merging fails
            
            total_execution_time = time.time() - start_time
            
            return {
                "success": True,
                "message": f"Batch processing completed. {successful_pairs}/{len(image_pairs)} pairs successful",
                "total_pairs": len(image_pairs),
                "successful_pairs": successful_pairs,
                "failed_pairs": failed_pairs,
                "output_dir": str(main_output_dir),
                "merged_csv_path": merged_csv_paths.get("registration_solutions", None),
                "merged_logs_csv_path": merged_csv_paths.get("experiment_logs", None),
                "results": [result.dict() for result in batch_results],
                "total_execution_time": total_execution_time,
                "image_sequence_info": {
                    "sequence_summary": sequence_summary,
                    "detected_range": f"{detected_info['min_index']}-{detected_info['max_index']}",
                    "processed_range": f"{request.start_index or detected_info['min_index']}-{request.end_index or detected_info['max_index']}",
                    "total_detected": detected_info['total_files'],
                    "missing_indices": detected_info['missing_indices'] if detected_info['has_gaps'] else None
                }
            }
            
        except Exception as e:
            logger.error(f"Batch fourier processing failed: {str(e)}")
            return {
                "success": False,
                "message": f"Batch processing failed: {str(e)}",
                "total_pairs": 0,
                "successful_pairs": 0,
                "failed_pairs": 0,
                "output_dir": str(main_output_dir) if 'main_output_dir' in locals() else None,
                "merged_csv_path": None,
                "merged_logs_csv_path": None,
                "results": [],
                "total_execution_time": time.time() - start_time,
                "image_sequence_info": None
            }
    
    async def _process_single_fourier_pair(
        self, 
        semaphore: asyncio.Semaphore, 
        img1_path: str, 
        img2_path: str,
        idx1: int,
        idx2: int,
        batch_request: BatchFourierSoft2DRequest,
        main_output_dir: Path
    ) -> Dict[str, Any]:
        """Process a single sequential image pair through fourier-soft2d with UUID"""
        
        async with semaphore:
            pair_id = generate_sequential_pair_id(batch_request.base_pattern, idx1, idx2)
            pair_start_time = time.time()
            
            # Generate UUID for this individual run
            run_uuid = str(uuid.uuid4())
            
            # Create temporary output directory for this pair
            temp_output_dir = main_output_dir / f"temp_{pair_id}"
            
            try:
                # Create individual fourier request with ENFORCED debug=False
                fourier_request = FourierSoft2DRequest(
                    image1_path=img1_path,
                    image2_path=img2_path,
                    output_dir=str(temp_output_dir.relative_to("/workspace/output")),
                    dimensions=batch_request.dimensions,  # REQUIRED parameter
                    debug=False  # ENFORCED as False for batch processing
                )
                
                logger.info(f"Processing pair {pair_id} with UUID {run_uuid} and dimensions {batch_request.dimensions}")
                
                # Execute fourier-soft2d
                result = await self.executor.run_fourier_soft2d(fourier_request)
                
                # Add UUID and indices to the generated CSV files
                if result["success"]:
                    await self._add_uuid_to_csv_files(temp_output_dir, run_uuid, idx1, idx2)
                
                return {
                    "pair_id": pair_id,
                    "image1_path": img1_path,
                    "image2_path": img2_path,
                    "image1_index": idx1,
                    "image2_index": idx2,
                    "success": result["success"],
                    "message": result["message"],
                    "temp_output_dir": str(temp_output_dir),  # For CSV merging
                    "run_uuid": run_uuid,
                    "solution_index": result.get("solution_index"),
                    "execution_time": time.time() - pair_start_time,
                    "error": result.get("error")
                }
                
            except Exception as e:
                return {
                    "pair_id": pair_id,
                    "image1_path": img1_path,
                    "image2_path": img2_path,
                    "image1_index": idx1,
                    "image2_index": idx2,
                    "success": False,
                    "message": f"Failed to process pair {pair_id}",
                    "temp_output_dir": str(temp_output_dir),
                    "run_uuid": run_uuid,
                    "execution_time": time.time() - pair_start_time,
                    "error": str(e)
                }
        
    async def _add_uuid_to_csv_files(self, temp_output_dir: Path, run_uuid: str, idx1: int, idx2: int):
        """
        Add UUID and image indices to CSV files for proper sorting and tracking
        
        Args:
            temp_output_dir: Directory containing the CSV files
            run_uuid: UUID to add to both files
            idx1: First image index
            idx2: Second image index
        """
        csv_files = [
            "registration_solutions_transformation.csv",
            "experiment_task_logs.csv"
        ]
        
        for csv_filename in csv_files:
            csv_file = temp_output_dir / csv_filename
            if csv_file.exists():
                try:
                    # Read CSV
                    df = pd.read_csv(csv_file)
                    
                    # Add tracking columns in logical order
                    df.insert(0, 'uuid', run_uuid)
                    df.insert(1, 'image1_index', idx1)
                    df.insert(2, 'image2_index', idx2)
                    df.insert(3, 'pair_id', f"{idx1:03d}_to_{idx2:03d}")  # For readability
                    
                    # Save back to file
                    df.to_csv(csv_file, index=False)
                    logger.debug(f"Added UUID {run_uuid} and indices to {csv_file}")
                    
                except Exception as e:
                    logger.warning(f"Failed to add UUID to {csv_file}: {str(e)}")
            else:
                logger.warning(f"CSV file not found: {csv_file}")

    async def _merge_csv_files(
        self, 
        temp_directories: List[str], 
        main_output_dir: Path
    ) -> Dict[str, Path]:
        """
        Merge CSV files with logical sorting by image indices
        """
        logger.info(f"Merging CSV files from {len(temp_directories)} directories")
        
        csv_types = {
            "registration_solutions_transformation.csv": {
                "dataframes": [],
                "output_name": "batch_registration_solutions.csv"
            },
            "experiment_task_logs.csv": {
                "dataframes": [],
                "output_name": "batch_experiment_task_logs.csv"
            }
        }
        
        # Collect all CSV files by type
        for temp_dir_str in temp_directories:
            temp_dir = Path(temp_dir_str)
            
            for csv_filename, csv_info in csv_types.items():
                csv_file = temp_dir / csv_filename
                
                if csv_file.exists():
                    try:
                        # Read CSV (UUID and index columns should be present)
                        df = pd.read_csv(csv_file)
                        csv_info["dataframes"].append(df)
                        logger.debug(f"Added {csv_filename} from {csv_file} with {len(df)} rows")
                        
                    except Exception as e:
                        logger.warning(f"Failed to read {csv_filename} from {csv_file}: {str(e)}")
                        continue
                else:
                    logger.warning(f"CSV file not found: {csv_file}")
        
        # Merge and save each CSV type
        merged_paths = {}
        
        for csv_filename, csv_info in csv_types.items():
            if not csv_info["dataframes"]:
                logger.warning(f"No valid {csv_filename} files found to merge")
                continue
            
            try:
                # Concatenate all dataframes
                merged_df = pd.concat(csv_info["dataframes"], ignore_index=True)
                
                # Sort by image indices for logical sequential order
                merged_df = merged_df.sort_values(['image1_index', 'image2_index'])
                
                # Save merged CSV
                output_path = main_output_dir / csv_info["output_name"]
                merged_df.to_csv(output_path, index=False)
                
                merged_paths[csv_filename.split('.')[0].replace('_', '_')] = output_path
                logger.info(f"Merged {csv_info['output_name']} saved with {len(merged_df)} total rows (sorted by image indices)")
                
            except Exception as e:
                logger.error(f"Failed to merge {csv_filename}: {str(e)}")
                continue
        
        return merged_paths
    
    async def _cleanup_temp_directories(self, temp_directories: List[str]):
        """
        Clean up temporary directories after CSV merging
        
        Args:
            temp_directories: List of temporary directory paths to remove
        """
        for temp_dir_str in temp_directories:
            temp_dir = Path(temp_dir_str)
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Removed temporary directory: {temp_dir}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary directory {temp_dir}: {str(e)}")
                    # Continue with other directories even if one fails