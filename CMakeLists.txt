cmake_minimum_required(VERSION 3.21)
set(CMAKE_CXX_FLAGS_RELEASE "-O3")
set(CMAKE_CXX_STANDARD 20)


project(fourier_soft2D)


find_package( PCL 1.10 REQUIRED COMPONENTS common io )
find_package( OpenCV REQUIRED )
find_package( OpenMP REQUIRED )
set(SOURCE_FILES
        soft20/src/lib1/rotate_so3_fftw.c
        soft20/src/lib1/rotate_so3_utils.c
        soft20/src/lib1/s2_cospmls.c
        soft20/src/lib1/s2_legendreTransforms.c
        soft20/src/lib1/s2_semi_fly.c
        soft20/src/lib1/s2_semi_memo.c
        soft20/src/lib1/so3_correlate_fftw.c
        soft20/src/lib1/soft_fftw.c
        soft20/src/lib1/soft_fftw_nt.c
        soft20/src/lib1/soft_fftw_pc.c
        soft20/src/lib1/utils_vec_cx.c
        soft20/src/lib1/wignerTransforms_fftw.c
        soft20/src/lib1/wrap_s2_rotate_fftw.c
        soft20/src/lib1/wrap_soft_fftw.c
        soft20/src/lib1/wrap_soft_fftw_cor2.c

        soft20/src/common/csecond.c
        soft20/src/common/makeweights.c
        soft20/src/common/makeWigner.c
        soft20/src/common/s2_primitive.c
        soft20/src/common/utils_so3.c
        soft20/src/common/wignerTransforms.c

        registration/src/softCorrelationClass.cpp
        registration/src/softDescriptorRegistration.cpp

#        tools/src/generalHelpfulTools.cpp
        tools/src/PeakFinder.cpp
        )


include_directories(
        ${OpenCV_INCLUDE_DIRS}
        ${PCL_INCLUDE_DIRS}
        tools/include
        soft20/include
        soft20/include/soft20
        registration/include
)

add_executable(fourier_soft2D registrationOfTwoImageScans.cpp ${SOURCE_FILES})
target_link_libraries(fourier_soft2D fftw3 OpenMP::OpenMP_CXX  ${PCL_LIBRARIES} ${OpenCV_LIBS})


add_executable(fourier_soft2D_pcl registrationOfTwoPCLScans.cpp ${SOURCE_FILES})
target_link_libraries(fourier_soft2D_pcl fftw3 OpenMP::OpenMP_CXX  ${PCL_LIBRARIES} ${OpenCV_LIBS})

