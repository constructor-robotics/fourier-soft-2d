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

def step2_read_transformation_matrix(csv_path, solution_index=0):
    """
    Step 2: Read transformation matrix from CSV file
    
    Args:
        csv_path (str): Path to CSV file
        solution_index (int): Which solution to use
        
    Returns:
        np.ndarray: 4x4 transformation matrix
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
    
    print("4x4 Transformation Matrix:")
    print(transformation_matrix)
    
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

def step3b_rotate_image1(img1, rotation_angle_deg, adjust_canvas=False):
    """
    Step 3b: Rotate image1 using cv2.warpAffine()
    
    Args:
        img1 (np.ndarray): First image
        rotation_angle_deg (float): Rotation angle in degrees
        adjust_canvas (bool): Whether to adjust canvas size to fit rotation
        
    Returns:
        np.ndarray: Rotated image
    """
    print("\n=== STEP 3b: Rotating Image 1 ===")
    
    height, width = img1.shape[:2]
    center = (width / 2, height / 2)
    
    # Create rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, rotation_angle_deg, 1.0)
    print("Rotation matrix (2x3):")
    print(rotation_matrix)
    
    if adjust_canvas:
        # Calculate canvas size needed for full rotation
        canvas_width, canvas_height = calculate_rotation_canvas_size(img1.shape, rotation_angle_deg)
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
    rotated_img1 = cv2.warpAffine(
        img1, 
        rotation_matrix, 
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )
    
    print(f"Rotated image size: {rotated_img1.shape}")
    
    return rotated_img1

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

def step3d_apply_translation(rotated_img1, translation_matrix, adjust_canvas=False):
    """
    Step 3d: Apply translation to rotated image1
    
    Args:
        rotated_img1 (np.ndarray): Rotated image
        translation_matrix (np.ndarray): 2x3 translation matrix
        adjust_canvas (bool): Whether to adjust canvas size for translation
        
    Returns:
        np.ndarray: Transformed image (rotated + translated)
    """
    print("\n=== STEP 3d: Applying Translation ===")
    
    height, width = rotated_img1.shape[:2]
    
    if adjust_canvas:
        # Calculate canvas size needed for translation
        tx = translation_matrix[0, 2]
        ty = translation_matrix[1, 2]
        
        canvas_width, canvas_height, offset_x, offset_y = calculate_translation_canvas_size(
            rotated_img1.shape, tx, ty
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
        rotated_img1,
        adjusted_translation_matrix,
        output_size,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0
    )
    
    print(f"Final transformed image size: {transformed_image.shape}")
    
    return transformed_image

def step4_blend_images(transformed_image, img2, adjust_canvas=False):
    """
    Step 4: Blend transformed_image with image2
    Creates two versions: one with colormaps, one with original images
    
    Args:
        transformed_image (np.ndarray): Final transformed image
        img2 (np.ndarray): Second image (reference)
        adjust_canvas (bool): Whether canvas was adjusted (affects img2 handling)
        
    Returns:
        tuple: (original_blend, colormap_blend)
    """
    print("\n=== STEP 4: Blending Images ===")
    
    # Get sizes
    h1, w1 = transformed_image.shape[:2]
    h2, w2 = img2.shape[:2]
    
    if adjust_canvas:
        # Expand img2 to match transformed_image canvas and center it
        print(f"Expanding img2 from {w2}x{h2} to {w1}x{h1} and centering")
        img2_expanded = expand_image_to_canvas(img2, w1, h1)
        img2_to_use = img2_expanded
    else:
        # Resize img2 to match transformed_image if needed
        if (h1, w1) != (h2, w2):
            print(f"Resizing img2 from {w2}x{h2} to {w1}x{h1}")
            img2_to_use = cv2.resize(img2, (w1, h1))
        else:
            img2_to_use = img2
    
    # Create masks
    if len(transformed_image.shape) == 3:
        mask1 = np.any(transformed_image > 0, axis=2)
        mask2 = np.any(img2_to_use > 0, axis=2)
    else:
        mask1 = transformed_image > 0
        mask2 = img2_to_use > 0
    
    overlap = mask1 & mask2
    overlap_pixels = np.sum(overlap)
    print(f"Overlap region: {overlap_pixels} pixels")
    
    # === ORIGINAL BLEND (no colormaps) ===
    print("Creating original blend...")
    img1_float = transformed_image.astype(np.float32)
    img2_float = img2_to_use.astype(np.float32)
    
    original_blend = np.zeros_like(transformed_image, dtype=np.float32)
    
    # Where only img1 exists
    only_img1 = mask1 & ~mask2
    original_blend[only_img1] = img1_float[only_img1]
    
    # Where only img2 exists
    only_img2 = mask2 & ~mask1
    original_blend[only_img2] = img2_float[only_img2]
    
    # Average in overlap
    if overlap_pixels > 0:
        if len(transformed_image.shape) == 3:
            for c in range(transformed_image.shape[2]):
                original_blend[overlap, c] = (img1_float[overlap, c] + img2_float[overlap, c]) / 2.0
        else:
            original_blend[overlap] = (img1_float[overlap] + img2_float[overlap]) / 2.0
    
    original_blend = original_blend.astype(np.uint8)
    
    # === COLORMAP BLEND ===
    print("Creating colormap blend...")
    
    # Apply colormaps
    img1_colored = cv2.applyColorMap(
        cv2.cvtColor(transformed_image, cv2.COLOR_BGR2GRAY) if len(transformed_image.shape) == 3 else transformed_image,
        cv2.COLORMAP_HOT
    )
    img2_colored = cv2.applyColorMap(
        cv2.cvtColor(img2_to_use, cv2.COLOR_BGR2GRAY) if len(img2_to_use.shape) == 3 else img2_to_use,
        cv2.COLORMAP_COOL
    )
    
    # Blend colored images
    img1_colored_float = img1_colored.astype(np.float32) / 255.0
    img2_colored_float = img2_colored.astype(np.float32) / 255.0
    
    colormap_blend = np.zeros_like(img1_colored, dtype=np.float32)
    
    # Where only img1 exists
    colormap_blend[only_img1] = img1_colored_float[only_img1]
    
    # Where only img2 exists
    colormap_blend[only_img2] = img2_colored_float[only_img2]
    
    # Blend in overlap (50/50)
    if overlap_pixels > 0:
        for c in range(3):  # RGB channels
            colormap_blend[overlap, c] = 0.5 * (img1_colored_float[overlap, c] + img2_colored_float[overlap, c])
    
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
    parser.add_argument('csv_dir_path', help='Path to directory containing CSV file')
    parser.add_argument('solution_index', type=int, nargs='?', default=0, 
                       help='Solution index (default: 0)')
    parser.add_argument('--adjust-canvas', action='store_true',
                       help='Adjust canvas size to fit full transformation (default: False)')
    
    args = parser.parse_args()
    
    print("=== SYSTEMATIC IMAGE STITCHING ===")
    print(f"Image 1: {args.image1_path}")
    print(f"Image 2: {args.image2_path}")
    print(f"CSV dir: {args.csv_dir_path}")
    print(f"Solution: {args.solution_index}")
    print(f"Adjust canvas: {args.adjust_canvas}")
    print()
    
    # Setup paths
    input_dir = Path('/workspace/input')
    img1_path = input_dir / args.image1_path
    img2_path = input_dir / args.image2_path
    csv_dir = Path(args.csv_dir_path)
    csv_path = csv_dir / 'registration_solutions_transformation.csv'
    output_dir = csv_dir
    
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
        
        transformation_matrix = step2_read_transformation_matrix(csv_path, args.solution_index)
        
        rotation_angle_deg = step3a_extract_rotation_angle(transformation_matrix)
        
        rotated_img1 = step3b_rotate_image1(img1, rotation_angle_deg, args.adjust_canvas)
        
        translation_matrix = step3c_create_translation_matrix(transformation_matrix)
        
        transformed_image = step3d_apply_translation(rotated_img1, translation_matrix, args.adjust_canvas)
        
        original_blend, colormap_blend = step4_blend_images(transformed_image, img2, args.adjust_canvas)
        
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