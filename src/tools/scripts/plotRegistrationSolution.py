import os
import sys
import glob
# Set environment variables before importing matplotlib to ensure headless operation. i.e., to avoid GUI backend issues.
os.environ['MPLBACKEND'] = 'Agg'
os.environ['DISPLAY'] = ''

import numpy as np
import pandas as pd
import cv2
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.signal import find_peaks

# Disable interactive mode completely
plt.ioff()

def create_sphere_texture(data, size=1000):
    """Create a sphere with texture mapping similar to MATLAB's sphere function"""
    try:
        # Create sphere coordinates
        u = np.linspace(0, 2 * np.pi, size)
        v = np.linspace(0, np.pi, size)
        x = np.outer(np.cos(u), np.sin(v))
        y = np.outer(np.sin(u), np.sin(v))
        z = np.outer(np.ones(np.size(u)), np.cos(v))
        
        # Create the sphere plot with texture
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_surface(x, y, z, facecolors=plt.cm.viridis(data), 
                       linewidth=0, antialiased=False)
        ax.set_box_aspect([1,1,1])
        return fig
    except Exception as e:
        print(f"Warning: 3D sphere plotting failed ({e}), falling back to 2D visualization")
        return None

def get_latest_timestamp_folder(base_dir):
    """Find the folder with the latest UNIX timestamp name"""
    try:
        # Get all directories in the base directory
        directories = [d for d in os.listdir(base_dir) 
                      if os.path.isdir(os.path.join(base_dir, d))]
        
        # Filter directories that are valid UNIX timestamps (numeric)
        timestamp_dirs = []
        for dir_name in directories:
            try:
                timestamp = int(dir_name)
                timestamp_dirs.append((timestamp, dir_name))
            except ValueError:
                continue
        
        if not timestamp_dirs:
            return None
            
        # Sort by timestamp and return the latest
        timestamp_dirs.sort(reverse=True)
        return timestamp_dirs[0][1]  # Return the directory name
        
    except Exception as e:
        print(f"Error finding latest timestamp folder: {e}")
        return None

def check_debug_mode(folder_path):
    """Check if the folder contains debug files to determine debug mode"""
    rotation_file = os.path.join(folder_path, "rotation_analysis_results.csv")
    registration_file = os.path.join(folder_path, "registration_results.csv")
    
    return os.path.exists(rotation_file) and os.path.exists(registration_file)

def print_usage():
    """Print usage information"""
    print("Usage: python3 plotSolutionsOneScan.py [folder_name]")
    print("")
    print("Arguments:")
    print("  folder_name    Name of the folder under /workspace/output (optional)")
    print("                 If not provided, uses the folder with the latest UNIX timestamp")
    print("")
    print("Examples:")
    print("  python3 plotSolutionsOneScan.py my_results")
    print("  python3 plotSolutionsOneScan.py 1703123456")
    print("  python3 plotSolutionsOneScan.py")

