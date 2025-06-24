import subprocess
import asyncio
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ServiceExecutor:
    def __init__(self):
        # Paths to executables
        self.cpp_executable = "/path/to/your/cpp_program"  # Update this path
        self.python_script = "/path/to/your/python_script.py"  # Update this path
    
    async def run_cpp_service(self, string_param: str, int_param: int) -> dict:
        """Execute C++ program with parameters"""
        try:
            start_time = time.time()
            
            # Build command with parameters
            cmd = [self.cpp_executable, string_param, str(int_param)]
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "C++ service executed successfully",
                    "output": stdout.decode().strip(),
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "message": "C++ service failed",
                    "error": stderr.decode().strip(),
                    "execution_time": execution_time
                }
                
        except Exception as e:
            logger.error(f"Error executing C++ service: {str(e)}")
            return {
                "success": False,
                "message": "Failed to execute C++ service",
                "error": str(e)
            }
    
    async def run_python_service(self, string_param: str, int_param: int) -> dict:
        """Execute Python script with parameters"""
        try:
            start_time = time.time()
            
            # Build command with parameters
            cmd = ["python3", self.python_script, string_param, str(int_param)]
            
            # Run the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time
            
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "Python service executed successfully",
                    "output": stdout.decode().strip(),
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "message": "Python service failed",
                    "error": stderr.decode().strip(),
                    "execution_time": execution_time
                }
                
        except Exception as e:
            logger.error(f"Error executing Python service: {str(e)}")
            return {
                "success": False,
                "message": "Failed to execute Python service",
                "error": str(e)
            }
    
    def check_executables(self) -> dict:
        """Check if executables exist and are accessible"""
        cpp_exists = Path(self.cpp_executable).is_file()
        python_exists = Path(self.python_script).is_file()
        
        return {
            "cpp_executable": {
                "path": self.cpp_executable,
                "exists": cpp_exists,
                "executable": Path(self.cpp_executable).stat().st_mode & 0o111 != 0 if cpp_exists else False
            },
            "python_script": {
                "path": self.python_script,
                "exists": python_exists,
                "readable": Path(self.python_script).is_file() if python_exists else False
            }
        }
