import subprocess
import asyncio
import time
import logging
from pathlib import Path
from typing import Dict, Any, List
import json

logger = logging.getLogger(__name__)

class WorkspaceServiceExecutor:
    def __init__(self):
        # Define paths to your executables in /workspace
        self.fourier_soft2d = "/workspace/fourier_soft2D"
        self.image_stitching = "/workspace/imageStitching.py"
        self.plot_registration = "/workspace/plotRegistrationSolution.py"
        self.workspace_input = "/workspace/input"
        self.workspace_output = "/workspace/output"

        # Enhanced directory structure
        self.workspace_output_individual = "/workspace/output/individual_runs"
        self.workspace_output_batch = "/workspace/output/batch_runs"
        self.workspace_output_stitching = "/workspace/output/stitching_results"
        
        # Ensure directories exist
        Path(self.workspace_output_individual).mkdir(parents=True, exist_ok=True)
        Path(self.workspace_output_batch).mkdir(parents=True, exist_ok=True)
        Path(self.workspace_output_stitching).mkdir(parents=True, exist_ok=True)
    
    def _build_fourier_command(self, request) -> List[str]:
        """Build command for fourier_soft2D executable"""
        cmd = [self.fourier_soft2d, request.image1_path, request.image2_path]
        
        if request.output_dir:
            cmd.extend(["--output-dir", request.output_dir])
        
        if request.dimensions:
            cmd.extend(["--dimensions", str(request.dimensions)])
        
        if request.debug:
            cmd.extend(["--debug", "true"])
        
        return cmd
    
    def _build_image_stitching_command(self, request) -> List[str]:
        """Build command for imageStitching.py script"""
        cmd = ["python3", self.image_stitching, request.image1_path, request.image2_path]
        
        if request.csv_dir_path:
            cmd.extend(["--csv_dir_path", request.csv_dir_path])
        if request.solution_index is not None:
            cmd.extend(["--solution_index", str(request.solution_index)])
        if request.inverse:
            cmd.append("--inverse")
        if request.adjust_canvas:
            cmd.append("--adjust-canvas")
        
        # New scaling functionality
        if request.doscale:
            cmd.append("--doscale")
            
            # Add manual scaling factors if provided
            if request.sx is not None:
                cmd.extend(["--sx", str(request.sx)])
            if request.sy is not None:
                cmd.extend(["--sy", str(request.sy)])
        
        return cmd
    
    def _build_plot_registration_command(self, request) -> List[str]:
        """Build command for plotRegistrationSolution.py script"""
        cmd = ["python3", self.plot_registration]
        
        if request.folder_name:
            cmd.append(request.folder_name)
        
        return cmd
    
    async def _execute_command(self, cmd: List[str], service_name: str) -> Dict[str, Any]:
        """Generic command executor"""
        try:
            start_time = time.time()
            logger.info(f"Executing {service_name}: {' '.join(cmd)}")
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/workspace"  # Set working directory to /workspace
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            stdout_str = stdout.decode().strip()
            stderr_str = stderr.decode().strip()
            
            if process.returncode == 0:
                if service_name == "Fourier Soft 2D":
                    try:
                        # Get the last line and try to parse it as JSON
                        lines = stdout_str.strip().split('\n')
                        last_line = lines[-1] if lines else ""
                        result = json.loads(last_line)
                        solution_index = int(result["solution_index"])

                        return {
                            "success": True,
                            "message": f"{service_name} executed successfully",
                            "solution_index": solution_index,
                            "logs_output": stdout_str,
                            "execution_time": execution_time
                        }
                    except (json.JSONDecodeError, KeyError, IndexError):
                        return {
                            "success": False,
                            "message": "Could not parse JSON result",
                            "solution_index": None,
                            "logs_output": stdout_str if stdout_str else None,
                            "execution_time": execution_time
                        }
                else:
                    return {
                        "success": True,
                        "message": f"{service_name} executed successfully",
                        "logs_output": stdout_str if stdout_str else None,
                        "execution_time": execution_time
                    }
            else:
                return {
                    "success": False,
                    "message": f"{service_name} failed with return code {process.returncode}",
                    "error": stderr_str,
                    "logs output": stdout_str if stdout_str else None,
                    "execution_time": execution_time
                }
                
        except Exception as e:
            logger.error(f"Error executing {service_name}: {str(e)}")
            return {
                "success": False,
                "message": f"Failed to execute {service_name}",
                "error": str(e)
            }
    
    async def run_fourier_soft2d(self, request) -> Dict[str, Any]:
        """Execute fourier_soft2D with parameters"""
        cmd = self._build_fourier_command(request)
        return await self._execute_command(cmd, "Fourier Soft 2D")
    
    async def run_image_stitching(self, request) -> Dict[str, Any]:
        """Execute imageStitching.py with parameters"""
        cmd = self._build_image_stitching_command(request)
        return await self._execute_command(cmd, "Image Stitching")
    
    async def run_plot_registration(self, request) -> Dict[str, Any]:
        """Execute plotRegistrationSolution.py with parameters"""
        cmd = self._build_plot_registration_command(request)
        return await self._execute_command(cmd, "Plot Registration Solution")
    
    def check_executables(self) -> Dict[str, Any]:
        """Check if all executables exist and are accessible"""
        executables = {
            "fourier_soft2d": self.fourier_soft2d,
            "image_stitching": self.image_stitching,
            "plot_registration": self.plot_registration
        }
        
        status = {}
        for name, path in executables.items():
            file_path = Path(path)
            exists = file_path.is_file()
            
            if name == "fourier_soft2d":
                # Check if C++ executable has execute permissions
                executable = file_path.stat().st_mode & 0o111 != 0 if exists else False
                status[name] = {
                    "path": path,
                    "exists": exists,
                    "executable": executable
                }
            else:
                # For Python scripts, check if readable
                status[name] = {
                    "path": path,
                    "exists": exists,
                    "readable": exists
                }
        
        # Check workspace directories
        status["workspace_input"] = {
            "path": self.workspace_input,
            "exists": Path(self.workspace_input).is_dir()
        }
        status["workspace_output"] = {
            "path": self.workspace_output,
            "exists": Path(self.workspace_output).is_dir()
        }
        
        return status
    
    def _generate_run_id(self, prefix="run"):
        """Generate timestamped run ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}"
    
    def _build_enhanced_fourier_command(self, request, run_context=None):
        """Enhanced fourier command builder with proper output directory"""
        cmd = [self.fourier_soft2d, request.image1_path, request.image2_path]
        
        if run_context:
            # Batch processing - use structured directory
            if run_context["type"] == "batch":
                output_dir = f"{run_context['batch_id']}/{run_context['pair_id']}"
                full_output_path = Path(self.workspace_output_batch) / output_dir
            else:
                # Individual processing
                output_dir = run_context.get("run_id", self._generate_run_id())
                full_output_path = Path(self.workspace_output_individual) / output_dir
        else:
            # Legacy individual processing
            if request.output_dir:
                output_dir = f"{request.output_dir}_{self._generate_run_id()}"
            else:
                output_dir = self._generate_run_id()
            full_output_path = Path(self.workspace_output_individual) / output_dir
        
        # Ensure output directory exists
        full_output_path.mkdir(parents=True, exist_ok=True)
        
        # Pass relative path to C++ program
        cmd.extend(["--output-dir", str(full_output_path.relative_to("/workspace/output"))])
        
        if request.dimensions:
            cmd.extend(["--dimensions", str(request.dimensions)])
        if request.debug:
            cmd.extend(["--debug", "true"])
        
        return cmd, str(full_output_path)

    def save_batch_metadata(self, batch_id, request_params, results):
        """Save batch processing metadata"""
        metadata = {
            "batch_id": batch_id,
            "created_at": datetime.now().isoformat(),
            "request_parameters": request_params,
            "processing_results": {
                "total_pairs": len(results),
                "successful_pairs": sum(1 for r in results if r.get("success", False)),
                "failed_pairs": sum(1 for r in results if not r.get("success", False))
            },
            "pair_results": results
        }
        
        metadata_file = Path(self.workspace_output_batch) / batch_id / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return metadata_file