def main():
    
    base_output_dir = "/workspace/output"
    
    # Parse command line arguments
    if len(sys.argv) > 2:
        print("Error: Too many arguments")
        print_usage()
        return
    elif len(sys.argv) == 2:
        if sys.argv[1] in ["-h", "--help"]:
            print_usage()
            return
        folder_name = sys.argv[1]
    else:
        # No folder specified, find latest timestamp folder
        folder_name = get_latest_timestamp_folder(base_output_dir)
        if folder_name is None:
            print("Error: No timestamp folders found in /workspace/output")
            print("Available folders:")
            try:
                dirs = [d for d in os.listdir(base_output_dir) 
                       if os.path.isdir(os.path.join(base_output_dir, d))]
                for d in dirs:
                    print(f"  {d}")
            except:
                print("  (unable to list directories)")
            return
        print(f"Using latest timestamp folder: {folder_name}")
    
    # Construct full path
    name_of_folder = os.path.join(base_output_dir, folder_name)
    
    # Check if folder exists
    if not os.path.exists(name_of_folder):
        print(f"Error: Folder '{name_of_folder}' does not exist")
        print("Available folders:")
        try:
            dirs = [d for d in os.listdir(base_output_dir) 
                   if os.path.isdir(os.path.join(base_output_dir, d))]
            for d in dirs:
                print(f"  {d}")
        except:
            print("  (unable to list directories)")
        return
    
    print(f"Processing data from: {name_of_folder}")
    
    # Check debug mode
    debug_mode = check_debug_mode(name_of_folder)
    print(f"Debug mode detected: {debug_mode}")
    
    # Check if transformation file exists (required in both modes)
    transformation_file = os.path.join(name_of_folder, "registration_solutions_transformation.csv")
    if not os.path.exists(transformation_file):
        print(f"Error: Required file 'registration_solutions_transformation.csv' not found in {name_of_folder}")
        return
    
    # Read transformation data (always available)
    try:
        transformation_data = pd.read_csv(transformation_file)
        print(f"Found {len(transformation_data)} transformation solution(s)")
    except Exception as e:
        print(f"Error reading transformation file: {e}")
        return
    
    if debug_mode:
        # Read data from all CSV files (debug mode)
        try:
            rotation_data = pd.read_csv(os.path.join(name_of_folder, "rotation_analysis_results.csv"))
            registration_data = pd.read_csv(os.path.join(name_of_folder, "registration_results.csv"))
        except FileNotFoundError as e:
            print(f"Error: Required debug CSV file not found: {e}")
            return
        except Exception as e:
            print(f"Error reading debug CSV files: {e}")
            return
        
        # Extract data from CSV files
        magnitude_fftw1 = rotation_data['magnitudeFFTW1'].dropna().values
        phase_fftw1 = rotation_data['phaseFFTW1'].dropna().values
        voxel_data_used1 = rotation_data['voxelDataFFTW1'].dropna().values
        magnitude_fftw2 = rotation_data['magnitudeFFTW2'].dropna().values
        phase_fftw2 = rotation_data['phaseFFTW2'].dropna().values
        voxel_data_used2 = rotation_data['voxelDataFFTW2'].dropna().values
        resampled_data_sphere1 = rotation_data['resampledVoxel1'].dropna().values
        resampled_data_sphere2 = rotation_data['resampledVoxel2'].dropna().values
        correlation_of_angles = rotation_data['resultingCorrelation1D'].dropna().values
        
        # Get solution info from registration results
        number_of_solutions = int(registration_data['numberOfSolutions'].iloc[0])
        best_solution = int(registration_data['indexOfBestSolution'].iloc[0]) + 1  # MATLAB 1-indexed
        
        # Generate all debug visualizations
        generate_debug_visualizations(name_of_folder, magnitude_fftw1, phase_fftw1, voxel_data_used1,
                                    magnitude_fftw2, phase_fftw2, voxel_data_used2,
                                    resampled_data_sphere1, resampled_data_sphere2,
                                    correlation_of_angles, registration_data, 
                                    number_of_solutions, best_solution)
    else:
        # Non-debug mode - only transformation data available
        number_of_solutions = len(transformation_data)
        best_solution = 1 if number_of_solutions > 0 else 0  # Only one solution in non-debug mode
        print("Debug mode disabled - limited visualizations available")
    
    # Generate transformation matrix visualization (available in both modes)
    generate_transformation_visualization(name_of_folder, transformation_data, best_solution)
    
    print(f"\nProcessing completed!")
    print(f"Number of solutions: {number_of_solutions}")
    print(f"Best solution: {best_solution}")
    print(f"Results saved in: {name_of_folder}")
    
    if debug_mode:
        print(f"\nBest transformation matrix (Solution {best_solution}):")
        best_row = transformation_data.iloc[best_solution-1]  # Convert to 0-based index
    else:
        print(f"\nTransformation matrix:")
        best_row = transformation_data.iloc[0]  # Only one solution in non-debug mode
    
    best_transformation = np.array([
        [best_row['r11'], best_row['r12'], best_row['r13'], best_row['tx']],
        [best_row['r21'], best_row['r22'], best_row['r23'], best_row['ty']],
        [best_row['r31'], best_row['r32'], best_row['r33'], best_row['tz']],
        [best_row['h41'], best_row['h42'], best_row['h43'], best_row['h44']]
    ])
    print(best_transformation)

