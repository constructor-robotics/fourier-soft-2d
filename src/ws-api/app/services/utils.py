"""
File: utils.py
Description: Utility functions for sequential batch processing operations
Author: Arturo Gomez-Chavez
Creation Date: 30.06.2025
Institution/Organization: Constructor University GmbH
Contributors/Editors:
License: MIT License - See LICENSE.MD file for details
Contact & Support:
- Email: [support@example.com]
"""

"""
Utility functions for sequential batch processing operations
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def detect_numbered_images(directory: str, base_pattern: str, image_format: str) -> Dict[str, any]:
    """
    Detect numbered image files matching the pattern and format
    
    Args:
        directory: Directory path relative to /workspace/input
        base_pattern: Base pattern (e.g., 'image_', 'frame_')
        image_format: Image format without dot (e.g., 'png', 'jpg')
    
    Returns:
        Dictionary with detected images info
    """
    full_path = Path("/workspace/input") / directory
    if not full_path.exists():
        raise FileNotFoundError(f"Directory not found: {full_path}")
    
    # Create regex pattern to match numbered files
    # Pattern matches: base_pattern + digits + .format
    pattern = rf"^{re.escape(base_pattern)}(\d+)\.{re.escape(image_format)}$"
    regex = re.compile(pattern)
    
    detected_files = {}
    
    # Scan directory for matching files
    for file_path in full_path.iterdir():
        if file_path.is_file():
            match = regex.match(file_path.name)
            if match:
                index = int(match.group(1))
                relative_path = str(Path(directory) / file_path.name)
                detected_files[index] = relative_path
    
    if not detected_files:
        raise FileNotFoundError(
            f"No images found matching pattern '{base_pattern}***.{image_format}' in {directory}"
        )
    
    # Sort by index
    sorted_indices = sorted(detected_files.keys())
    min_index = min(sorted_indices)
    max_index = max(sorted_indices)
    
    # Check for gaps in sequence
    missing_indices = []
    for i in range(min_index, max_index + 1):
        if i not in detected_files:
            missing_indices.append(i)
    
    result = {
        "detected_files": detected_files,
        "sorted_indices": sorted_indices,
        "min_index": min_index,
        "max_index": max_index,
        "total_files": len(detected_files),
        "missing_indices": missing_indices,
        "has_gaps": len(missing_indices) > 0,
        "pattern_info": {
            "base_pattern": base_pattern,
            "image_format": image_format,
            "full_pattern": f"{base_pattern}***.{image_format}"
        }
    }
    
    logger.info(f"Detected {len(detected_files)} images: indices {min_index}-{max_index}")
    if missing_indices:
        logger.warning(f"Missing indices in sequence: {missing_indices}")
    
    return result

def create_sequential_pairs(
    detected_info: Dict[str, any], 
    start_index: Optional[int] = None, 
    end_index: Optional[int] = None
) -> List[Tuple[str, str, int, int]]:
    """
    Create sequential image pairs from detected images
    
    Args:
        detected_info: Result from detect_numbered_images
        start_index: Starting index (use detected min if None)
        end_index: Ending index (use detected max if None)
    
    Returns:
        List of tuples: (img1_path, img2_path, img1_index, img2_index)
    """
    detected_files = detected_info["detected_files"]
    available_indices = detected_info["sorted_indices"]
    
    # Determine range
    actual_start = start_index if start_index is not None else detected_info["min_index"]
    actual_end = end_index if end_index is not None else detected_info["max_index"]
    
    # Validate range
    if actual_start < detected_info["min_index"]:
        raise ValueError(f"Start index {actual_start} is below minimum detected index {detected_info['min_index']}")
    if actual_end > detected_info["max_index"]:
        raise ValueError(f"End index {actual_end} is above maximum detected index {detected_info['max_index']}")
    
    # Filter available indices within range
    range_indices = [idx for idx in available_indices if actual_start <= idx <= actual_end]
    
    if len(range_indices) < 2:
        raise ValueError(f"Not enough images in range {actual_start}-{actual_end}. Found: {len(range_indices)}")
    
    # Create sequential pairs
    pairs = []
    for i in range(len(range_indices) - 1):
        idx1 = range_indices[i]
        idx2 = range_indices[i + 1]
        
        img1_path = detected_files[idx1]
        img2_path = detected_files[idx2]
        
        pairs.append((img1_path, img2_path, idx1, idx2))
    
    logger.info(f"Created {len(pairs)} sequential pairs from indices {actual_start} to {actual_end}")
    return pairs

def generate_sequential_pair_id(base_pattern: str, idx1: int, idx2: int) -> str:
    """
    Generate a pair ID for sequential processing
    
    Args:
        base_pattern: Base pattern used
        idx1: First image index
        idx2: Second image index
    
    Returns:
        Unique pair identifier
    """
    clean_pattern = base_pattern.rstrip('_').replace('_', '')
    return f"{clean_pattern}_{idx1:03d}_to_{idx2:03d}"

def find_csv_result_dir_for_pair(
    pair_id: str, 
    base_results_dir: Optional[str] = None,
    idx1: int = None,
    idx2: int = None
) -> Optional[str]:
    """
    Find the CSV result directory for a specific sequential image pair
    
    Args:
        pair_id: Unique pair identifier
        base_results_dir: Base directory to search in
        idx1: First image index
        idx2: Second image index
    
    Returns:
        Path to directory containing CSV results for the pair
    """
    if base_results_dir:
        # Look for specific subdirectory for this pair
        search_dir = Path("/workspace/output") / base_results_dir
        if search_dir.exists():
            # Try to find subdirectory with pair ID or indices
            possible_dirs = [
                search_dir / pair_id,
                search_dir / f"{base_results_dir}_{pair_id}",
            ]
            
            for dir_path in possible_dirs:
                if dir_path.exists() and dir_path.is_dir():
                    return str(dir_path)
            
            # If no specific subdirectory found, return base directory
            return str(search_dir)
    else:
        # Look in latest timestamped directory
        output_dir = Path("/workspace/output")
        if output_dir.exists():
            # Find directories that might contain results
            subdirs = [d for d in output_dir.iterdir() if d.is_dir()]
            if subdirs:
                # Return the most recent directory (assuming timestamp naming)
                latest_dir = max(subdirs, key=lambda x: x.stat().st_mtime)
                return str(latest_dir)
    
    return None

def validate_workspace_directories():
    """
    Validate that required workspace directories exist
    """
    required_dirs = [
        "/workspace/input",
        "/workspace/output"
    ]
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            raise FileNotFoundError(f"Required workspace directory not found: {dir_path}")
    
    logger.info("Workspace directories validated successfully")

def get_sequence_summary(detected_info: Dict[str, any]) -> str:
    """
    Generate a human-readable summary of the detected image sequence
    """
    info = detected_info
    summary_parts = [
        f"Found {info['total_files']} images",
        f"Range: {info['min_index']}-{info['max_index']}",
        f"Pattern: {info['pattern_info']['full_pattern']}"
    ]
    
    if info['has_gaps']:
        summary_parts.append(f"Missing: {info['missing_indices']}")
    
    return " | ".join(summary_parts)
