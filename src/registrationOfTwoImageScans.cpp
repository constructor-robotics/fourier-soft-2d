//
// Created by tim-linux on 26.03.22.
//

//
// Created by jurobotics on 13.09.21.
//
// Example usage:
// ./registrationOfTwoImageScans img1.jpg img2.jpg
// ./registrationOfTwoImageScans folder1/scan1.png folder2/scan2.png --debug true
#include "softDescriptorRegistration.h"
#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui.hpp>
#include <filesystem>
#include <chrono>
#include <cmath>
#include <iostream>
#include <string>
#include <fstream>
#include <iomanip>
#include <sstream>

// Structure to hold experiment data for logging
struct ExperimentData {
    std::string timestamp_utc;
    std::string first_image_name;
    std::string second_image_name;
    int original_img1_width;
    int original_img1_height;
    int original_img2_width;
    int original_img2_height;
    int scaled_width;
    int scaled_height;
    bool debug_enabled;
    std::string output_directory_relative;
    double execution_time_seconds;
    bool registration_successful;
    int best_solution_index;
};

std::string getCurrentUTCTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()) % 1000;
    
    std::stringstream ss;
    ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%d %H:%M:%S");
    ss << "." << std::setfill('0') << std::setw(3) << ms.count() << " UTC";
    
    return ss.str();
}

bool fileExists(const std::string& filePath) {
    std::ifstream file(filePath);
    return file.good();
}

void writeExperimentLog(const ExperimentData& data, const std::string& outputDir) {
    std::string csvFilePath = outputDir + "/experiment_task_logs.csv";
    bool fileExisted = fileExists(csvFilePath);
    
    std::ofstream csvFile;
    csvFile.open(csvFilePath, std::ios::app); // Append mode
    
    if (!csvFile.is_open()) {
        std::cerr << "Warning: Could not create/open experiment log file: " << csvFilePath << std::endl;
        return;
    }
    
    // Write header if file is new
    if (!fileExisted) {
        csvFile << "timestamp_utc,first_image_name,second_image_name,"
                << "original_img1_width,original_img1_height,original_img2_width,original_img2_height,"
                << "scaled_width,scaled_height,debug_enabled,output_directory_relative,"
                << "execution_time_seconds,registration_successful,best_solution_index\n";
    }
    
    // Write data row
    csvFile << "\"" << data.timestamp_utc << "\","
            << "\"" << data.first_image_name << "\","
            << "\"" << data.second_image_name << "\","
            << data.original_img1_width << ","
            << data.original_img1_height << ","
            << data.original_img2_width << ","
            << data.original_img2_height << ","
            << data.scaled_width << ","
            << data.scaled_height << ","
            << (data.debug_enabled ? "true" : "false") << ","
            << "\"" << data.output_directory_relative << "\","
            << std::fixed << std::setprecision(3) << data.execution_time_seconds << ","
            << (data.registration_successful ? "true" : "false") << ","
            << data.best_solution_index << "\n";
    
    csvFile.close();
    
    std::cout << "Experiment log written to: " << csvFilePath << std::endl;
}

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

int getClosestPowerOfTwo(int value) {
    // Find the closest power of 2 that is equal or less than the value
    if (value <= 0) return 1;
    
    int powerOfTwo = 1;
    while (powerOfTwo * 2 <= value) {
        powerOfTwo *= 2;
    }
    return powerOfTwo;
}

bool isPowerOfTwo(int value) {
    return value > 0 && (value & (value - 1)) == 0;
}

std::string resolveInputPath(const std::string& relativePath) {
    // Base input directory
    const std::string baseInputDir = "/workspace/input";
    
    // If the path is already absolute (starts with /), return as is
    if (!relativePath.empty() && relativePath[0] == '/') {
        return relativePath;
    }
    
    // Otherwise, prepend the base input directory
    return baseInputDir + "/" + relativePath;
}

