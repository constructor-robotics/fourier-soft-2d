# Fourier-SOFT-2D Registration
Implementation of Fourier-SOFT-2D registration, with intermediate steps of the registration process.
This project provides tools for aligning and stitching images using advanced frequency domain techniques, including batch processing capabilities for sequential image sequences.

## Installation

### Prerequisites
- Docker
- Docker Compose
- Git

### Build and Run the Container

1. **Clone the repository** (or navigate to your project directory)
   ```bash
   cd your-project-directory
   ```

2. **Build the Docker container**
   ```bash
   docker-compose build
   ```

3. **Start the container**
   ```bash
   docker-compose up -d
   ```

   This will:
   - Build the Ubuntu 20.04 container with all dependencies
   - Mount `./input` and `./output` directories
   - Start the FastAPI web application on port 8090
   - Keep the container running in the background

4. **Verify the container is running**
   ```bash
   docker-compose ps
   ```
   and/or

   ```bash
   docker-compose logs -f
   ```

## Running the FastAPI Application

### Access the Web Interface

Once the container is running, you can access the FastAPI application in your browser:

- **API Documentation (Swagger UI)**: http://localhost:8090/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8090/redoc
- **API Base URL**: http://localhost:8090

The FastAPI interface provides interactive documentation where you can:
- View all available endpoints
- Test API calls directly from the browser
- Upload files and execute registration workflows
- Download results

### Container Management

- **View logs**: `docker-compose logs -f`
- **Stop the container**: `docker-compose down`
- **Restart the container**: `docker-compose restart`
- **Access container shell**: `docker exec -it fourier-sof-2d bash`

## Quick Start Example

1. Place your images in the `input/` directory
2. Access http://localhost:8090/docs
3. Use the API to run registration on your image pair
4. Check the `output/` directory for results
5. Run visualization and stitching tools through the web interface

## Dependencies

The container includes all necessary dependencies:
- OpenCV 4.x
- PCL (Point Cloud Library)
- FFTW3 (Fast Fourier Transform)
- CGAL (Computational Geometry)
- Eigen3, Boost
- Python 3 with NumPy, SciPy, Matplotlib, Pandas
- FastAPI and Uvicorn

## Main Services and Tools

The system provides six main services for image registration, analysis, and batch processing:

### 1. **fourier-soft2D**

**Purpose**: Core image registration engine that performs 2D image alignment using SOFT descriptors.

- Loads two grayscale images and computes optimal transformation (rotation + translation)
- Uses Fourier transform and spherical harmonic analysis for robust feature matching

**Output Files**:
- `registration_solutions_transformation.csv` - Contains the computed 4x4 transformation matrix elements (r11-r33, tx, ty, tz, h41-h44) for each solution found
- `rotation_analysis_results.csv` - (Debug mode only) Raw data including magnitude and phase FFT components, voxel data, resampled sphere data, and 1D correlation results
- `registration_logs.csv` - (Debug mode only) Comprehensive registration data with correlation shift matrices, result voxel data for each solution, number of solutions found, and index of the best solution

### 2. **plot-registration**

**Purpose**: Visualization and analysis tool for registration results.

- Generates comprehensive plots and visualizations of registration outcomes
- Creates correlation matrices, magnitude spectra, and phase analysis charts

**Output Files**:
- `magnitude_voxel1.png` / `magnitude_voxel2.png` - (Debug mode only) FFT magnitude spectrum visualizations for both input images
- `voxel_data1.png` / `voxel_data2.png` - (Debug mode only) Original voxel data representations of the input images
- `resampled_sphere1_3d.png` / `resampled_sphere2_3d.png` - (Debug mode only) 3D sphere visualizations of resampled magnitude data (falls back to 2D if 3D rendering fails)
- `correlation_angles.png` - (Debug mode only) 1D correlation plot showing angle-correlation relationship with detected peaks
- `correlation_matrices.png` - (Debug mode only) Grid of 2D correlation matrices for all computed solutions
- `registration_results.png` - (Debug mode only) Color-blended visualization showing registration results for each solution (hot/cool colormap overlay)
- `transformation_matrices.png` - Heatmap visualization of transformation matrices with numerical values overlaid (single plot for one solution, 2x2 grid for multiple solutions)

### 3. **image-stitching**

**Purpose**: Image blending and stitching tool that applies computed transformations.

- Takes registration results and performs actual image alignment and blending
- Applies rotation and translation transformations
- Creates both original and colormap-enhanced blended images
- Supports canvas size adjustment for full transformation visibility
- Includes scaling compensation for resolution differences between registration and stitching images

**Output Files**:
- `stitched_originals_blend.png` - Final blended image using original image colors and intensities, with 50/50 averaging in overlap regions
- `stitched_colormaps_blend.png` - Color-enhanced blended image where the first image is mapped to a hot colormap (red/yellow tones) and the second image to a cool colormap (blue/cyan tones), enabling visual distinction between the two sources in the final blend
- If scaling is enabled, filenames include scaling suffix (e.g., `stitched_originals_blend_scaled_0.500x0.500.png`)

### 4. **batch-fourier-soft2d**

**Purpose**: Batch processing service for sequential numbered image pairs with automated CSV merging.

- Detects numbered images matching patterns (e.g., image_001.png, image_002.png)
- Creates sequential pairs automatically: (image_001.png, image_002.png), (image_002.png, image_003.png), etc.
- Processes each pair through fourier_soft2D with unique UUID tracking
- Merges all individual CSV results into consolidated batch files
- Supports concurrent processing for improved performance

**Process Overview**:
1. Auto-detects numbered images in specified directory
2. Creates sequential image pairs
3. Processes each pair through fourier_soft2D (debug=false by default)
4. Assigns unique UUID to each pair for experiment tracking
5. Merges registration results and experiment logs
6. Cleans up temporary directories

**Output Structure**:
```
/workspace/output/{output_dir}/
├── batch_registration_solutions.csv      # Merged registration results with UUIDs
└── batch_experiment_task_logs.csv        # Merged experiment logs with UUIDs
```

### 5. **batch-image-stitching**

**Purpose**: Progressive batch image stitching using fourier registration results.

- Loads batch CSV files from fourier processing results
- Performs progressive stitching: img1+img2 → result1, result1+img3 → result2, etc.
- Calculates scaling factors automatically from original vs processed dimensions
- Produces final combined image from entire sequence
- Supports debug mode with intermediate iteration results

**Progressive Stitching Logic**:
- **Iteration 1**: original_img1 + original_img2 → stitched_result1
- **Iteration 2**: stitched_result1 + original_img3 → stitched_result2  
- **Iteration 3**: stitched_result2 + original_img4 → stitched_result3
- **...and so on**

**Output Structure**:
```
/workspace/output/{registration_solution_dir}/
├── debug/                                    # (if debug=true)
│   ├── 001_iteration/
│   │   ├── stitched_originals_blend.png
│   │   └── stitched_colormaps_blend.png
│   ├── 002_iteration/
│   │   └── ...
│   └── ...
└── batch_registration_{first}_to_{last}_image_stitched.png  # Final result
```