def generate_debug_visualizations(name_of_folder, magnitude_fftw1, phase_fftw1, voxel_data_used1,
                                magnitude_fftw2, phase_fftw2, voxel_data_used2,
                                resampled_data_sphere1, resampled_data_sphere2,
                                correlation_of_angles, registration_data, 
                                number_of_solutions, best_solution):
    """Generate all debug visualizations when debug mode is enabled"""
    
    # Calculate N from data size
    N = int(np.sqrt(len(magnitude_fftw1)))
    
    # Initialize matrices
    magnitude1 = np.zeros((N, N))
    phase1 = np.zeros((N, N))
    voxel_data1 = np.zeros((N, N))
    magnitude2 = np.zeros((N, N))
    phase2 = np.zeros((N, N))
    voxel_data2 = np.zeros((N, N))
    
    # Reshape data from 1D to 2D (change MATLAB indexing conversion to numpy and OpenCV version)
    for j in range(N):
        for k in range(N):
            magnitude1[j,k] = magnitude_fftw1[k * N - N + j]
            phase1[j,k] = phase_fftw1[k * N - N + j]
            voxel_data1[j,k] = voxel_data_used1[k * N + j]
            magnitude2[j,k] = magnitude_fftw2[k * N - N + j]
            phase2[j,k] = phase_fftw2[k * N - N + j]
            voxel_data2[j,k] = voxel_data_used2[k * N + j]
    
    # Apply FFT shift
    magnitude1 = np.fft.fftshift(magnitude1)
    phase1 = np.fft.fftshift(phase1)
    magnitude2 = np.fft.fftshift(magnitude2)
    phase2 = np.fft.fftshift(phase2)
    
    # Save Figure 1: Magnitude Voxel 1
    plt.figure(figsize=(8, 6))
    plt.imshow(magnitude1, cmap='viridis')
    plt.title('Magnitude Voxel 1')
    plt.axis('equal')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/magnitude_voxel1.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 2: Voxel Data 1
    plt.figure(figsize=(8, 6))
    plt.imshow(voxel_data1, cmap='viridis')
    plt.title('Voxel Data 1')
    plt.axis('equal')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/voxel_data1.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 3: Magnitude Voxel 2
    plt.figure(figsize=(8, 6))
    plt.imshow(magnitude2, cmap='viridis')
    plt.title('Magnitude Voxel 2')
    plt.axis('equal')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/magnitude_voxel2.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 4: Voxel Data 2
    plt.figure(figsize=(8, 6))
    plt.imshow(voxel_data2, cmap='viridis')
    plt.title('Voxel Data 2')
    plt.axis('equal')
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/voxel_data2.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Process resampled sphere data
    resampled_sphere_result1 = np.zeros((N, N))
    resampled_sphere_result2 = np.zeros((N, N))
    
    for j in range(N):
        for i in range(N):
            resampled_sphere_result1[j, i] = resampled_data_sphere1[i * N + j]
            resampled_sphere_result2[j, i] = resampled_data_sphere2[i * N + j]
    
    # Option to plot as sphere (set to True) or as 2D (set to False)
    plot_as_sphere = True
    
    if plot_as_sphere:
        # Save Figure 5: Resampled Sphere 2 (3D)
        fig = create_sphere_texture(resampled_sphere_result2)
        if fig is not None:
            plt.title('Resampled Sphere 2')
            plt.savefig(f"{name_of_folder}/resampled_sphere2_3d.png", dpi=300, bbox_inches='tight')
            plt.close(fig)
        else:
            # Fallback to 2D if 3D fails
            plt.figure(figsize=(8, 8))
            plt.imshow(resampled_sphere_result2, cmap='viridis')
            plt.title('Resampled Sphere 2 (2D fallback)')
            plt.axis('equal')
            plt.colorbar()
            plt.tight_layout()
            plt.savefig(f"{name_of_folder}/resampled_sphere2_2d_fallback.png", dpi=300, bbox_inches='tight')
            plt.close()
        
        # Save Figure 6: Resampled Sphere 1 (3D)
        fig = create_sphere_texture(resampled_sphere_result1)
        if fig is not None:
            plt.title('Resampled Sphere 1')
            plt.savefig(f"{name_of_folder}/resampled_sphere1_3d.png", dpi=300, bbox_inches='tight')
            plt.close(fig)
        else:
            # Fallback to 2D if 3D fails
            plt.figure(figsize=(8, 8))
            plt.imshow(resampled_sphere_result1, cmap='viridis')
            plt.title('Resampled Sphere 1 (2D fallback)')
            plt.axis('equal')
            plt.colorbar()
            plt.tight_layout()
            plt.savefig(f"{name_of_folder}/resampled_sphere1_2d_fallback.png", dpi=300, bbox_inches='tight')
            plt.close()
    else:
        # Save Figure 5: Resampled Sphere 2 (2D)
        plt.figure(figsize=(8, 8))
        plt.imshow(resampled_sphere_result2, cmap='viridis')
        plt.title('Resampled Sphere as 2D 2')
        plt.axis('equal')
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(f"{name_of_folder}/resampled_sphere2_2d.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # Save Figure 6: Resampled Sphere 1 (2D)
        plt.figure(figsize=(8, 8))
        plt.imshow(resampled_sphere_result1, cmap='viridis')
        plt.title('Resampled Sphere as 2D 1')
        plt.axis('equal')
        plt.colorbar()
        plt.tight_layout()
        plt.savefig(f"{name_of_folder}/resampled_sphere1_2d.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    # Save Figure 7: Correlation of Angles
    angles_x = np.linspace(0, 2 * np.pi, len(correlation_of_angles))
    
    # Find peaks
    peaks, _ = find_peaks(correlation_of_angles)
    
    plt.figure(figsize=(10, 6))
    plt.plot(angles_x, correlation_of_angles)
    plt.plot(angles_x[peaks], correlation_of_angles[peaks], 'ro', markersize=5)
    plt.grid(True)
    plt.xlim([-0.2, 2 * np.pi + 0.2])
    plt.xlabel('Angle in rad')
    plt.ylabel('Correlation Value')
    plt.title('Correlation of Angles')
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/correlation_angles.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 8: Correlation matrices for all solutions
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for i in range(number_of_solutions):
        correlation_column = f"resultingCorrelationShift{i}"
        if correlation_column in registration_data.columns:
            correlation_matrix_shift_1d = registration_data[correlation_column].dropna().values
            
            result_size = int(np.round(len(correlation_matrix_shift_1d) ** (1/2)))
            correlation_matrix_shift_2d = correlation_matrix_shift_1d.reshape(result_size, result_size)
            
            if i < len(axes):
                im = axes[i].imshow(correlation_matrix_shift_2d, cmap='viridis')
                axes[i].set_title(f'Solution {i+1}')
                axes[i].set_aspect('equal')
                plt.colorbar(im, ax=axes[i])
        else:
            print(f"Warning: Column {correlation_column} not found in registration_results.csv")
    
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/correlation_matrices.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 9: Registration results (blended voxels)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for i in range(number_of_solutions):
        voxel1_column = f"resultVoxel1{i}"
        voxel2_column = f"resultVoxel2{i}"
        
        if voxel1_column in registration_data.columns and voxel2_column in registration_data.columns:
            result_voxel1_tmp = registration_data[voxel1_column].dropna().values
            result_voxel2_tmp = registration_data[voxel2_column].dropna().values
            
            voxel_result1 = np.zeros((N, N))
            voxel_result2 = np.zeros((N, N))
            
            for j in range(N):
                for k in range(N):
                    voxel_result1[j,k] = result_voxel1_tmp[k * N - N + j]
                    voxel_result2[j,k] = result_voxel2_tmp[k * N - N + j]
            
            # Normalize data for blending
            voxel1_norm = cv2.normalize(voxel_result1.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
            voxel2_norm = cv2.normalize(voxel_result2.astype(np.float32), None, 0, 255, cv2.NORM_MINMAX)
            
            # Convert to 3-channel for color blending
            voxel1_color = cv2.applyColorMap(voxel1_norm.astype(np.uint8), cv2.COLORMAP_HOT)
            voxel2_color = cv2.applyColorMap(voxel2_norm.astype(np.uint8), cv2.COLORMAP_COOL)
            
            # Blend the images
            blended = cv2.addWeighted(voxel1_color, 0.5, voxel2_color, 0.5, 0)
            
            if i < len(axes):
                axes[i].imshow(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
                axes[i].set_title(f'Registration Result {i+1}')
                axes[i].set_aspect('equal')
                axes[i].axis('off')
        else:
            print(f"Warning: Columns {voxel1_column} or {voxel2_column} not found in registration_results.csv")
    
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/registration_results.png", dpi=300, bbox_inches='tight')
    plt.close()

def generate_transformation_visualization(name_of_folder, transformation_data, best_solution):
    """Generate transformation matrix visualization (available in both debug and non-debug modes)"""    # Display and visualize transformation matrices
    print("\nTransformation Matrices:")
    print("=" * 50)
    for i, row in transformation_data.iterrows():
        print(f"\nSolution {i+1}:")
        transformation_matrix = np.array([
            [row['r11'], row['r12'], row['r13'], row['tx']],
            [row['r21'], row['r22'], row['r23'], row['ty']],
            [row['r31'], row['r32'], row['r33'], row['tz']],
            [row['h41'], row['h42'], row['h43'], row['h44']]
        ])
        print(transformation_matrix)
        
    # Save transformation matrices visualization
    num_solutions = len(transformation_data)
    if num_solutions == 1:
        # Single solution - create a single plot
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        row = transformation_data.iloc[0]
        transformation_matrix = np.array([
            [row['r11'], row['r12'], row['r13'], row['tx']],
            [row['r21'], row['r22'], row['r23'], row['ty']],
            [row['r31'], row['r32'], row['r33'], row['tz']],
            [row['h41'], row['h42'], row['h43'], row['h44']]
        ])
        
        im = ax.imshow(transformation_matrix, cmap='RdBu', vmin=-1, vmax=1)
        ax.set_title('Transformation Matrix')
        
        # Add text annotations
        for (j, k), val in np.ndenumerate(transformation_matrix):
            ax.text(k, j, f'{val:.3f}', ha='center', va='center', 
                   color='white' if abs(val) > 0.5 else 'black', fontsize=10)
        
        plt.colorbar(im, ax=ax)
        plt.tight_layout()
    else:
        # Multiple solutions - create subplot grid
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        axes = axes.flatten()
        
        for i, row in transformation_data.iterrows():
            if i < len(axes):
                transformation_matrix = np.array([
                    [row['r11'], row['r12'], row['r13'], row['tx']],
                    [row['r21'], row['r22'], row['r23'], row['ty']],
                    [row['r31'], row['r32'], row['r33'], row['tz']],
                    [row['h41'], row['h42'], row['h43'], row['h44']]
                ])
                
                im = axes[i].imshow(transformation_matrix, cmap='RdBu', vmin=-1, vmax=1)
                axes[i].set_title(f'Transformation Matrix {i+1}')
                
                # Add text annotations
                for (j, k), val in np.ndenumerate(transformation_matrix):
                    axes[i].text(k, j, f'{val:.3f}', ha='center', va='center', 
                               color='white' if abs(val) > 0.5 else 'black', fontsize=8)
                
                plt.colorbar(im, ax=axes[i])
        
        plt.tight_layout()
    
    plt.savefig(f"{name_of_folder}/transformation_matrices.png", dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    main()