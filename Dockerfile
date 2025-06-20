# Use Ubuntu 20.04 as base image
FROM ubuntu:20.04

# Set environment variables to avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Update package lists and install essential build tools
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    cmake \
    git \
    wget \
    curl \
    pkg-config \
    software-properties-common 
    
# C/C++ compilers and tools
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gdb \
    make \
    ninja-build

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
    libboost-all-dev \
    # OpenCV (often used with PCL)
    libopencv-dev

# Additional useful tools
RUN apt-get update && apt-get install -y \
    vim \
    nano \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Verify PCL installation and get version info
RUN pkg-config --modversion pcl_common-1.10 || echo "PCL version check failed, but PCL should be installed"

# Set default command
CMD ["/bin/bash"]

# Labels for documentation
LABEL maintainer="Arturo Gomez-Chavez <agomezchav@constructor.university>"
LABEL description="Ubuntu 20.04 with PCL 1.10 and C/C++ development tools"
LABEL version="1.0"