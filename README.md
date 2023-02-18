# Fourier-SOFT-2D
Implementation of Fourier-SOFT-2D registration, with intermediate steps of the registration process.
These can be plotted with the help of the matlab file provided.
PCL implementation just converts PCL to Voxel data.




Required packages:
* OpenCV
* Point Cloud Library
* OpenMP
* FFTW3
* CGAL




Start registration Voxel Based:
* `fourier_soft2D "scan1.jpg" "scan2.jpg" "outputFolderResults"`
* `fourier_soft2D inputFiles/voxelScan1.jpg inputFiles/voxelScan2.jpg tools/matlabVisualization/out`

The size `N` is described by the size of the image. It has to be the size of `N = 2^k`
The example images are of size `N = 256`

Start registration PCL Based(worse results):
* `fourier_soft2D_pcl "scan1.pcd" "scan2.pcd" "outputFolderResults" "dimensionRegistration"`
* Example: `fourier_soft2D_pcl inputFiles/scan1.pcd  inputFiles/scan2.pcd tools/matlabVisualization/out 256`


