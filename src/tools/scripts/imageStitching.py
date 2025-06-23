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
    
    return expanded#!/usr/bin/env python3
"""
Image Stitching Script - Systematic Implementation

Steps:
1. Load image 1 and image 2 from user input
2. Read transformation matrix from CSV file
3. From transformation matrix:
   a. Extract rotation matrix and calculate angle
   b. Rotate image1 using cv2.warpAffine()
   c. Create translational affine_matrix from CSV values
   d. Apply translation to rotated image1
   e. Result = transformed_image
4. Blend transformed_image with image2 (with and without colormaps)
"""

import numpy as np
import cv2
import pandas as pd
import argparse
from pathlib import Path

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

def step2_read_and_process_transformation_matrix(csv_path, solution_index=0, inverse=False):
    """
    Step 2: Read transformation matrix from CSV file and optionally compute inverse
    
    Args:
        csv_path (str): Path to CSV file
        solution_index (int): Which solution to use
        inverse (bool): Whether to compute inverse transformation
        
    Returns:
        np.ndarray: 4x4 transformation matrix (original or inverse)
    """
    print("\n=== STEP 2: Reading Transformation Matrix ===")
    
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

def step3a_extract_rotation_angle(transformation_matrix):
    """
    Step 3a: Extract rotation matrix and calculate estimated angle
    
    Args:
        transformation_matrix (np.ndarray): 4x4 transformation matrix
        
    Returns:
        float: Rotation angle in degrees
    """
    print("\n=== STEP 3a: Extract Rotation Angle ===")
    
    # Extract rotation angle from transformation matrix
    rotation_angle_rad = np.arctan2(transformation_matrix[1, 0], transformation_matrix[0, 0])
    rotation_angle_deg = np.degrees(rotation_angle_rad)
    
    print(f"Rotation angle: {rotation_angle_deg:.2f} degrees ({rotation_angle_rad:.4f} radians)")
    
    return rotation_angle_deg

def step3b_rotate_image(img, rotation_angle_deg, adjust_canvas=False, image_name="image"):
    """
    Step 3b: Rotate image using cv2.warpAffine()
    
    Args:
        img (np.ndarray): Image to rotate
        rotation_angle_deg (float): Rotation angle in degrees
        adjust_canvas (bool): Whether to adjust canvas size to fit rotation
        image_name (str): Name for logging purposes
        
    Returns:
        np.ndarray: Rotated image
    """
    print(f"\n=== STEP 3b: Rotating {image_name} ===")
    
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

def step3c_create_translation_matrix(transformation_matrix):
    """
    Step 3c: Create translational affine_matrix from CSV values
    
    Args:
        transformation_matrix (np.ndarray): 4x4 transformation matrix
        
    Returns:
        np.ndarray: 2x3 translation matrix
    """
    print("\n=== STEP 3c: Creating Translation Matrix ===")
    
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

def step3d_apply_translation(rotated_img, translation_matrix, adjust_canvas=False, image_name="image"):
    """
    Step 3d: Apply translation to rotated image
    
    Args:
        rotated_img (np.ndarray): Rotated image
        translation_matrix (np.ndarray): 2x3 translation matrix
        adjust_canvas (bool): Whether to adjust canvas size for translation
        image_name (str): Name for logging purposes
        
    Returns:
        np.ndarray: Transformed image (rotated + translated)
    """
    print(f"\n=== STEP 3d: Applying Translation to {image_name} ===")
    
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

def step4_blend_images(transformed_image, reference_image, adjust_canvas=False, transform_name="img1", reference_name="img2"):
    """
    Step 4: Blend transformed_image with reference_image
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
    print(f"\n=== STEP 4: Blending {transform_name} (transformed) with {reference_name} (reference) ===")
    
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
    Main function - orchestrates all steps
    """
    parser = argparse.ArgumentParser(description='Systematic image stitching')
    parser.add_argument('image1_path', help='Path to first image relative to /workspace/input')
    parser.add_argument('image2_path', help='Path to second image relative to /workspace/input')
    parser.add_argument('--csv_dir_path', help='Path to directory containing CSV file')
    parser.add_argument('--solution_index', type=int, nargs='?', default=0, 
                       help='Solution index (default: 0)')
    parser.add_argument('--inverse', action='store_true',
                       help='Apply inverse transformation (transform img2 to img1 instead) (default: False)')
    parser.add_argument('--adjust-canvas', action='store_true',
                       help='Adjust canvas size to fit full transformation (default: False)')
    
    args = parser.parse_args()
    
    # Setup paths
    input_dir = Path('/workspace/input')
    output_dir = Path('/workspace/output')
    img1_path = input_dir / args.image1_path
    img2_path = input_dir / args.image2_path
    
    # Handle CSV directory - use latest timestamped dir if not provided
    if args.csv_dir_path is None:
        print("No CSV directory specified, searching for latest timestamped directory...")
        csv_dir = find_latest_output_directory()
    else:
        csv_dir = output_dir / Path(args.csv_dir_path) 
    
    csv_path = csv_dir / 'registration_solutions_transformation.csv'
    output_dir = csv_dir
    
    print("=== SYSTEMATIC IMAGE STITCHING ===")
    print(f"Image 1: {args.image1_path}")
    print(f"Image 2: {args.image2_path}")
    print(f"CSV dir: {csv_dir}")
    print(f"Solution: {args.solution_index}")
    print(f"Inverse: {args.inverse}")
    print(f"Adjust canvas: {args.adjust_canvas}")
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
        # Execute all steps
        img1, img2 = step1_load_images(img1_path, img2_path)
        
        transformation_matrix = step2_read_and_process_transformation_matrix(csv_path, args.solution_index, args.inverse)
        
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
        
        rotation_angle_deg = step3a_extract_rotation_angle(transformation_matrix)
        
        rotated_img = step3b_rotate_image(img_to_transform, rotation_angle_deg, args.adjust_canvas, transform_name)
        
        translation_matrix = step3c_create_translation_matrix(transformation_matrix)
        
        transformed_image = step3d_apply_translation(rotated_img, translation_matrix, args.adjust_canvas, transform_name)
        
        original_blend, colormap_blend = step4_blend_images(transformed_image, reference_img, args.adjust_canvas, transform_name, reference_name)
        
        # Save results
        print("\n=== SAVING RESULTS ===")
        
        original_path = output_dir / "original_blend.jpg"
        colormap_path = output_dir / "colormap_blend.jpg"
        
        cv2.imwrite(str(original_path), original_blend)
        cv2.imwrite(str(colormap_path), colormap_blend)
        
        print(f"Original blend saved: {original_path}")
        print(f"Colormap blend saved: {colormap_path}")
        
        print("\n=== PROCESS COMPLETE ===")
        return 0
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return 1

if __name__ == "__main__":
    exit(main())