void printUsage(const std::string& programName) {
    std::cout << "Usage: " << programName << " <first_image> <second_image> [options]" << std::endl;
    std::cout << std::endl;
    std::cout << "Image paths:" << std::endl;
    std::cout << "  All image paths are relative to /workspace/input/" << std::endl;
    std::cout << "  Examples:" << std::endl;
    std::cout << "    'image1.jpg' resolves to '/workspace/input/image1.jpg'" << std::endl;
    std::cout << "    'folder/scan.png' resolves to '/workspace/input/folder/scan.png'" << std::endl;
    std::cout << std::endl;
    std::cout << "Options:" << std::endl;
    std::cout << "  --output-dir <dir_name>   Output directory name (default: current UNIX timestamp)" << std::endl;
    std::cout << "  --dimensions <N>          Image dimensions (must be power of 2, default: auto-detect)" << std::endl;
    std::cout << "  --debug <true|false>      Enable debug mode (default: false)" << std::endl;
    std::cout << "  --help                    Show this help message" << std::endl;
    std::cout << std::endl;
    std::cout << "Examples:" << std::endl;
    std::cout << "  " << programName << " img1.jpg img2.jpg" << std::endl;
    std::cout << "  " << programName << " scans/img1.jpg scans/img2.jpg --debug true" << std::endl;
    std::cout << "  " << programName << " folder1/scan1.png folder2/scan2.png --output-dir my_results --dimensions 256" << std::endl;
}

