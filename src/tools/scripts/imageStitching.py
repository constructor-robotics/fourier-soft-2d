#!/usr/bin/env python3

"""
File: imageStitching.py
Description: [Brief description of the file's purpose]

Author: Arturo Gomez-Chavez
Creation Date: 30.06.2025
Institution/Organization: Constructor University GmbH

Contributors/Editors:

License: MIT License - See LICENSE.MD file for details

Contact & Support:
- Email: [support@example.com]
"""
"""
Enhanced Image Stitching Script with Scaling Support

New features:
- --doscale flag to enable scaling compensation
- --sx and --sy flags for manual scaling factors
- --match-canvas flag for handling pre-stitched images with larger canvas
- Automatic scaling factor extraction from experiment_task_logs.csv
- Scaling matrix application to transformation matrix
- Canvas matching and re-centering for reference image

Steps:
1. Load image 1 and image 2 from user input
2. If --match-canvas is true, resize reference image canvas to match transform image canvas
3. Read transformation matrix from CSV file
4. If --doscale is true, apply scaling compensation to transformation matrix
5. From transformation matrix:
   a. Extract rotation matrix and calculate angle
   b. Rotate image using cv2.warpAffine()
   c. Create translational affine_matrix from CSV values
   d. Apply translation to rotated image
   e. Result = transformed_image
6. Blend transformed_image with reference image (with and without colormaps)
"""

import numpy as np
import cv2
import pandas as pd
import argparse
from pathlib import Path
import json

