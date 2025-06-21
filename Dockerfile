# Use Ubuntu 20.04 as base image
FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install essential build tools
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    git \
    wget \
    curl \
    pkg-config \
    software-properties-common \
    lsb-release \
    unzip \
    libtool \
    autoconf \
    # Dependencies for building CMake
    libssl-dev

# Install CMake 3.21.1 (removing default cmake first if it exists)
RUN apt purge --auto-remove -y cmake && \
    wget https://cmake.org/files/v3.21/cmake-3.21.1.tar.gz && \
    tar -xzvf cmake-3.21.1.tar.gz && \
    cd cmake-3.21.1 && \
    ./bootstrap && \ 
    make -j$(nproc) && \
    make install

# C/C++ compilers and tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdb \
    make \
    ninja-build

# OpenMP support (usually included with gcc, but ensure libomp-dev is available)
RUN apt-get update && apt-get install -y \
    libomp-dev \
    libomp5

# PCL dependencies
RUN apt-get update && apt-get install -y \    
    libpcl-dev \
    #libpcl-tools \
    # Additional libraries that PCL depends on
    libeigen3-dev \
    libflann-dev \
    libvtk7-dev \
    libqhull-dev \
    libusb-1.0-0-dev \
    libgtest-dev \
    # Boost libraries
    libboost-all-dev 

# OpenCV (comprehensive installation)
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    libopencv-contrib-dev \
    # OpenCV dependencies
    libgtk-3-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libv4l-dev \
    libxvidcore-dev \
    libx264-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libatlas-base-dev \
    python3-dev \
    python3-numpy

# FFTW3 (Fast Fourier Transform library)
RUN apt-get update && apt-get install -y \
    libfftw3-dev \
    libfftw3-doc

# CGAL (Computational Geometry Algorithms Library)
RUN apt-get update && apt-get install -y \
    libcgal-dev \
    libcgal-qt5-dev \
    # CGAL dependencies
    libgmp-dev \
    libmpfr-dev \
    # Qt5 for CGAL GUI components (optional)
    qtbase5-dev \
    libqt5opengl5-dev

# Additional useful tools
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Verify installations
RUN echo "=== Verifying library installations ===" && \
    (cmake --version | head -1 && echo "✓ CMake 3.21.1 installed") || echo "✗ CMake NOT properly installed" && \
    (pkg-config --modversion pcl_common-1.10 && echo "✓ PCL installed") || echo "✗ PCL NOT properly installed" && \
    (pkg-config --modversion opencv4 || pkg-config --modversion opencv) && echo "✓ OpenCV installed" || echo "✗ OpenCV NOT properly installed" && \
    (pkg-config --modversion fftw3 && echo "✓ FFTW3 installed") || echo "✗ FFTW3 NOT properly installed" && \
    (gcc -fopenmp --version >/dev/null 2>&1 && echo "✓ OpenMP support available") || echo "✗ OpenMP NOT available" && \
    (find /usr -name "CGAL" -type d 2>/dev/null | head -1 >/dev/null && echo "✓ CGAL installed") || echo "✗ CGAL NOT properly installed"


# Set up environment variables for development
ENV PKG_CONFIG_PATH="/usr/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH"
ENV LD_LIBRARY_PATH="/usr/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

# Create a workspace directory
WORKDIR /workspace

# Set default command
CMD ["/bin/bash"]

# Labels for documentation
LABEL maintainer="Arturo Gomez-Chavez <agomezchav@constructor.university>"
LABEL description="Ubuntu 20.04 with PCL 1.10 and C/C++ development tools"
LABEL version="1.0"