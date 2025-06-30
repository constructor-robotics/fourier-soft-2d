import requests
import json
import time
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8090"
SERVICES_ENDPOINT = f"{API_BASE_URL}/services"


def run_fourier_registration(image1_path, image2_path, dimensions=512, debug=False):
    """
    Execute fourier-soft2d registration on two images
    
    Args:
        image1_path: Path to first image (relative to /input directory)
        image2_path: Path to second image (relative to /input directory)
        dimensions: Image dimensions for processing (must be power of 2)
        debug: Enable debug mode for additional outputs
    
    Returns:
        Dictionary with registration results
    """
    
    # Prepare request payload
    payload = {
        "image1_path": image1_path,
        "image2_path": image2_path,
        "dimensions": dimensions,
        "debug": debug
    }
    
    # Make API request
    response = requests.post(
        f"{SERVICES_ENDPOINT}/fourier-soft2d",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Registration successful!")
        print(f"Solution index: {result.get('solution_index')}")
        print(f"Execution time: {result.get('execution_time'):.2f}s")
        return result
    else:
        print(f"Registration failed: {response.status_code}")
        print(f"Error: {response.text}")
        return None

# Example usage
if __name__ == "__main__":
    result = run_fourier_registration(
        image1_path="experiment1/image_001.png",
        image2_path="experiment1/image_002.png",
        dimensions=512,
        debug=True
    )