int main(int argc, char **argv) {
    // Initialize experiment data structure
    ExperimentData experimentData;
    experimentData.timestamp_utc = getCurrentUTCTimestamp();
    experimentData.registration_successful = false;
    experimentData.best_solution_index = -1;
    
    // Start timing the execution
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // Default values
    std::string outputDirName = "";
    int dimensionScan = -1; // -1 means auto-detect
    bool debug = false;
    std::string firstImageRelativePath = "";
    std::string secondImageRelativePath = "";

    // Parse command line arguments
    if (argc < 3) {
        std::cout << "Error: Not enough arguments provided" << std::endl;
        printUsage(argv[0]);
        return -1;
    }

    // First two arguments are always the image paths (relative to /workspace/input)
    firstImageRelativePath = argv[1];
    secondImageRelativePath = argv[2];

    // Store image names for logging
    experimentData.first_image_name = firstImageRelativePath;
    experimentData.second_image_name = secondImageRelativePath;

    // Parse optional arguments
    for (int i = 3; i < argc; i++) {
        std::string arg = argv[i];
        
        if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return 0;
        }
        else if (arg == "--output-dir") {
            if (i + 1 < argc) {
                outputDirName = argv[++i];
            } else {
                std::cout << "Error: --output-dir requires a directory name" << std::endl;
                return -1;
            }
        }
        else if (arg == "--dimensions") {
            if (i + 1 < argc) {
                try {
                    dimensionScan = std::stoi(argv[++i]);
                } catch (const std::exception& e) {
                    std::cout << "Error: Invalid dimensions value: " << argv[i] << std::endl;
                    return -1;
                }
            } else {
                std::cout << "Error: --dimensions requires a numeric value" << std::endl;
                return -1;
            }
        }
        else if (arg == "--debug") {
            if (i + 1 < argc) {
                std::string debugStr = argv[++i];
                if (debugStr == "true" || debugStr == "1") {
                    debug = true;
                } else if (debugStr == "false" || debugStr == "0") {
                    debug = false;
                } else {
                    std::cout << "Error: Invalid debug value. Use 'true' or 'false'" << std::endl;
                    return -1;
                }
            } else {
                std::cout << "Error: --debug requires a boolean value (true/false)" << std::endl;
                return -1;
            }
        }
        else {
            std::cout << "Error: Unknown argument: " << arg << std::endl;
            printUsage(argv[0]);
            return -1;
        }
    }

    // Store debug setting
    experimentData.debug_enabled = debug;

    // Resolve full paths
    std::string firstImagePath = resolveInputPath(firstImageRelativePath);
    std::string secondImagePath = resolveInputPath(secondImageRelativePath);

    std::cout << "Loading images:" << std::endl;
    std::cout << "  First image:  " << firstImageRelativePath << " -> " << firstImagePath << std::endl;
    std::cout << "  Second image: " << secondImageRelativePath << " -> " << secondImagePath << std::endl;

    // Check if input files exist
    if (!std::filesystem::exists(firstImagePath)) {
        std::cout << "Error: First image file does not exist: " << firstImagePath << std::endl;
        std::cout << "Make sure the file is in the /workspace/input directory" << std::endl;
        return -1;
    }

    if (!std::filesystem::exists(secondImagePath)) {
        std::cout << "Error: Second image file does not exist: " << secondImagePath << std::endl;
        std::cout << "Make sure the file is in the /workspace/input directory" << std::endl;
        return -1;
    }

    // Load images
    cv::Mat img1 = cv::imread(firstImagePath, cv::IMREAD_GRAYSCALE);
    cv::Mat img2 = cv::imread(secondImagePath, cv::IMREAD_GRAYSCALE);

    if (img1.empty()) {
        std::cout << "Error: Could not load first image: " << firstImagePath << std::endl;
        std::cout << "Make sure the file is a valid image format" << std::endl;
        return -1;
    }

    if (img2.empty()) {
        std::cout << "Error: Could not load second image: " << secondImagePath << std::endl;
        std::cout << "Make sure the file is a valid image format" << std::endl;
        return -1;
    }

    // Store original image dimensions
    experimentData.original_img1_width = img1.cols;
    experimentData.original_img1_height = img1.rows;
    experimentData.original_img2_width = img2.cols;
    experimentData.original_img2_height = img2.rows;

    std::cout << "Images loaded successfully!" << std::endl;
    std::cout << "  First image size:  " << img1.cols << "x" << img1.rows << std::endl;
    std::cout << "  Second image size: " << img2.cols << "x" << img2.rows << std::endl;

    // Determine dimensions
    if (dimensionScan == -1) {
        // Auto-detect: use the smaller dimension of the first image
        int maxDim = std::max(img1.rows, img1.cols);
        dimensionScan = getClosestPowerOfTwo(maxDim);
        std::cout << "Auto-detected dimensions: " << dimensionScan << " (closest power of 2 to max dimension " << maxDim << ")" << std::endl;
    } else {
        // Check if provided dimension is power of 2
        if (!isPowerOfTwo(dimensionScan)) {
            int originalDim = dimensionScan;
            int maxDim = std::max(img1.rows, img1.cols);
            dimensionScan = getClosestPowerOfTwo(std::min(dimensionScan, maxDim));
            std::cout << "Warning: Provided dimension " << originalDim << " is not a power of 2." << std::endl;
            std::cout << "Adjusted to closest power of 2: " << dimensionScan << std::endl;
    }
    }

    // Store scaled dimensions
    experimentData.scaled_width = dimensionScan;
    experimentData.scaled_height = dimensionScan;

    // Resize images if necessary
    cv::Mat resizedImg1, resizedImg2;
    if (img1.rows != dimensionScan || img1.cols != dimensionScan) {
        cv::resize(img1, resizedImg1, cv::Size(dimensionScan, dimensionScan));
        std::cout << "Resized first image from " << img1.cols << "x" << img1.rows 
                  << " to " << dimensionScan << "x" << dimensionScan << std::endl;
    } else {
        resizedImg1 = img1;
    }

    if (img2.rows != dimensionScan || img2.cols != dimensionScan) {
        cv::resize(img2, resizedImg2, cv::Size(dimensionScan, dimensionScan));
        std::cout << "Resized second image from " << img2.cols << "x" << img2.rows 
                  << " to " << dimensionScan << "x" << dimensionScan << std::endl;
    } else {
        resizedImg2 = img2;
    }

    // Create output directory
    std::string baseOutputDir = "/workspace/output";
    
    if (outputDirName.empty()) {
        // Use current UNIX timestamp
        auto now = std::chrono::system_clock::now();
        auto timestamp = std::chrono::duration_cast<std::chrono::seconds>(now.time_since_epoch()).count();
        outputDirName = std::to_string(timestamp);
    }
    
    std::string fullOutputDir = baseOutputDir + "/" + outputDirName;
    
    // Store relative output directory path for logging
    experimentData.output_directory_relative = outputDirName;
    
    try {
        std::filesystem::create_directories(fullOutputDir);
        std::cout << "Created output directory: " << fullOutputDir << std::endl;
    } catch (const std::exception& e) {
        std::cout << "Error creating output directory: " << e.what() << std::endl;
        return -1;
    }

    std::cout << "\nRegistration Parameters:" << std::endl;
    std::cout << "  Voxel size: " << dimensionScan << "x" << dimensionScan << std::endl;
    std::cout << "  Debug mode: " << (debug ? "enabled" : "disabled") << std::endl;
    std::cout << "  Output directory: " << fullOutputDir << std::endl;

    // Allocate memory for voxel data
    double *voxelData1;
    double *voxelData2;
    voxelData1 = (double *) malloc(sizeof(double) * dimensionScan * dimensionScan);
    voxelData2 = (double *) malloc(sizeof(double) * dimensionScan * dimensionScan);

    if (voxelData1 == nullptr || voxelData2 == nullptr) {
        std::cout << "Error: Failed to allocate memory for voxel data" << std::endl;
        if (voxelData1) free(voxelData1);
        if (voxelData2) free(voxelData2);
        return -1;
    }

    // Convert images to voxel data
    convertMatToDoubleArray(resizedImg1, voxelData1);
    convertMatToDoubleArray(resizedImg2, voxelData2);

    // Create registration object
    softDescriptorRegistration scanRegistrationObject(dimensionScan, dimensionScan / 2, dimensionScan / 2, dimensionScan / 2 - 1);

    std::cout << "\nStarting registration process..." << std::endl;

    int bestSolutionIndex = -1; // This will be set to the index of the best solution found
    try {
        // Perform registration
        // use initial guess yes/no Currently set to no. Therefore, global registration is happening.
        Eigen::Matrix4d estimatedTransformation = scanRegistrationObject.registrationOfTwoVoxelsSOFTFast(voxelData1,
                                                                                                        voxelData2,
                                                                                                        Eigen::Matrix4d::Identity(),
                                                                                                        false, false,
                                                                                                        1,
                                                                                                        fullOutputDir,
                                                                                                        bestSolutionIndex,
                                                                                                        debug);

        std::cout << "\nEstimated Transformation:" << std::endl;
        std::cout << estimatedTransformation << std::endl;

        // Mark registration as successful
        experimentData.registration_successful = true;
        experimentData.best_solution_index = bestSolutionIndex;
        
        // Output JSON result as the very last line
        std::cout << "{\"solution_index\":" << bestSolutionIndex << "}" << std::endl;

    } catch (const std::exception& e) {
        std::cout << "Error during registration: " << e.what() << std::endl;
        experimentData.registration_successful = false;
    }

    // Calculate execution time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    experimentData.execution_time_seconds = duration.count() / 1000.0;

    // Clean up memory
    free(voxelData1);
    free(voxelData2);

    // Write experiment log
    writeExperimentLog(experimentData, fullOutputDir);

    if (experimentData.registration_successful) {
    std::cout << "Registration completed successfully!" << std::endl;
    } else {
        std::cout << "Registration failed!" << std::endl;
    }
    
    std::cout << "Results saved in: " << fullOutputDir << std::endl;
    std::cout << "Execution time: " << experimentData.execution_time_seconds << " seconds" << std::endl;

    // Output JSON result as the very last line -- IMPORTANT: This must be the very last line of output
    std::cout << "{\"solution_index\":" << bestSolutionIndex << "}" << std::endl;

    return experimentData.registration_successful ? 0 : -1;
}