def find_latest_output_directory(base_dir="/workspace/output"):
    """
    Find the directory with the latest unix timestamp name in the base directory.
    
    Args:
        base_dir (str): Base directory to search in
        
    Returns:
        Path: Path to the latest timestamped directory
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        raise ValueError(f"Base directory does not exist: {base_dir}")
    
    # Find all directories that look like unix timestamps (numeric names)
    timestamp_dirs = []
    for item in base_path.iterdir():
        if item.is_dir() and item.name.isdigit():
            timestamp_dirs.append((int(item.name), item))
    
    if not timestamp_dirs:
        raise ValueError(f"No timestamped directories found in {base_dir}")
    
    # Sort by timestamp and get the latest (highest number)
    timestamp_dirs.sort(key=lambda x: x[0], reverse=True)
    latest_timestamp, latest_dir = timestamp_dirs[0]
    
    print(f"Found latest timestamped directory: {latest_dir} (timestamp: {latest_timestamp})")
    
    return latest_dir

def determine_csv_path(csv_dir_path=None, base_dir="/workspace/output"):
    """
    Determine the CSV file path based on user input.
    
    Args:
        csv_dir_path (str): User provided CSV directory or file path (relative to base_dir)
        base_dir (str): Base directory for all operations
        
    Returns:
        Path: Full path to the CSV file
    """
    base_path = Path(base_dir)
    
    if not base_path.exists():
        raise ValueError(f"Base directory does not exist: {base_dir}")
    
    if csv_dir_path is None:
        # Case 3: No path given, find latest timestamped directory
        print("No CSV path specified, searching for latest timestamped directory...")
        csv_dir = find_latest_output_directory(base_dir)
        csv_file = csv_dir / 'registration_solutions_transformation.csv'
    else:
        # Convert to Path object relative to base_dir
        user_path = base_path / csv_dir_path
        
        if user_path.is_file() and user_path.suffix == '.csv':
            # Case 1: Specific CSV file provided
            print(f"Using specific CSV file: {user_path}")
            csv_file = user_path
        elif user_path.is_dir():
            # Case 2: Directory provided, look for expected CSV file
            print(f"Using directory: {user_path}")
            csv_file = user_path / 'registration_solutions_transformation.csv'
        else:
            # Try to interpret as directory path even if it doesn't exist yet
            print(f"Treating as directory path: {user_path}")
            csv_file = user_path / 'registration_solutions_transformation.csv'
    
    if not csv_file.exists():
        raise ValueError(f"CSV file not found: {csv_file}")
    
    print(f"Using CSV file: {csv_file}")
    return csv_file

def extract_scaling_factors_from_logs(output_dir, sx=None, sy=None, source_width=None, source_height=None):
    """
    Extract scaling factors from experiment_task_logs.csv or use provided values.
    
    Args:
        output_dir (Path): Output directory containing the logs
        sx (float): Manual scaling factor in x (optional)
        sy (float): Manual scaling factor in y (optional)
        
    Returns:
        tuple: (sx, sy) scaling factors
    """
    print("\n=== EXTRACTING SCALING FACTORS ===")
    
    if sx is not None and sy is not None:
        print(f"Using manually provided scaling factors: sx={sx}, sy={sy}")
        return sx, sy
    
    # Read from experiment_task_logs.csv
    logs_path = output_dir / 'experiment_task_logs.csv'
    
    if not logs_path.exists():
        raise ValueError(f"experiment_task_logs.csv not found in {output_dir}")
    
    print(f"Reading scaling factors from: {logs_path}")
    
    try:
        logs_df = pd.read_csv(logs_path)
        
        if len(logs_df) == 0:
            raise ValueError("experiment_task_logs.csv is empty")
        
        # Use the first (most recent) row
        row = logs_df.iloc[0]
        
        # original_width = row['original_img1_width']
        # original_height = row['original_img1_height']
        scaled_width = row['scaled_width']
        scaled_height = row['scaled_height']
        
        # Calculate scaling factors
        sx_calculated = source_width / scaled_width
        sy_calculated = source_height / scaled_height
        
        print(f"Original image size: {source_width}x{source_height}")
        print(f"Scaled image size: {scaled_width}x{scaled_height}")
        print(f"Calculated scaling factors: sx={sx_calculated:.4f}, sy={sy_calculated:.4f}")
        
        return sx_calculated, sy_calculated
        
    except Exception as e:
        raise ValueError(f"Error reading experiment_task_logs.csv: {e}")

def apply_scaling_to_transformation_matrix(transformation_matrix, sx, sy):
    """
    Apply scaling compensation to the transformation matrix.
    
    The scaling is applied to the important 3x3 section of the transformation matrix.
    This compensates for the difference in scale between the original images used for
    registration and the current input images.
    
    Args:
        transformation_matrix (np.ndarray): Original 4x4 transformation matrix
        sx (float): Scaling factor in x
        sy (float): Scaling factor in y
        
    Returns:
        np.ndarray: Scaled 4x4 transformation matrix
    """
    print(f"\n=== APPLYING SCALING TO TRANSFORMATION MATRIX ===")
    print(f"Scaling factors: sx={sx:.4f}, sy={sy:.4f}")
    
    # Create scaling matrix
    scaling_matrix = np.array([
        [sx,  0,  0, 0],
        [0,  sy,  0, 0],
        [0,   0,  1, 0],
        [0,   0,  0, 1]
    ])
    
    print("Scaling matrix:")
    print(scaling_matrix)
    
    print("Original transformation matrix:")
    print(transformation_matrix)
    
    # Apply scaling to the transformation matrix
    # The scaling affects the translation components and potentially rotation
    scaled_transformation_matrix = scaling_matrix @ transformation_matrix
    
    print("Scaled transformation matrix:")
    print(scaled_transformation_matrix)
    
    return scaled_transformation_matrix

def calculate_rotation_canvas_size(image_shape, rotation_angle_deg):
    """
    Calculate the canvas size needed to fit the entire rotated image.
    
    Args:
        image_shape (tuple): Original image shape (height, width)
        rotation_angle_deg (float): Rotation angle in degrees
        
    Returns:
        tuple: (canvas_width, canvas_height)
    """
    h, w = image_shape[:2]
    rotation_angle_rad = np.radians(rotation_angle_deg)
    
    # Calculate the corners of the original image
    corners = np.array([
        [0, 0],
        [w, 0],
        [w, h],
        [0, h]
    ])
    
    # Rotation matrix
    cos_angle = np.cos(rotation_angle_rad)
    sin_angle = np.sin(rotation_angle_rad)
    rotation_matrix_2x2 = np.array([
        [cos_angle, -sin_angle],
        [sin_angle, cos_angle]
    ])
    
    # Rotate corners around image center
    center = np.array([w/2, h/2])
    rotated_corners = []
    
    for corner in corners:
        # Translate to origin
        translated = corner - center
        # Rotate
        rotated = rotation_matrix_2x2 @ translated
        # Translate back
        final_corner = rotated + center
        rotated_corners.append(final_corner)
    
    rotated_corners = np.array(rotated_corners)
    
    # Find bounding box
    min_x = np.min(rotated_corners[:, 0])
    max_x = np.max(rotated_corners[:, 0])
    min_y = np.min(rotated_corners[:, 1])
    max_y = np.max(rotated_corners[:, 1])
    
    # Calculate required canvas size
    canvas_width = int(np.ceil(max_x - min_x))
    canvas_height = int(np.ceil(max_y - min_y))
    
    return canvas_width, canvas_height

def calculate_translation_canvas_size(image_shape, tx, ty):
    """
    Calculate the canvas size needed after applying translation.
    
    Args:
        image_shape (tuple): Image shape (height, width)
        tx (float): Translation in x
        ty (float): Translation in y
        
    Returns:
        tuple: (canvas_width, canvas_height, offset_x, offset_y)
    """
    h, w = image_shape[:2]
    
    # Calculate bounds after translation
    min_x = min(0, tx)
    max_x = max(w, w + tx)
    min_y = min(0, ty)
    max_y = max(h, h + ty)
    
    # Calculate required canvas size
    canvas_width = int(np.ceil(max_x - min_x))
    canvas_height = int(np.ceil(max_y - min_y))
    
    # Calculate offset to position correctly
    offset_x = int(-min_x)
    offset_y = int(-min_y)
    
    return canvas_width, canvas_height, offset_x, offset_y

def expand_image_to_canvas(image, target_width, target_height):
    """
    Expand image to target canvas size by centering it.
    
    Args:
        image (np.ndarray): Input image
        target_width (int): Target canvas width
        target_height (int): Target canvas height
        
    Returns:
        np.ndarray: Expanded image centered on canvas
    """
    h, w = image.shape[:2]
    
    # Create expanded canvas with black background
    if len(image.shape) == 3:
        expanded = np.zeros((target_height, target_width, image.shape[2]), dtype=image.dtype)
    else:
        expanded = np.zeros((target_height, target_width), dtype=image.dtype)
    
    # Calculate center position
    start_x = (target_width - w) // 2
    start_y = (target_height - h) // 2
    
    # Ensure we don't exceed bounds
    end_x = min(start_x + w, target_width)
    end_y = min(start_y + h, target_height)
    
    # Place image on canvas
    if start_x >= 0 and start_y >= 0:
        expanded[start_y:end_y, start_x:end_x] = image[0:(end_y-start_y), 0:(end_x-start_x)]
    
    return expanded

def step1_load_images(img1_path, img2_path):
    """
    Step 1: Load image 1 and image 2 from user input
    
    Args:
        img1_path (str): Path to first image
        img2_path (str): Path to second image
        
    Returns:
        tuple: (img1, img2) loaded images
    """
    print("=== STEP 1: Loading Images ===")
    
    img1 = cv2.imread(str(img1_path))
    img2 = cv2.imread(str(img2_path))
    
    if img1 is None:
        raise ValueError(f"Could not load image 1: {img1_path}")
    if img2 is None:
        raise ValueError(f"Could not load image 2: {img2_path}")
    
    print(f"Image 1 loaded: {img1.shape}")
    print(f"Image 2 loaded: {img2.shape}")
    
    return img1, img2

def step2_match_canvas_sizes(img_to_transform, reference_img, match_canvas, inverse):
    """
    Step 2: Match canvas sizes if requested (NEW FEATURE)
    
    When match_canvas=True, resize the reference image canvas to match the transform image canvas
    and re-center the reference image content.
    
    Args:
        img_to_transform (np.ndarray): Image that will be transformed
        reference_img (np.ndarray): Reference image that may need canvas adjustment
        match_canvas (bool): Whether to match canvas sizes
        inverse (bool): Whether inverse transformation is being used
        
    Returns:
        tuple: (img_to_transform, reference_img_adjusted)
    """
    if not match_canvas:
        print("\n=== STEP 2: Canvas matching disabled ===")
        return img_to_transform, reference_img
    
    print("\n=== STEP 2: Matching Canvas Sizes ===")
    
    transform_h, transform_w = img_to_transform.shape[:2]
    reference_h, reference_w = reference_img.shape[:2]
    
    print(f"Transform image size: {transform_w}x{transform_h}")
    print(f"Reference image size: {reference_w}x{reference_h}")
    
    if (transform_h, transform_w) == (reference_h, reference_w):
        print("Images already have the same canvas size - no adjustment needed")
        return img_to_transform, reference_img
    
    # Determine which image needs canvas adjustment
    if inverse:
        print("INVERSE MODE: Reference image (img1) has larger canvas, adjusting transform image (img2) canvas")
        # In inverse mode, img1 is reference and img2 is being transformed
        # If img1 has larger canvas, we need to expand img2's canvas to match
        adjusted_transform_img = expand_image_to_canvas(img_to_transform, transform_w, transform_h)
        adjusted_reference_img = reference_img  # Reference already has the right size
        print(f"Expanded transform image canvas from {img_to_transform.shape} to {adjusted_transform_img.shape}")
    else:
        print("NORMAL MODE: Transform image (img1) has larger canvas, adjusting reference image (img2) canvas")
        # In normal mode, img1 is being transformed and img2 is reference
        # If img1 has larger canvas, we need to expand img2's canvas to match
        adjusted_reference_img = expand_image_to_canvas(reference_img, transform_w, transform_h)
        adjusted_transform_img = img_to_transform  # Transform image already has the right size
        print(f"Expanded reference image canvas from {reference_img.shape} to {adjusted_reference_img.shape}")
    
    print("Canvas sizes now match - both images ready for registration")
    
    return adjusted_transform_img, adjusted_reference_img

def step3_read_and_process_transformation_matrix(csv_path, solution_index=0, inverse=False):
    """
    Step 3: Read transformation matrix from CSV file and optionally compute inverse
    
    Args:
        csv_path (str): Path to CSV file
        solution_index (int): Which solution to use
        inverse (bool): Whether to compute inverse transformation
        
    Returns:
        np.ndarray: 4x4 transformation matrix (original or inverse)
    """
    print("\n=== STEP 3: Reading Transformation Matrix ===")
    
    df = pd.read_csv(csv_path)
    print(f"Found {len(df)} solutions in CSV")
    
    if solution_index >= len(df):
        raise ValueError(f"Solution index {solution_index} out of range (0-{len(df)-1})")
    
    row = df.iloc[solution_index]
    print(f"Using solution index: {solution_index}")
    
    # Reconstruct 4x4 transformation matrix
    transformation_matrix = np.array([
        [row['r11'], row['r12'], row['r13'], row['tx']],
        [row['r21'], row['r22'], row['r23'], row['ty']],
        [row['r31'], row['r32'], row['r33'], row['tz']],
        [row['h41'], row['h42'], row['h43'], row['h44']]
    ])
    
    print("Original 4x4 Transformation Matrix:")
    print(transformation_matrix)
    
    if inverse:
        print("\nComputing inverse transformation...")
        # Compute inverse of 4x4 transformation matrix
        try:
            inverse_matrix = np.linalg.inv(transformation_matrix)
            print("Inverse 4x4 Transformation Matrix:")
            print(inverse_matrix)
            return inverse_matrix
        except np.linalg.LinAlgError:
            raise ValueError("Transformation matrix is not invertible")
    else:
        return transformation_matrix

def step4_apply_scaling_compensation(transformation_matrix, output_dir, do_scale, sx=None, sy=None, source_width=None, source_height=None):
    """
    Step 4: Apply scaling compensation to transformation matrix if enabled
    
    Args:
        transformation_matrix (np.ndarray): Original transformation matrix
        output_dir (Path): Output directory for reading logs
        do_scale (bool): Whether to apply scaling
        sx (float): Manual scaling factor in x (optional)
        sy (float): Manual scaling factor in y (optional)
        
    Returns:
        np.ndarray: Transformation matrix (scaled if do_scale=True, original otherwise)
    """
    if not do_scale:
        print("\n=== STEP 4: Scaling compensation disabled ===")
        return transformation_matrix
    
    print("\n=== STEP 4: Applying Scaling Compensation ===")
    
    # Extract scaling factors
    sx_final, sy_final = extract_scaling_factors_from_logs(output_dir, sx, sy, source_width, source_height)
    
    # Apply scaling to transformation matrix
    scaled_transformation_matrix = apply_scaling_to_transformation_matrix(
        transformation_matrix, sx_final, sy_final
    )
    
    return scaled_transformation_matrix

def step5a_extract_rotation_angle(transformation_matrix):
    """
    Step 5a: Extract rotation matrix and calculate estimated angle
    
    Args:
        transformation_matrix (np.ndarray): 4x4 transformation matrix
        
    Returns:
        float: Rotation angle in degrees
    """
    print("\n=== STEP 5a: Extract Rotation Angle ===")
    
    # Extract rotation angle from transformation matrix
    rotation_angle_rad = np.arctan2(transformation_matrix[1, 0], transformation_matrix[0, 0])
    rotation_angle_deg = np.degrees(rotation_angle_rad)
    
    print(f"Rotation angle: {rotation_angle_deg:.2f} degrees ({rotation_angle_rad:.4f} radians)")
    
    return rotation_angle_deg

def step5b_rotate_image(img, rotation_angle_deg, adjust_canvas=False, image_name="image"):
    """
    Step 5b: Rotate image using cv2.warpAffine()
    
    Args:
        img (np.ndarray): Image to rotate
        rotation_angle_deg (float): Rotation angle in degrees
        adjust_canvas (bool): Whether to adjust canvas size to fit rotation
        image_name (str): Name for logging purposes
        
    Returns:
        np.ndarray: Rotated image
    """
    print(f"\n=== STEP 5b: Rotating {image_name} ===")
    
    height, width = img.shape[:2]
    center = (width / 2, height / 2)
    
    # Create rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, rotation_angle_deg, 1.0)
    print("Rotation matrix (2x3):")
    print(rotation_matrix)
    
    if adjust_canvas:
        # Calculate canvas size needed for full rotation
        canvas_width, canvas_height = calculate_rotation_canvas_size(img.shape, rotation_angle_deg)
        print(f"Adjusted canvas size for rotation: {canvas_width}x{canvas_height}")
        
        # Adjust rotation matrix to center the rotated image in new canvas
        new_center_x = canvas_width / 2
        new_center_y = canvas_height / 2
        
        tx = new_center_x - center[0]
        ty = new_center_y - center[1]
        
        rotation_matrix[0, 2] += tx
        rotation_matrix[1, 2] += ty
        
        output_size = (canvas_width, canvas_height)
        print(f"Canvas adjustment: offset by ({tx:.1f}, {ty:.1f})")
    else:
        # Use original image size
        output_size = (width, height)
        print("Using original canvas size")
    
    # Apply rotation
    rotated_img = cv2.warpAffine(
        img, 
        rotation_matrix, 
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )
    
    print(f"Rotated {image_name} size: {rotated_img.shape}")
    
    return rotated_img

def step5c_create_translation_matrix(transformation_matrix):
    """
    Step 5c: Create translational affine_matrix from CSV values
    
    Args:
        transformation_matrix (np.ndarray): 4x4 transformation matrix
        
    Returns:
        np.ndarray: 2x3 translation matrix
    """
    print("\n=== STEP 5c: Creating Translation Matrix ===")
    
    # Extract translation values
    tx = transformation_matrix[0, 3]
    ty = transformation_matrix[1, 3]
    
    print(f"Translation values: tx={tx:.2f}, ty={ty:.2f}")
    
    # Create pure translation matrix
    translation_matrix = np.array([
        [1.0, 0.0, tx],
        [0.0, 1.0, ty]
    ], dtype=np.float32)
    
    print("Translation matrix (2x3):")
    print(translation_matrix)
    
    return translation_matrix

def step5d_apply_translation(rotated_img, translation_matrix, adjust_canvas=False, image_name="image"):
    """
    Step 5d: Apply translation to rotated image
    
    Args:
        rotated_img (np.ndarray): Rotated image
        translation_matrix (np.ndarray): 2x3 translation matrix
        adjust_canvas (bool): Whether to adjust canvas size for translation
        image_name (str): Name for logging purposes
        
    Returns:
        np.ndarray: Transformed image (rotated + translated)
    """
    print(f"\n=== STEP 5d: Applying Translation to {image_name} ===")
    
    height, width = rotated_img.shape[:2]
    
    if adjust_canvas:
        # Calculate canvas size needed for translation
        tx = translation_matrix[0, 2]
        ty = translation_matrix[1, 2]
        
        canvas_width, canvas_height, offset_x, offset_y = calculate_translation_canvas_size(
            rotated_img.shape, tx, ty
        )
        print(f"Adjusted canvas size for translation: {canvas_width}x{canvas_height}")
        print(f"Canvas offset: ({offset_x}, {offset_y})")
        
        # Adjust translation matrix to account for canvas expansion
        adjusted_translation_matrix = translation_matrix.copy()
        adjusted_translation_matrix[0, 2] += offset_x  # Add offset to tx
        adjusted_translation_matrix[1, 2] += offset_y  # Add offset to ty
        
        output_size = (canvas_width, canvas_height)
        print("Adjusted translation matrix:")
        print(adjusted_translation_matrix)
    else:
        # Use original size and matrix
        adjusted_translation_matrix = translation_matrix
        output_size = (width, height)
        print("Using original canvas size")
    
    # Apply translation
    transformed_image = cv2.warpAffine(
        rotated_img,
        adjusted_translation_matrix,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )
    
    print(f"Final transformed {image_name} size: {transformed_image.shape}")
    
    return transformed_image

def step6_blend_images(transformed_image, reference_image, adjust_canvas=False, transform_name="img1", reference_name="img2"):
    """
    Step 6: Blend transformed_image with reference_image
    Creates two versions: one with colormaps, one with original images
    
    Args:
        transformed_image (np.ndarray): Transformed image
        reference_image (np.ndarray): Reference image (unchanged)
        adjust_canvas (bool): Whether canvas was adjusted (affects reference image handling)
        transform_name (str): Name of transformed image for logging
        reference_name (str): Name of reference image for logging
        
    Returns:
        tuple: (original_blend, colormap_blend)
    """
    print(f"\n=== STEP 6: Blending {transform_name} (transformed) with {reference_name} (reference) ===")
    
    # Get sizes
    h1, w1 = transformed_image.shape[:2]
    h2, w2 = reference_image.shape[:2]
    
    if adjust_canvas:
        # Expand reference image to match transformed image canvas and center it
        print(f"Expanding {reference_name} from {w2}x{h2} to {w1}x{h1} and centering")
        reference_expanded = expand_image_to_canvas(reference_image, w1, h1)
        reference_to_use = reference_expanded
    else:
        # Resize reference image to match transformed image if needed
        if (h1, w1) != (h2, w2):
            print(f"Resizing {reference_name} from {w2}x{h2} to {w1}x{h1}")
            reference_to_use = cv2.resize(reference_image, (w1, h1))
        else:
            reference_to_use = reference_image
    
    # Create masks
    if len(transformed_image.shape) == 3:
        mask_transformed = np.any(transformed_image > 0, axis=2)
        mask_reference = np.any(reference_to_use > 0, axis=2)
    else:
        mask_transformed = transformed_image > 0
        mask_reference = reference_to_use > 0
    
    overlap = mask_transformed & mask_reference
    overlap_pixels = np.sum(overlap)
    print(f"Overlap region: {overlap_pixels} pixels")
    
    # === ORIGINAL BLEND (no colormaps) ===
    print("Creating original blend...")
    transformed_float = transformed_image.astype(np.float32)
    reference_float = reference_to_use.astype(np.float32)
    
    original_blend = np.zeros_like(transformed_image, dtype=np.float32)
    
    # Where only transformed image exists
    only_transformed = mask_transformed & ~mask_reference
    original_blend[only_transformed] = transformed_float[only_transformed]
    
    # Where only reference image exists
    only_reference = mask_reference & ~mask_transformed
    original_blend[only_reference] = reference_float[only_reference]
    
    # Average in overlap
    if overlap_pixels > 0:
        if len(transformed_image.shape) == 3:
            for c in range(transformed_image.shape[2]):
                original_blend[overlap, c] = (transformed_float[overlap, c] + reference_float[overlap, c]) / 2.0
        else:
            original_blend[overlap] = (transformed_float[overlap] + reference_float[overlap]) / 2.0
    
    original_blend = original_blend.astype(np.uint8)
    
    # === COLORMAP BLEND ===
    print("Creating colormap blend...")
    
    # Apply colormaps
    transformed_colored = cv2.applyColorMap(
        cv2.cvtColor(transformed_image, cv2.COLOR_BGR2GRAY) if len(transformed_image.shape) == 3 else transformed_image,
        cv2.COLORMAP_HOT
    )
    reference_colored = cv2.applyColorMap(
        cv2.cvtColor(reference_to_use, cv2.COLOR_BGR2GRAY) if len(reference_to_use.shape) == 3 else reference_to_use,
        cv2.COLORMAP_COOL
    )
    
    # Blend colored images
    transformed_colored_float = transformed_colored.astype(np.float32) / 255.0
    reference_colored_float = reference_colored.astype(np.float32) / 255.0
    
    colormap_blend = np.zeros_like(transformed_colored, dtype=np.float32)
    
    # Where only transformed image exists
    colormap_blend[only_transformed] = transformed_colored_float[only_transformed]
    
    # Where only reference image exists
    colormap_blend[only_reference] = reference_colored_float[only_reference]
    
    # Blend in overlap (50/50)
    if overlap_pixels > 0:
        for c in range(3):  # RGB channels
            colormap_blend[overlap, c] = 0.5 * (transformed_colored_float[overlap, c] + reference_colored_float[overlap, c])
    
    colormap_blend = (colormap_blend * 255).astype(np.uint8)
    
    print("Both blends created successfully")
    
    return original_blend, colormap_blend

def main():
    """
    Main function - orchestrates all steps with scaling support
    """
    parser = argparse.ArgumentParser(description='Enhanced image stitching with scaling support')
    parser.add_argument('image1_path', help='Path to first image relative to /workspace/input')
    parser.add_argument('image2_path', help='Path to second image relative to /workspace/input')
    parser.add_argument('--override-inputdir', action='store_true',
                       help='Override search in /input and follow full-path of images (default: False)')
    parser.add_argument('--csv_dir_path', help='Path to directory containing CSV file')
    parser.add_argument('--subdir_output', help='Subdirectory to save image results')
    parser.add_argument('--solution_index', type=int, nargs='?', default=0, 
                       help='Solution index (default: 0)')
    parser.add_argument('--inverse', action='store_true',
                       help='Apply inverse transformation (transform img2 to img1 instead) (default: False)')
    parser.add_argument('--adjust-canvas', action='store_true',
                       help='Adjust canvas size to fit full transformation (default: False)')
    
    # New scaling arguments
    parser.add_argument('--doscale', action='store_true',
                       help='Enable scaling compensation (default: False)')
    parser.add_argument('--sx', type=float, 
                       help='Manual scaling factor in x direction (optional)')
    parser.add_argument('--sy', type=float,
                       help='Manual scaling factor in y direction (optional)')
    
    # Canvas matching argument
    parser.add_argument('--match-canvas', action='store_true',
                       help='Match canvas sizes when transform image has larger canvas (e.g., pre-stitched) (default: False)')
    
    args = parser.parse_args()
    
    # NEW: Validation check for --match-canvas and scaling parameters
    if args.match_canvas and args.doscale:
        if args.sx is None or args.sy is None:
            print("ERROR: When --match-canvas is enabled with --doscale, both --sx and --sy must be explicitly provided.")
            print("Reason: Canvas adjustment doesn't mean the image was scaled, so automatic scaling factor")
            print("calculation from experiment logs may be incorrect. Please provide manual scaling factors.")
            print("Example: --sx 1.0 --sy 1.0 (if no scaling) or appropriate values for your case.")
            return 1
    
    # Setup paths
    input_dir = Path('/workspace/input')
    output_dir = Path('/workspace/output')
    img1_path = input_dir / args.image1_path if (args.override_inputdir is False) else Path(args.image1_path)
    img2_path = input_dir / args.image2_path if (args.override_inputdir is False) else Path(args.image2_path)
    
    # Determine CSV file path based on user input
    csv_path = determine_csv_path(args.csv_dir_path)
    output_dir = csv_path.parent  # Output in same directory as CSV file

    # Check if the subdirectory for the images files exists, otherwise create it
    if args.subdir_output is not None:
        subdir_output_path = output_dir / args.subdir_output
        subdir_output_path.mkdir(parents=True, exist_ok=True)
    
    print("=== ENHANCED IMAGE STITCHING WITH SCALING SUPPORT ===")
    print(f"Image 1: {args.image1_path}")
    print(f"Image 2: {args.image2_path}")
    print(f"CSV file: {csv_path}")
    print(f"Output dir: {output_dir}")
    print(f"Image subdirectory: {args.subdir_output}")
    print(f"Solution: {args.solution_index}")
    print(f"Inverse: {args.inverse}")
    print(f"Adjust canvas: {args.adjust_canvas}")
    print(f"Match canvas: {args.match_canvas}") 
    print(f"Scaling enabled: {args.doscale}")
    
    if args.doscale:
        if args.sx is not None and args.sy is not None:
            print(f"Manual scaling: sx={args.sx}, sy={args.sy}")
        else:
            print("Scaling: Will calculated based on current image size and experiment_task_logs.csv")
    print()
    
    # Validate paths
    if not img1_path.exists():
        print(f"Error: Image 1 not found: {img1_path}")
        return 1
    if not img2_path.exists():
        print(f"Error: Image 2 not found: {img2_path}")
        return 1
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}")
        return 1
    
    try:
        # ========================================
        # EXECUTE ALL STEPS OF THE PIPELINE
        # ========================================
        
        # STEP 1: Load images
        img1, img2 = step1_load_images(img1_path, img2_path)

        # Determine which image to transform based on inverse flag
        if args.inverse:
            # Transform img2 to align with img1
            img_to_transform = img2
            reference_img = img1
            transform_name = "img2"
            reference_name = "img1"
            print(f"\nINVERSE MODE: Transforming {transform_name} to align with {reference_name}")
        else:
            # Transform img1 to align with img2 (default)
            img_to_transform = img1
            reference_img = img2
            transform_name = "img1"
            reference_name = "img2"
            print(f"\nNORMAL MODE: Transforming {transform_name} to align with {reference_name}")
        
        # STEP 2: Match canvas sizes if requested (NEW FEATURE)
        img_to_transform, reference_img = step2_match_canvas_sizes(
            img_to_transform, reference_img, args.match_canvas, args.inverse
        )
        
        # STEP 3: Read transformation matrix from CSV
        transformation_matrix = step3_read_and_process_transformation_matrix(csv_path, args.solution_index, args.inverse)
        
        # STEP 4: Apply scaling compensation if enabled
        transformation_matrix = step4_apply_scaling_compensation(
            transformation_matrix, output_dir, args.doscale, args.sx, args.sy, 
            img_to_transform.shape[1], img_to_transform.shape[0]  # Use transform image dimensions for scaling
        )
        
        # STEP 5a: Extract rotation angle from transformation matrix
        rotation_angle_deg = step5a_extract_rotation_angle(transformation_matrix)
        
        # STEP 5b: Rotate the selected image
        rotated_img = step5b_rotate_image(img_to_transform, rotation_angle_deg, args.adjust_canvas, transform_name)
        
        # STEP 5c: Create translation matrix from transformation matrix
        translation_matrix = step5c_create_translation_matrix(transformation_matrix)
        
        # STEP 5d: Apply translation to the rotated image
        transformed_image = step5d_apply_translation(rotated_img, translation_matrix, args.adjust_canvas, transform_name)
        
        # STEP 6: Blend the transformed image with the reference image
        original_blend, colormap_blend = step6_blend_images(transformed_image, reference_img, args.adjust_canvas, transform_name, reference_name)
        
        # ========================================
        # SAVE ALL RESULTS
        # ========================================
        print("\n=== SAVING RESULTS ===")
        
        # Build filename suffix based on enabled features
        suffix_parts = []
        
        if args.match_canvas:
            suffix_parts.append("canvas_matched")
        
        if args.doscale:
            sx_final, sy_final = extract_scaling_factors_from_logs(output_dir, args.sx, args.sy, img_to_transform.shape[1], img_to_transform.shape[0])
            suffix_parts.append(f"scaled_{sx_final:.3f}x{sy_final:.3f}")
        
        if args.inverse:
            suffix_parts.append("inverse")
        
        if args.adjust_canvas:
            suffix_parts.append("adjusted_canvas")
        
        # Create filename suffix
        suffix = "_" + "_".join(suffix_parts) if suffix_parts else ""
        
        # Save blended images
        if args.subdir_output is None:
            original_path = output_dir / f"stitched_originals_blend{suffix}.png"
            colormap_path = output_dir / f"stitched_colormaps_blend{suffix}.png"
        else:
            original_path = output_dir / args.subdir_output / f"stitched_originals_blend{suffix}.png"
            colormap_path = output_dir / args.subdir_output / f"stitched_colormaps_blend{suffix}.png"
        
        cv2.imwrite(str(original_path), original_blend)
        cv2.imwrite(str(colormap_path), colormap_blend)
        
        print(f"Original blend saved: {original_path}")
        print(f"Colormap blend saved: {colormap_path}")
        
        # Save intermediate results for debugging if canvas matching was used
        if args.match_canvas:
            if args.subdir_output is None:
                transform_path = output_dir / f"debug_transform_image{suffix}.png"
                reference_path = output_dir / f"debug_reference_image{suffix}.png"
                transformed_path = output_dir / f"debug_transformed_result{suffix}.png"
            else:
                transform_path = output_dir / args.subdir_output / f"debug_transform_image{suffix}.png"
                reference_path = output_dir / args.subdir_output / f"debug_reference_image{suffix}.png"
                transformed_path = output_dir / args.subdir_output / f"debug_transformed_result{suffix}.png"
            
            cv2.imwrite(str(transform_path), img_to_transform)
            cv2.imwrite(str(reference_path), reference_img)
            cv2.imwrite(str(transformed_path), transformed_image)
            
            print(f"Debug - Transform image saved: {transform_path}")
            print(f"Debug - Reference image saved: {reference_path}")
            print(f"Debug - Transformed result saved: {transformed_path}")
        
        print("\n=== PROCESS COMPLETE ===")
        print("All steps executed successfully!")
        
        # Print summary of what was done
        print(f"\nSUMMARY:")
        print(f"- Loaded images: {args.image1_path}, {args.image2_path}")
        print(f"- Transform mode: {'INVERSE' if args.inverse else 'NORMAL'}")
        print(f"- Canvas matching: {'ENABLED' if args.match_canvas else 'DISABLED'}")
        print(f"- Scaling compensation: {'ENABLED' if args.doscale else 'DISABLED'}")
        print(f"- Canvas adjustment: {'ENABLED' if args.adjust_canvas else 'DISABLED'}")
        print(f"- Final canvas size: {transformed_image.shape}")
        
        stitched_image_path = str(original_path)
        data = {"stitched_image_path": stitched_image_path}
        print(json.dumps(data))
        return 0
    
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())