import os
# Set environment variables before importing matplotlib to ensure headless operation. i.e., to avoid GUI backend issues.
os.environ['MPLBACKEND'] = 'Agg'
os.environ['DISPLAY'] = ''

import numpy as np
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

def main():
    
    name_of_folder = "/workspace/output"
    
    # Ensure output directory exists
    os.makedirs(name_of_folder, exist_ok=True)
    
    # Read magnitude and phase data for FFT
    magnitude_fftw1 = np.loadtxt(f"{name_of_folder}/magnitudeFFTW1.csv", delimiter=',')
    N = int(np.sqrt(len(magnitude_fftw1)))
    
    phase_fftw1 = np.loadtxt(f"{name_of_folder}/phaseFFTW1.csv", delimiter=',')
    voxel_data_used1 = np.loadtxt(f"{name_of_folder}/voxelDataFFTW1.csv", delimiter=',')
    
    magnitude_fftw2 = np.loadtxt(f"{name_of_folder}/magnitudeFFTW2.csv", delimiter=',')
    phase_fftw2 = np.loadtxt(f"{name_of_folder}/phaseFFTW2.csv", delimiter=',')
    voxel_data_used2 = np.loadtxt(f"{name_of_folder}/voxelDataFFTW2.csv", delimiter=',')
    
    # Initialize matrices
    magnitude1 = np.zeros((N, N))
    phase1 = np.zeros((N, N))
    voxel_data1 = np.zeros((N, N))
    magnitude2 = np.zeros((N, N))
    phase2 = np.zeros((N, N))
    voxel_data2 = np.zeros((N, N))
    
    # Reshape data from 1D to 2D (MATLAB indexing conversion)
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
    
    # Read resampled sphere data
    resampled_data_sphere1 = np.loadtxt(f"{name_of_folder}/resampledVoxel1.csv", delimiter=',')
    resampled_data_sphere2 = np.loadtxt(f"{name_of_folder}/resampledVoxel2.csv", delimiter=',')
    
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
    correlation_of_angles = np.loadtxt(f"{name_of_folder}/resultingCorrelation1D.csv", delimiter=',')
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
    
    # Read data information
    data_information = np.loadtxt(f"{name_of_folder}/dataForReadIn.csv", delimiter=',')
    number_of_solutions = int(data_information[0])
    best_solution = int(data_information[1])+1 # MATLAB figures are 1-indexed
    
    # Save Figure 8: Correlation matrices for all solutions
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for i in range(number_of_solutions):
        correlation_matrix_shift_1d = np.loadtxt(
            f"{name_of_folder}/resultingCorrelationShift{i}.csv", delimiter=','
        )
        result_size = int(np.round(len(correlation_matrix_shift_1d) ** (1/2)))
        correlation_matrix_shift_2d = correlation_matrix_shift_1d.reshape(result_size, result_size)
        
        X, Y = np.meshgrid(range(result_size), range(result_size))
        
        if i < len(axes):
            im = axes[i].imshow(correlation_matrix_shift_2d, cmap='viridis')
            axes[i].set_title(f'Solution {i+1}')
            axes[i].set_aspect('equal')
            plt.colorbar(im, ax=axes[i])
    
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/correlation_matrices.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # Save Figure 9: Registration results (blended voxels)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()
    
    for i in range(number_of_solutions):
        result_voxel1_tmp = np.loadtxt(f"{name_of_folder}/resultVoxel1{i}.csv", delimiter=',')
        result_voxel2_tmp = np.loadtxt(f"{name_of_folder}/resultVoxel2{i}.csv", delimiter=',')
        
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
        voxel1_color = cv2.applyColorMap(voxel1_norm.astype(np.uint8), cv2.COLORMAP_JET)
        voxel2_color = cv2.applyColorMap(voxel2_norm.astype(np.uint8), cv2.COLORMAP_VIRIDIS)
        
        # Blend the images
        blended = cv2.addWeighted(voxel1_color, 0.5, voxel2_color, 0.5, 0)
        
        if i < len(axes):
            axes[i].imshow(cv2.cvtColor(blended, cv2.COLOR_BGR2RGB))
            axes[i].set_title(f'Registration Result {i+1}')
            axes[i].set_aspect('equal')
            axes[i].axis('off')
    
    plt.tight_layout()
    plt.savefig(f"{name_of_folder}/registration_results.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"All visualizations have been saved to the '{name_of_folder}' folder.")
    print(f"Number of solutions: {number_of_solutions}")
    print(f"Best solution: {best_solution}")

if __name__ == "__main__":
    main()