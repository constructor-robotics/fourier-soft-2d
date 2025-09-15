#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from PIL import Image
import sys

def crop_images(input_dir, output_dir, npw, nph):
    """
    Crop images from center and save with sequential naming.
    
    Args:
        input_dir (str): Directory containing input images
        output_dir (str): Directory to save cropped images
        npw (int): Half-width of crop region in pixels
        nph (int): Half-height of crop region in pixels
    """
    
    # Convert to Path objects
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    # Check if input directory exists
    if not input_path.exists():
        print(f"Error: Input directory '{input_dir}' does not exist.")
        sys.exit(1)
    
    if not input_path.is_dir():
        print(f"Error: '{input_dir}' is not a directory.")
        sys.exit(1)
    
    # Create output directory if it doesn't exist
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {output_path}")
    
    # Get all image files and sort them alphabetically
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif'}
    image_files = []
    
    for file_path in input_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            image_files.append(file_path)
    
    # Sort alphabetically (ascending)
    image_files.sort(key=lambda x: x.name.lower())
    
    if not image_files:
        print(f"No image files found in '{input_dir}'")
        return
    
    print(f"Found {len(image_files)} image files to process")
    
    # Process each image
    processed_count = 0
    for i, image_file in enumerate(image_files, 1):
        try:
            # Open image
            with Image.open(image_file) as img:
                # Get image dimensions
                width, height = img.size
                
                # Calculate center coordinates
                cx = width // 2
                cy = height // 2
                
                # Calculate crop boundaries
                # Top-left corner: (cy-nph, cx-npw)
                # Bottom-right corner: (cy+nph, cx+npw)
                left = cx - npw
                top = cy - nph
                right = cx + npw
                bottom = cy + nph
                
                # Check if crop region is within image boundaries
                if left < 0 or top < 0 or right > width or bottom > height:
                    print(f"Warning: Crop region for '{image_file.name}' exceeds image boundaries")
                    print(f"  Image size: {width}x{height}, Center: ({cx},{cy})")
                    print(f"  Crop region: ({left},{top}) to ({right},{bottom})")
                    print(f"  Adjusting crop region to fit within image...")
                    
                    # Adjust boundaries to stay within image
                    left = max(0, left)
                    top = max(0, top)
                    right = min(width, right)
                    bottom = min(height, bottom)
                
                # Crop the image
                cropped_img = img.crop((left, top, right, bottom))
                
                # Generate output filename with 4-digit suffix
                output_filename = f"image_{i:04d}.png"
                output_file_path = output_path / output_filename
                
                # Save cropped image as PNG
                cropped_img.save(output_file_path, 'PNG')
                
                processed_count += 1
                print(f"Processed: {image_file.name} -> {output_filename} "
                      f"(crop: {right-left}x{bottom-top})")
                
        except Exception as e:
            print(f"Error processing '{image_file.name}': {str(e)}")
            continue
    
    print(f"\nProcessing complete! {processed_count}/{len(image_files)} images processed successfully.")

def main():
    parser = argparse.ArgumentParser(
        description="Crop images from center and save with sequential naming",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python crop_images.py /path/to/input /path/to/output --npw 100 --nph 100
  python crop_images.py input_dir output_dir --nopixels-width 150 --nopixels-height 200
        """
    )
    
    parser.add_argument('input_dir', 
                       help='Directory containing input images')
    
    parser.add_argument('output_dir', 
                       help='Directory to save cropped images (will be created if it doesn\'t exist)')
    
    # Add arguments for crop dimensions with both short and long forms
    parser.add_argument('--nopixels-width', '--npw', 
                       type=int, 
                       required=True,
                       help='Half-width of crop region in pixels')
    
    parser.add_argument('--nopixels-height', '--nph', 
                       type=int, 
                       required=True,
                       help='Half-height of crop region in pixels')
    
    args = parser.parse_args()
    
    # Validate crop dimensions
    if args.nopixels_width <= 0 or args.nopixels_height <= 0:
        print("Error: Crop dimensions must be positive integers.")
        sys.exit(1)
    
    print(f"Input directory: {args.input_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Crop half-width: {args.nopixels_width} pixels")
    print(f"Crop half-height: {args.nopixels_height} pixels")
    print(f"Total crop size: {args.nopixels_width * 2}x{args.nopixels_height * 2} pixels")
    print("-" * 50)
    
    crop_images(args.input_dir, args.output_dir, args.nopixels_width, args.nopixels_height)

if __name__ == "__main__":
    main()