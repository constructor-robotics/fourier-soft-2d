"""
File: batch_stitching_processor.py
Description: Batch image stitching processor for progressive image combination
Author: Arturo Gomez-Chavez
Creation Date: 30.06.2025
Institution/Organization: Constructor University GmbH
Contributors/Editors:
License: MIT License - See LICENSE.MD file for details
Contact & Support:
- Email: [support@example.com]
"""

"""
Batch image stitching processor for progressive image combination
"""

import asyncio
import time
import logging
import pandas as pd
import shutil
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from app.schemas import (
    BatchImageStitchingRequest,
    BatchImageStitchingResponse,
    BatchStitchingResult,
    ImageStitchingRequest
)
from app.services.executor import WorkspaceServiceExecutor

logger = logging.getLogger(__name__)

class BatchStitchingProcessor:
    def __init__(self):
        self.executor = WorkspaceServiceExecutor()
    
    async def process_batch_image_stitching(self, request: BatchImageStitchingRequest) -> Dict[str, Any]:
        """
        Process progressive image stitching using batch fourier results
        
        Args:
            request: Batch stitching request parameters
            
        Returns:
            Dictionary containing batch stitching results
        """
        start_time = time.time()
        
        try:
            # Validate and load CSV files
            registration_dir = Path("/workspace/output") / request.registration_solution_dir
            if not registration_dir.exists():
                raise FileNotFoundError(f"Registration solution directory not found: {registration_dir}")
            
            task_logs_df, registration_df = await self._load_csv_files(registration_dir)
            
            # Calculate scaling factors once at the beginning
            scaling_factors = await self._calculate_scaling_factors(task_logs_df, request.doscale)
            logger.info(f"Calculated scaling factors: sx={scaling_factors['sx']}, sy={scaling_factors['sy']}")
            
            # Create debug directory
            debug_dir = registration_dir / "debug"
            debug_dir.mkdir(exist_ok=True)
            logger.info(f"Created debug directory: {debug_dir}")
            
            # Process progressive stitching
            stitching_results = []
            current_image_path = None  # Will store path to previous stitched result
            
            for iteration, (_, row) in enumerate(task_logs_df.iterrows(), 1):
                try:
                    result = await self._process_single_stitching_iteration(
                        iteration=iteration,
                        row=row,
                        current_image_path=current_image_path,
                        scaling_factors=scaling_factors,
                        debug_dir=debug_dir,
                        request=request,
                        is_first_pair=(iteration == 1),
                        is_last_pair=(iteration == len(task_logs_df))
                    )
                    
                    stitching_results.append(result)
                    
                    if result["success"]:
                        # Update current_image_path for next iteration
                        if iteration < len(task_logs_df):  # Not the last iteration
                            current_image_path = result["output_path"]
                        else:
                            # Last iteration - copy final result to main directory
                            final_image_path = await self._save_final_result(
                                result["output_path"], 
                                registration_dir, 
                                task_logs_df
                            )
                            result["final_image_path"] = final_image_path
                    else:
                        logger.error(f"Iteration {iteration} failed: {result['message']}")
                        logger.error(f"Error: {result['error']}")
                        break  # Stop on failure
                        
                except Exception as e:
                    logger.error(f"Exception in iteration {iteration}: {str(e)}")
                    error_result = {
                        "pair_id": f"iteration_{iteration}",
                        "iteration": iteration,
                        "image1_path": "unknown",
                        "image2_path": "unknown", 
                        "output_path": "none",
                        "success": False,
                        "message": f"Exception in iteration {iteration}",
                        "error": str(e),
                        "execution_time": 0,
                        "is_final_result": False
                    }
                    stitching_results.append(error_result)
                    break
            
            # Calculate summary statistics
            successful_iterations = sum(1 for r in stitching_results if r["success"])
            failed_iterations = len(stitching_results) - successful_iterations
            
            # Get final result info
            final_stitched_image = None
            if stitching_results and stitching_results[-1]["success"]:
                final_stitched_image = stitching_results[-1].get("final_image_path")
            
            # Clean up debug folder if not in debug mode
            debug_folder_path = None
            if request.debug:
                debug_folder_path = str(debug_dir)
                logger.info(f"Debug mode enabled - keeping debug folder: {debug_dir}")
            else:
                try:
                    shutil.rmtree(debug_dir)
                    logger.info(f"Cleaned up debug directory: {debug_dir}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup debug directory: {str(e)}")
            
            total_execution_time = time.time() - start_time
            
            return {
                "success": successful_iterations > 0,
                "message": f"Progressive stitching completed. {successful_iterations}/{len(task_logs_df)} iterations successful",
                "total_iterations": len(task_logs_df),
                "successful_iterations": successful_iterations,
                "failed_iterations": failed_iterations,
                "registration_solution_dir": str(registration_dir),
                "final_stitched_image": final_stitched_image,
                "debug_folder": debug_folder_path,
                "scaling_factors": scaling_factors,
                "results": stitching_results,
                "total_execution_time": total_execution_time,
                "processing_info": {
                    "total_pairs_processed": len(task_logs_df),
                    "doscale_enabled": request.doscale,
                    "inverse_enabled": request.inverse,
                    "debug_enabled": request.debug
                }
            }
            
        except Exception as e:
            logger.error(f"Batch stitching processing failed: {str(e)}")
            return {
                "success": False,
                "message": f"Batch stitching failed: {str(e)}",
                "total_iterations": 0,
                "successful_iterations": 0,
                "failed_iterations": 0,
                "registration_solution_dir": str(registration_dir) if 'registration_dir' in locals() else None,
                "final_stitched_image": None,
                "debug_folder": None,
                "scaling_factors": {"sx": 1.0, "sy": 1.0},
                "results": [],
                "total_execution_time": time.time() - start_time,
                "processing_info": None
            }
    
    async def _load_csv_files(self, registration_dir: Path) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load and validate the required CSV files"""
        
        task_logs_file = registration_dir / "batch_experiment_task_logs.csv"
        registration_file = registration_dir / "batch_registration_solutions.csv"
        
        if not task_logs_file.exists():
            raise FileNotFoundError(f"Required file not found: {task_logs_file}")
        if not registration_file.exists():
            raise FileNotFoundError(f"Required file not found: {registration_file}")
        
        try:
            task_logs_df = pd.read_csv(task_logs_file)
            registration_df = pd.read_csv(registration_file)
            
            logger.info(f"Loaded task logs: {len(task_logs_df)} rows")
            logger.info(f"Loaded registration solutions: {len(registration_df)} rows")
            
            # Validate required columns
            required_task_cols = ['first_image_name', 'second_image_name', 'best_solution_index', 
                                 'original_img1_width', 'original_img1_height', 'scaled_width', 'scaled_height']
            missing_cols = [col for col in required_task_cols if col not in task_logs_df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns in task logs: {missing_cols}")
            
            return task_logs_df, registration_df
            
        except Exception as e:
            raise ValueError(f"Failed to load CSV files: {str(e)}")
    
    async def _calculate_scaling_factors(self, task_logs_df: pd.DataFrame, doscale: bool) -> Dict[str, float]:
        """Calculate scaling factors from the first row of task logs"""
        
        if not doscale:
            return {"sx": 1.0, "sy": 1.0}
        
        # Use first row for scaling calculation
        first_row = task_logs_df.iloc[0]
        
        try:
            original_width = float(first_row['original_img1_width'])
            original_height = float(first_row['original_img1_height'])
            scaled_width = float(first_row['scaled_width'])
            scaled_height = float(first_row['scaled_height'])
            
            sx = original_width / scaled_width
            sy = original_height / scaled_height
            
            logger.info(f"Scaling calculation: {original_width}x{original_height} -> {scaled_width}x{scaled_height}")
            
            return {"sx": sx, "sy": sy}
            
        except Exception as e:
            logger.warning(f"Failed to calculate scaling factors: {str(e)}. Using defaults.")
            return {"sx": 1.0, "sy": 1.0}
    
    async def _process_single_stitching_iteration(
        self,
        iteration: int,
        row: pd.Series,
        current_image_path: Optional[str],
        scaling_factors: Dict[str, float],
        debug_dir: Path,
        request: BatchImageStitchingRequest,
        is_first_pair: bool,
        is_last_pair: bool
    ) -> Dict[str, Any]:
        """Process a single stitching iteration"""
        
        iteration_start_time = time.time()
        
        try:
            # Determine input images - In this case we always use full-paths
            if is_first_pair:
                # First iteration: use original images
                image1_path = '/workspace/input/' + row['first_image_name']
                image2_path = '/workspace/input/' + row['second_image_name']
            else:
                # Subsequent iterations: use previous result + next image
                image1_path = current_image_path
                image2_path = '/workspace/input/' + row['second_image_name']
            
            logger.info(f"Iteration {iteration}: Processing {image1_path} + {image2_path}")
            # Create pair-specific debug subdirectory
            pair_id = f"{iteration:03d}_iteration"
            pair_debug_dir = debug_dir / pair_id
            pair_debug_dir.mkdir(exist_ok=True)
            
            # Build stitching request
            stitching_request = ImageStitchingRequest(
                image1_path=image1_path,
                image2_path=image2_path,
                override_inputdir=True,
                csv_dir_path=str(debug_dir.parent) + "/batch_registration_solutions.csv",  # Points to registration_solution_dir
                subdir_output=str(pair_debug_dir),
                solution_index=int(row['best_solution_index']),
                inverse=request.inverse,
                adjust_canvas=True,  # Always true
                match_canvas=not is_first_pair,  # False for first pair, True for rest
                doscale=request.doscale,
                sx=scaling_factors['sx'],
                sy=scaling_factors['sy']
            )
            
            #logger.info(f"Iteration {iteration}: Processing {image1_path} + {image2_path}")
            logger.info(f"  - Solution index: {stitching_request.solution_index}")
            logger.info(f"  - Match canvas: {stitching_request.match_canvas}")
            logger.info(f"  - Scaling: sx={stitching_request.sx}, sy={stitching_request.sy}")
            
            # Execute image stitching
            result = await self.executor.run_image_stitching(stitching_request)
            #print(result)
            
            # Move output files to pair-specific directory
            output_path = None
            if result["success"]:
                output_path = result.get("result_image_path")
                logger.info(f"  - Result image: {output_path}")
                #output_path = await self._organize_output_files(pair_debug_dir, iteration)
            
            execution_time = time.time() - iteration_start_time
            
            return {
                "pair_id": pair_id,
                "iteration": iteration,
                "image1_path": image1_path,
                "image2_path": image2_path,
                "output_path": output_path,
                "success": result["success"],
                "message": result["message"],
                "execution_time": execution_time,
                "error": result.get("error"),
                "is_final_result": is_last_pair
            }
            
        except Exception as e:
            execution_time = time.time() - iteration_start_time
            return {
                "pair_id": f"{iteration:03d}_iteration",
                "iteration": iteration,
                "image1_path": current_image_path or "unknown",
                "image2_path": row.get('second_image_name', 'unknown'),
                "output_path": None,
                "success": False,
                "message": f"Failed to process iteration {iteration}",
                "execution_time": execution_time,
                "error": str(e),
                "is_final_result": is_last_pair
            }
    
    async def _organize_output_files(self, pair_debug_dir: Path, iteration: int) -> Optional[str]:
        """Move stitched output files to the pair-specific debug directory"""
        
        # Look for stitched output files in the main output directory
        output_dir = Path("/workspace/output")
        stitched_files = list(output_dir.glob("stitched_*"))
        
        if not stitched_files:
            logger.warning(f"No stitched output files found for iteration {iteration}")
            return None
        
        # Move files to pair debug directory
        moved_files = []
        for file_path in stitched_files:
            if file_path.is_file():
                dest_path = pair_debug_dir / file_path.name
                shutil.move(str(file_path), str(dest_path))
                moved_files.append(dest_path)
                logger.debug(f"Moved {file_path.name} to {dest_path}")
        
        # Return path to the main stitched result
        main_result = pair_debug_dir / "stitched_originals_blend.png"
        if main_result.exists():
            return str(main_result)
        
        # Fallback: return first moved file
        if moved_files:
            return str(moved_files[0])
        
        return None
    
    async def _save_final_result(
        self, 
        final_output_path: str, 
        registration_dir: Path, 
        task_logs_df: pd.DataFrame
    ) -> str:
        """Save the final stitched result to the main registration directory"""
        
        try:
            # Determine final filename
            first_row = task_logs_df.iloc[0]
            last_row = task_logs_df.iloc[-1]
            
            # Extract image indices/numbers from filenames
            first_name = Path(first_row['first_image_name']).stem
            last_name = Path(last_row['second_image_name']).stem
            
            # Extract numbers from image names (assuming pattern like image_001, frame_005, etc.)
            import re
            first_match = re.search(r'(\d+)', first_name)
            last_match = re.search(r'(\d+)', last_name)
            
            if first_match and last_match:
                first_idx = first_match.group(1)
                last_idx = last_match.group(1)
                final_filename = f"batch_registration_{first_idx}_to_{last_idx}_image_stitched.png"
            else:
                final_filename = "batch_registration_final_image_stitched.png"
            
            final_path = registration_dir / final_filename
            
            # Copy the final result
            shutil.copy2(final_output_path, final_path)
            logger.info(f"Saved final stitched result: {final_path}")
            
            return str(final_path)
            
        except Exception as e:
            logger.error(f"Failed to save final result: {str(e)}")
            return final_output_path