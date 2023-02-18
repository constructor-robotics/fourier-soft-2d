//
// Created by tim-linux on 26.03.22.
//

//
// Created by jurobotics on 13.09.21.
//
// /home/tim-external/dataFolder/StPereDataset/lowNoise52/scanNumber_0/00_ForShow.jpg /home/tim-external/dataFolder/StPereDataset/lowNoise52/scanNumber_1/00_ForShow.jpg
// /home/tim-external/dataFolder/ValentinBunkerData/noNoise305_52/scanNumber_0/00_ForShow.jpg  /home/tim-external/dataFolder/ValentinBunkerData/noNoise305_52/scanNumber_1/00_ForShow.jpg
#include "softDescriptorRegistration.h"
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>
#include <filesystem>

void convertMatToDoubleArray(cv::Mat inputImg, double voxelData[]) {
    // takes input cv::Mat and convert it to double array
    std::vector<uchar> array;
    if (inputImg.isContinuous()) {
        array.assign(inputImg.data, inputImg.data + inputImg.total() * inputImg.channels());
    } else {
        for (int i = 0; i < inputImg.rows; ++i) {
            array.insert(array.end(), inputImg.ptr<uchar>(i),
                         inputImg.ptr<uchar>(i) + inputImg.cols * inputImg.channels());
        }
    }

    for (int i = 0; i < array.size(); i++) {
        voxelData[i] = array[i];
    }

}


int main(int argc, char **argv) {
    // input needs to be two scans as voxelData

    bool debug = true;

    std::string current_exec_name = argv[0]; // Name of the current exec program
    std::vector<std::string> all_args;

    if (argc > 3) {
        // arguments are: first_image second_image output_dir
        // size N is based on image
        all_args.assign(argv + 1, argv + argc);
    } else {
        std::cout << "not enough arguments given" << std::endl;
        exit(-1);
    }


    cv::Mat img1 = cv::imread(
            all_args[0],
            cv::IMREAD_GRAYSCALE);
    cv::Mat img2 = cv::imread(
            all_args[1],
            cv::IMREAD_GRAYSCALE);

    std::string outputDir = all_args[2];
    int dimensionScan = img1.rows;
    std::cout << "Voxel size: " << dimensionScan << std::endl;

    double *voxelData1;
    double *voxelData2;
    voxelData1 = (double *) malloc(sizeof(double) * dimensionScan * dimensionScan);
    voxelData2 = (double *) malloc(sizeof(double) * dimensionScan * dimensionScan);

    convertMatToDoubleArray(img1, voxelData1);
    convertMatToDoubleArray(img2, voxelData2);

    softDescriptorRegistration scanRegistrationObject(img1.rows, img1.rows / 2, img1.rows / 2, img1.rows / 2 - 1);


    // use initial guess yes/no Currently set to no. Therefore, global registration is happening.
    Eigen::Matrix4d estimatedTransformation = scanRegistrationObject.registrationOfTwoVoxelsSOFTFast(voxelData1,
                                                                                                      voxelData2,
                                                                                                      Eigen::Matrix4d::Identity(),
                                                                                                      false, false,
                                                                                                      1,
                                                                                                     outputDir,
                                                                                                     debug);


    std::cout << "Estimated Transformation:" << std::endl;

    std::cout << estimatedTransformation << std::endl;

    free(voxelData1);
    free(voxelData2);


    return (0);
}
