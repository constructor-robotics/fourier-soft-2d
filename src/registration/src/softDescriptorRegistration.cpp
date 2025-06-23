//
// Created by tim-external on 01.03.22.
//

#include "softDescriptorRegistration.h"

bool compareTwoAngleCorrelation(angleAndCorrelation i1, angleAndCorrelation i2) {
    return (i1.angle < i2.angle);
}

std::vector<double> linspace(double start_in, double end_in, int num_in) {
    if (num_in < 0) {
        std::cout << "number of linspace negative" << std::endl;
        exit(-1);
    }
    std::vector<double> linspaced;

    double start = start_in;
    double end = end_in;
    auto num = (double) num_in;

    if (num == 0) { return linspaced; }
    if (num == 1) {
        linspaced.push_back(start);
        return linspaced;
    }

    double delta = (end - start) / (num - 1);//stepSize

    for (int i = 0; i < num - 1; ++i) {
        linspaced.push_back(start + delta * i);
    }
    linspaced.push_back(end); // I want to ensure that start and end
    // are exactly the same as the input
    return linspaced;
}


double thetaIncrement(double index, int bandwidth) {
    return M_PI * index / (2.0 * bandwidth);
}

double phiIncrement(double index, int bandwidth) {
    return M_PI * index / bandwidth;
}

double angleDifference(double angle1, double angle2) {//gives angle 1 - angle 2
    return atan2(sin(angle1 - angle2), cos(angle1 - angle2));
}


void
softDescriptorRegistration::PCL2Voxel(pcl::PointCloud<pcl::PointXYZ> &pointCloudInputData,
                                      double voxelData[], double fromTo) {
    for (int i = 0; i < this->N; i++) {
        for (int j = 0; j < this->N; j++) {
            voxelData[j + this->N * i] = 0.0;
        }
    }

    for (int i = 0; i < pointCloudInputData.points.size(); i++) {

        std::vector<double> vectorForSettingZeroX = linspace(0, pointCloudInputData.points[i].x, this->N);
        std::vector<double> vectorForSettingZeroY = linspace(0, pointCloudInputData.points[i].y, this->N);


        for (int j = 0; j < this->N - 1; j++) {
            double positionPointX = vectorForSettingZeroX[j];
            double positionPointY = vectorForSettingZeroY[j];
            double positionPointZ = 0;
            int indexX = (int) std::round((positionPointX + fromTo) / (fromTo * 2) * this->N) - 1;
            int indexY = (int) std::round((positionPointY + fromTo) / (fromTo * 2) * this->N) - 1;
            voxelData[indexY + N * indexX] = 0.01;

        }

    }
    for (int i = 0; i < pointCloudInputData.points.size(); i++) {

        double positionPointX = pointCloudInputData.points[i].x;
        double positionPointY = pointCloudInputData.points[i].y;
        double positionPointZ = 0;
        int indexX = (int) std::round((positionPointX + fromTo) / (fromTo * 2) * this->N) - 1;
        int indexY = (int) std::round((positionPointY + fromTo) / (fromTo * 2) * this->N) - 1;
        voxelData[indexY + this->N * indexX] = 1.0;
    }
}


double
softDescriptorRegistration::getSpectrumFromVoxelData2D(double voxelData[], double magnitude[], double phase[],
                                                       bool gaussianBlur) {


    if (gaussianBlur) {
        cv::Mat magTMP1(this->N, this->N, CV_64F, voxelData);
        //add gaussian blur
        cv::GaussianBlur(magTMP1, magTMP1, cv::Size(9, 9), 0);
//        cv::GaussianBlur(magTMP1, magTMP1, cv::Size(9, 9), 0);
//        cv::GaussianBlur(magTMP1, magTMP1, cv::Size(9, 9), 0);
    }



    //from voxel data to row and input for fftw
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            inputSpacialData[j + N * i][0] = voxelData[j + N * i]; // real part
            inputSpacialData[j + N * i][1] = 0; // imaginary part
        }
    }

    fftw_execute(planVoxelToFourier2D);

    //calc magnitude and phase
    double maximumMagnitude = 0;

    //get magnitude and find maximum
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            magnitude[j + N * i] = sqrt(
                    spectrumOut[j + N * i][0] *
                    spectrumOut[j + N * i][0] +
                    spectrumOut[j + N * i][1] *
                    spectrumOut[j + N * i][1]); // real part;
            if (maximumMagnitude < magnitude[j + N * i]) {
                maximumMagnitude = magnitude[j + N * i];
            }

            phase[j + N * i] = atan2(spectrumOut[j + N * i][1], spectrumOut[j + N * i][0]);

        }
    }


    return maximumMagnitude;
}

double softDescriptorRegistration::movePCLtoMiddle(pcl::PointCloud<pcl::PointXYZ> &pointCloudInputData,
                                                   Eigen::Matrix4d &transformationPCL) {
    //calc min circle for PCL1
    CGAL::Simple_cartesian<double>::Point_2 P1[pointCloudInputData.points.size()];
    for (int i = 0; i < pointCloudInputData.points.size(); ++i) {
        P1[i] = CGAL::Simple_cartesian<double>::Point_2(pointCloudInputData.points[i].x,
                                                        pointCloudInputData.points[i].y);
    }
    CGAL::Min_sphere_of_spheres_d<CGAL::Min_sphere_of_points_d_traits_2<CGAL::Simple_cartesian<double>, double>> mc1(P1,
                                                                                                                     P1 +
                                                                                                                     pointCloudInputData.points.size());
    CGAL::Min_sphere_of_spheres_d<CGAL::Min_sphere_of_points_d_traits_2<CGAL::Simple_cartesian<double>, double>>::Cartesian_const_iterator ccib1 = mc1.center_cartesian_begin(), ccie1 = mc1.center_cartesian_end();

    transformationPCL = Eigen::Matrix4d::Identity();
    transformationPCL(0, 3) = -*ccib1;//x change
    ccib1++;
    transformationPCL(1, 3) = -*ccib1;//y change

    pcl::transformPointCloud(pointCloudInputData, pointCloudInputData, transformationPCL);
    return mc1.radius();
}

Eigen::Matrix4d softDescriptorRegistration::registrationOfTwoPCL2D(pcl::PointCloud<pcl::PointXYZ> &pointCloudInputData1,
                                                                   pcl::PointCloud<pcl::PointXYZ> &pointCloudInputData2,
                                                                   Eigen::Matrix4d initialGuess,
                                                                   bool useInitialAngle,
                                                                   bool useInitialTranslation,
                                                                   std::string outputDir,
                                                                   bool debug) {


    Eigen::Matrix4d transformationPCL1, transformationPCL2;
    //calc min circle for PCLs and move to PCL to the center to not have empty space in Voxel Registration
    double radius1 = this->movePCLtoMiddle(pointCloudInputData1, transformationPCL1);

    double radius2 = this->movePCLtoMiddle(pointCloudInputData2, transformationPCL2);

    double *voxelData1Input;
    double *voxelData2Input;
    voxelData1Input = (double *) malloc(sizeof(double) * this->N * this->N);
    voxelData2Input = (double *) malloc(sizeof(double) * this->N * this->N);


    //transforms the point clouds to a different position dependent on minimum circle
    //get max radius
    double maxDistance = radius2;
    if (radius1 > maxDistance) {
        maxDistance = radius1;
    }
    //calc cell size for voxel
    double cellSize = std::round(maxDistance * 2.0 * 1.1 / N * 100.0) / 100.0;//make 10% bigger area

    this->PCL2Voxel(pointCloudInputData1, voxelData1Input, cellSize * this->N / 2);
    this->PCL2Voxel(pointCloudInputData2, voxelData2Input, cellSize * this->N / 2);


    //calc Voxel registration
    Eigen::Matrix4d estimatedTransformation = this->registrationOfTwoVoxelsSOFTFast(voxelData1Input,
                                                                                    voxelData2Input,
                                                                                    initialGuess,
                                                                                    useInitialAngle,
                                                                                    useInitialTranslation,
                                                                                    cellSize,
                                                                                    outputDir,
                                                                                    debug);
    free(voxelData1Input);
    free(voxelData2Input);

    // take into account the movement of the PCL in the beginning
    Eigen::Matrix4d finalTransformation =
            transformationPCL2.inverse() * estimatedTransformation.inverse() * transformationPCL1;
    return finalTransformation.inverse();//should be the transformation matrix from 1 to 2
}


double
softDescriptorRegistration::softRegistrationVoxel2DRotationOnly(double voxelData1Input[], double voxelData2Input[],
                                                                double goodGuessAlpha, std::string outputDir,
                                                                bool debug) {
    //calculate all possible rotations
    std::vector<double> allAnglesList = this->softRegistrationVoxel2DListOfPossibleRotations(voxelData1Input,
                                                                                             voxelData2Input, outputDir,
                                                                                             debug);
    //take the closest initial guess
    int indexCorrectAngle = 0;
    for (int i = 1; i < allAnglesList.size(); i++) {
        if (std::abs(angleDifference(allAnglesList[indexCorrectAngle], goodGuessAlpha)) >
            std::abs(angleDifference(allAnglesList[i], goodGuessAlpha))) {
            indexCorrectAngle = i;
        }
    }
    return allAnglesList[indexCorrectAngle];//this angle is from Pos1 to Pos 2
}

std::vector<double>
softDescriptorRegistration::softRegistrationVoxel2DListOfPossibleRotations(double voxelData1Input[],
                                                                           double voxelData2Input[],
                                                                           std::string outputDir, bool debug) {
    // scan -> spectrum
    double maximumScan1 = this->getSpectrumFromVoxelData2D(voxelData1Input, this->magnitude1,
                                                           this->phase1, false);
    double maximumScan2 = this->getSpectrumFromVoxelData2D(voxelData2Input, this->magnitude2,
                                                           this->phase2, false);

    // Data collection structure for CSV output
    struct CSVData {
        std::vector<double> magnitudeFFTW1;
        std::vector<double> phaseFFTW1;
        std::vector<double> voxelDataFFTW1;
        std::vector<double> magnitudeFFTW2;
        std::vector<double> phaseFFTW2;
        std::vector<double> voxelDataFFTW2;
        std::vector<double> resampledVoxel1;
        std::vector<double> resampledVoxel2;
        std::vector<double> resultingCorrelation1D;
    } csvData;

    if (debug) {
        // Collect data for CSV output instead of writing separate files
        for (int j = 0; j < N; j++) {
            for (int i = 0; i < N; i++) {
                csvData.magnitudeFFTW1.push_back(magnitude1[j + N * i]);
                csvData.phaseFFTW1.push_back(phase1[j + N * i]);
                csvData.voxelDataFFTW1.push_back(voxelData1Input[j + N * i]);
                csvData.magnitudeFFTW2.push_back(magnitude2[j + N * i]);
                csvData.phaseFFTW2.push_back(phase2[j + N * i]);
                csvData.voxelDataFFTW2.push_back(voxelData2Input[j + N * i]);
            }
        }
    }

    double globalMaximumMagnitude;
    if (maximumScan2 < maximumScan1) {
        globalMaximumMagnitude = maximumScan1;
    } else {
        globalMaximumMagnitude = maximumScan2;
    }

    //normalize and fftshift
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            int indexX = (N / 2 + i) % N;
            int indexY = (N / 2 + j) % N;

            magnitude1Shifted[indexY + N * indexX] =
                    magnitude1[j + N * i] / globalMaximumMagnitude;
            magnitude2Shifted[indexY + N * indexX] =
                    magnitude2[j + N * i] / globalMaximumMagnitude;
            // }
        }
    }


    //re-initialize to zero
    for (int i = 0; i < N * N; i++) {
        resampledMagnitudeSO3_1[i] = 0;
        resampledMagnitudeSO3_2[i] = 0;
        resampledMagnitudeSO3_1TMP[i] = 0;
        resampledMagnitudeSO3_2TMP[i] = 0;
    }

    //resampling from magnitude to sphere of SO(3)
    int r = N / 2 - 2;
    int bandwidth = N / 2;

    for (int j = 0; j < 2 * bandwidth; j++) {
        for (int k = 0; k < 2 * bandwidth; k++) {
            int xIndex = std::round((double) r * std::sin(thetaIncrement((double) j, bandwidth)) *
                                    std::cos(phiIncrement((double) k, bandwidth)) + bandwidth) - 1;
            int yIndex = std::round((double) r * std::sin(thetaIncrement((double) j, bandwidth)) *
                                    std::sin(phiIncrement((double) k, bandwidth)) + bandwidth) - 1;
            resampledMagnitudeSO3_1TMP[k + j * bandwidth * 2] =
                    255 * magnitude1Shifted[yIndex + N * xIndex];
            resampledMagnitudeSO3_2TMP[k + j * bandwidth * 2] =
                    255 * magnitude2Shifted[yIndex + N * xIndex];
        }
    }
    // add CLAHE
    cv::Mat magTMP1(N, N, CV_64FC1, resampledMagnitudeSO3_1TMP);
    cv::Mat magTMP2(N, N, CV_64FC1, resampledMagnitudeSO3_2TMP);
    magTMP1.convertTo(magTMP1, CV_8UC1);
    magTMP2.convertTo(magTMP2, CV_8UC1);
    cv::Ptr<cv::CLAHE> clahe = cv::createCLAHE();
    clahe->setClipLimit(3);
    clahe->apply(magTMP1, magTMP1);
    clahe->apply(magTMP2, magTMP2);

    //add CLAHE output data to input data for SO(3) correlation
    for (int j = 0; j < 2 * bandwidth; j++) {
        for (int k = 0; k < 2 * bandwidth; k++) {
            resampledMagnitudeSO3_1[j + k * bandwidth * 2] = ((double) magTMP1.data[j + k * bandwidth * 2]) / 255.0;
            resampledMagnitudeSO3_2[j + k * bandwidth * 2] = ((double) magTMP2.data[j + k * bandwidth * 2]) / 255.0;
        }
    }

    if (debug) {
        // Collect resampled data for CSV output
        for (int j = 0; j < N; j++) {
            for (int k = 0; k < N; k++) {
                csvData.resampledVoxel1.push_back(resampledMagnitudeSO3_1[j + k * bandwidth * 2]);
                csvData.resampledVoxel2.push_back(resampledMagnitudeSO3_2[j + k * bandwidth * 2]);
            }
        }
    }

    //use SOFT descriptor to calculate the correlation
    this->softCorrelationObject.correlationOfTwoSignalsInSO3(resampledMagnitudeSO3_1, resampledMagnitudeSO3_2,
                                                             resultingCorrelationComplex);

    //calcs the rotation angle around z axis for 2D scans
    double currentThetaAngle;
    double currentPhiAngle;
    double maxCorrelation = 0;
    std::vector<angleAndCorrelation> correlationOfAngle;
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            currentThetaAngle = j * 2.0 * M_PI / N;
            currentPhiAngle = i * 2.0 * M_PI / N;

            angleAndCorrelation tmpHolding;
            tmpHolding.correlation = resultingCorrelationComplex[j + N * (i + N * 0)][0]; // real part
            if (tmpHolding.correlation > maxCorrelation) {
                maxCorrelation = tmpHolding.correlation;
            }

            tmpHolding.angle = std::fmod(-(currentThetaAngle + currentPhiAngle) + 6 * M_PI, 2 * M_PI);
            correlationOfAngle.push_back(tmpHolding);
        }
    }
    //sort the angle and corresponding correlation height
    std::sort(correlationOfAngle.begin(), correlationOfAngle.end(), compareTwoAngleCorrelation);

    std::vector<float> correlationAveraged, angleList;
    double currentAverageAngle = correlationOfAngle[0].angle;
    //calculate average correlation for each angle
    int numberOfAngles = 1;
    double averageCorrelation = correlationOfAngle[0].correlation;
    for (int i = 1; i < correlationOfAngle.size(); i++) {

        if (std::abs(currentAverageAngle - correlationOfAngle[i].angle) < 1.0 / N / 4.0) {
            numberOfAngles = numberOfAngles + 1;
            averageCorrelation = averageCorrelation + correlationOfAngle[i].correlation;
        } else {

            correlationAveraged.push_back((float) (averageCorrelation / numberOfAngles));
            angleList.push_back((float) currentAverageAngle);
            numberOfAngles = 1;
            averageCorrelation = correlationOfAngle[i].correlation;
            currentAverageAngle = correlationOfAngle[i].angle;

        }
    }
    correlationAveraged.push_back((float) (averageCorrelation / numberOfAngles));
    angleList.push_back((float) currentAverageAngle);

    if (debug) {
        // Collect correlation data for CSV output
        for (int i = 0; i < correlationAveraged.size(); i++) {
            csvData.resultingCorrelation1D.push_back(correlationAveraged[i]);
        }
    }

    //find peaks:
    //rotate to lowest position of 1d array
    //find peaks
    auto minmax = std::min_element(correlationAveraged.begin(), correlationAveraged.end());
    long distanceToMinElement = std::distance(correlationAveraged.begin(), minmax);
    std::rotate(correlationAveraged.begin(), correlationAveraged.begin() + distanceToMinElement,
                correlationAveraged.end());

    std::vector<int> out;

    PeakFinder::findPeaks(correlationAveraged, out, true, 4.0);
    // re-rotate
    std::rotate(correlationAveraged.begin(),
                correlationAveraged.begin() + correlationAveraged.size() - distanceToMinElement,
                correlationAveraged.end());
    for (int i = 0; i < out.size(); ++i) {
        out[i] = out[i] + (int) distanceToMinElement;
        if (out[i] >= correlationAveraged.size()) {
            out[i] = out[i] - correlationAveraged.size();
        }
    }

    std::vector<double> returnVectorWithAngles;

    for (int i = 0; i < out.size(); i++) {
        returnVectorWithAngles.push_back(angleList[out[i]]);
    }

    // Write collected data to single CSV file if debug is enabled
    if (debug) {
        std::ofstream csvFile;
        csvFile.open(outputDir + "/rotation_analysis_results.csv");
        
        // Write header
        csvFile << "magnitudeFFTW1,phaseFFTW1,voxelDataFFTW1,magnitudeFFTW2,phaseFFTW2,voxelDataFFTW2,resampledVoxel1,resampledVoxel2,resultingCorrelation1D\n";
        
        // Find maximum length among all vectors
        size_t maxLength = std::max({
            csvData.magnitudeFFTW1.size(),
            csvData.phaseFFTW1.size(),
            csvData.voxelDataFFTW1.size(),
            csvData.magnitudeFFTW2.size(),
            csvData.phaseFFTW2.size(),
            csvData.voxelDataFFTW2.size(),
            csvData.resampledVoxel1.size(),
            csvData.resampledVoxel2.size(),
            csvData.resultingCorrelation1D.size()
        });
        
        // Write data rows
        for (size_t i = 0; i < maxLength; i++) {
            csvFile << (i < csvData.magnitudeFFTW1.size() ? std::to_string(csvData.magnitudeFFTW1[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.phaseFFTW1.size() ? std::to_string(csvData.phaseFFTW1[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.voxelDataFFTW1.size() ? std::to_string(csvData.voxelDataFFTW1[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.magnitudeFFTW2.size() ? std::to_string(csvData.magnitudeFFTW2[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.phaseFFTW2.size() ? std::to_string(csvData.phaseFFTW2[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.voxelDataFFTW2.size() ? std::to_string(csvData.voxelDataFFTW2[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.resampledVoxel1.size() ? std::to_string(csvData.resampledVoxel1[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.resampledVoxel2.size() ? std::to_string(csvData.resampledVoxel2[i]) : "");
            csvFile << ",";
            csvFile << (i < csvData.resultingCorrelation1D.size() ? std::to_string(csvData.resultingCorrelation1D[i]) : "");
            csvFile << "\n";
        }
        
        csvFile.close();
    }

    return returnVectorWithAngles;
}


Eigen::Vector2d softDescriptorRegistration::softRegistrationVoxel2DTranslation(double voxelData1Input[],
                                                                               double voxelData2Input[],
                                                                               double cellSize,
                                                                               Eigen::Vector3d initialGuess,
                                                                               bool useInitialGuess,
                                                                               double &heightMaximumPeak, bool debug) {
    //scan -> spectrum
    double maximumScan1 = this->getSpectrumFromVoxelData2D(voxelData1Input, this->magnitude1,
                                                           this->phase1, false);
    double maximumScan2 = this->getSpectrumFromVoxelData2D(voxelData2Input, this->magnitude2,
                                                           this->phase2, false);

    //fftshift and calculate convolution of spectrums
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {

            int indexX = (N / 2 + i) % N;
            int indexY = (N / 2 + j) % N;
            //calculate the spectrum back
            std::complex<double> tmpComplex1 =
                    magnitude1[indexY + N * indexX] * std::exp(std::complex<double>(0, phase1[indexY + N * indexX]));
            std::complex<double> tmpComplex2 =
                    magnitude2[indexY + N * indexX] * std::exp(std::complex<double>(0, phase2[indexY + N * indexX]));

            resultingPhaseDiff2D[j + N * i][0] = ((tmpComplex1) * conj(tmpComplex2)).real();
            resultingPhaseDiff2D[j + N * i][1] = ((tmpComplex1) * conj(tmpComplex2)).imag();

        }
    }

    //calculate correlation
    fftw_execute(planFourierToVoxel2D);



    // fftshift and calc magnitude, together with getting highest peak
    int indexMaximumCorrelationI;
    int indexMaximumCorrelationJ;
    double maximumCorrelation = 0;
    for (int j = 0; j < N; j++) {
        for (int i = 0; i < N; i++) {
            int indexX = (N / 2 - i + N) % N;// changed j and i here
            int indexY = (N / 2 - j + N) % N;

            resultingCorrelationDouble[indexY + N * indexX] = sqrt(
                    resultingShiftPeaks2D[j + N * i][0] *
                    resultingShiftPeaks2D[j + N * i][0] +
                    resultingShiftPeaks2D[j + N * i][1] *
                    resultingShiftPeaks2D[j + N * i][1]); // real part;
            //meanCorrelation = meanCorrelation + resultingCorrelationDouble[indexY + N * indexX];
            if (maximumCorrelation < resultingCorrelationDouble[indexY + N * indexX]) {
                maximumCorrelation = resultingCorrelationDouble[indexY + N * indexX];
                indexMaximumCorrelationI = indexX;
                indexMaximumCorrelationJ = indexY;
            }
        }
    }

    // if initial guess is used, take initial position and find local maxima of correlation data. Always go the steepest assent
    if (useInitialGuess) {
        //find local maximum in 2d array
        int initialIndexX = (int) (initialGuess[0] / cellSize + N / 2);
        int initialIndexY = (int) (initialGuess[1] / cellSize + N / 2);
        int localMaxDiffX = 0;
        int localMaxDiffY = 0;
        do {
            localMaxDiffX = 0;
            localMaxDiffY = 0;

            for (int i = -1; i < 2; i++) {
                for (int j = -1; j < 2; j++) {
                    if (resultingCorrelationDouble[(initialIndexY + localMaxDiffY) +
                                                   N * (initialIndexX + localMaxDiffX)] <
                        resultingCorrelationDouble[(initialIndexY + j) + N * (initialIndexX + i)]) {
                        localMaxDiffX = i;
                        localMaxDiffY = j;
                    }
                }
            }
            initialIndexY += localMaxDiffY;
            initialIndexX += localMaxDiffX;
        } while (localMaxDiffX != 0 || localMaxDiffY != 0);
        indexMaximumCorrelationI = initialIndexX;
        indexMaximumCorrelationJ = initialIndexY;
    }
    heightMaximumPeak = resultingCorrelationDouble[indexMaximumCorrelationJ +
                                                   N * indexMaximumCorrelationI];//Hope that is correct

    Eigen::Vector3d translationCalculated((indexMaximumCorrelationI - N / 2.0) * cellSize,
                                          (indexMaximumCorrelationJ - N / 2.0) * cellSize, 0);


    Eigen::Vector2d returnVector;
    returnVector[0] = translationCalculated[0];
    returnVector[1] = translationCalculated[1];
    return returnVector;
}

Eigen::Matrix4d softDescriptorRegistration::registrationOfTwoVoxelsSOFTFast(double voxelData1Input[],
                                                                            double voxelData2Input[],
                                                                            Eigen::Matrix4d initialGuess,
                                                                            bool useInitialAngle,
                                                                            bool useInitialTranslation,
                                                                            double cellSize,
                                                                            std::string outputDir,
                                                                            bool debug) {


    std::vector<Eigen::Matrix4d> listOfTransformations;
    std::vector<double> maximumHeightPeakList;
    std::vector<double> estimatedAngles;
    
    // Data collection structure for CSV output
    struct CSVData {
        std::vector<std::vector<double>> resultingCorrelationShift; // Multiple correlation shift matrices
        std::vector<std::vector<double>> resultVoxel1; // Multiple result voxels
        std::vector<std::vector<double>> resultVoxel2; // Multiple result voxels
    } csvData;
    
    //calculate array of possible angle registrations. With an initial guess, one is choosen (thereofre list.size =1)
    if (useInitialAngle) {
        double goodGuessAlpha = std::atan2(initialGuess(1, 0), initialGuess(0, 0));
        double angleTMP = this->softRegistrationVoxel2DRotationOnly(voxelData1Input, voxelData2Input, goodGuessAlpha,
                                                                    outputDir, debug);

        estimatedAngles.push_back(angleTMP);

    } else {
        estimatedAngles = this->softRegistrationVoxel2DListOfPossibleRotations(voxelData1Input, voxelData2Input,
                                                                               outputDir, debug);
    }

    //calculate translation for each possible angle
    int angleIndex = 0;
    for (double estimatedAngle: estimatedAngles) {


        //copy data
        for (int i = 0; i < N * N; i++) {
            this->voxelData1[i] = voxelData1Input[i];
            this->voxelData2[i] = voxelData2Input[i];
        }


        cv::Mat magTMP1(this->N, this->N, CV_64F, voxelData1);
        cv::Mat magTMP2(this->N, this->N, CV_64F, voxelData2);

        //rotating first image to calculate correlation next
        cv::Point2f pc(magTMP1.cols / 2., magTMP1.rows / 2.);
        std::cout << "ESTIMATED ANGLE:" << estimatedAngle << std::endl;
        cv::Mat r = cv::getRotationMatrix2D(pc, estimatedAngle * 180.0 / M_PI, 1.0);
        cv::warpAffine(magTMP1, magTMP1, r, magTMP1.size());

        double maximumPeakOfThisTranslation;
        Eigen::Vector2d translation = this->softRegistrationVoxel2DTranslation(voxelData1, voxelData2, cellSize,
                                                                               initialGuess.block<3, 1>(0, 3),
                                                                               useInitialTranslation,
                                                                               maximumPeakOfThisTranslation,
                                                                               debug);

        Eigen::Matrix4d estimatedRotationScans = Eigen::Matrix4d::Identity();
        Eigen::AngleAxisd rotation_vectorTMP(estimatedAngle, Eigen::Vector3d(0, 0, 1));
        Eigen::Matrix3d tmpRotMatrix3d = rotation_vectorTMP.toRotationMatrix();
        estimatedRotationScans.block<3, 3>(0, 0) = tmpRotMatrix3d;
        estimatedRotationScans(0, 3) = translation.x();
        estimatedRotationScans(1, 3) = translation.y();
        estimatedRotationScans(2, 3) = 0;
        estimatedRotationScans(3, 3) = 1;
        // Inverse transformation, NOT SURE WHY NEED TO CALCUALTE THE INVERSE AN SAVE BACk
        Eigen::Matrix4d estimatedRotationScans1To2 = estimatedRotationScans.inverse();
        estimatedRotationScans(0, 3) = - estimatedRotationScans1To2(1, 3);
        estimatedRotationScans(1, 3) = - estimatedRotationScans1To2(0, 3);

        //transformation and peak height of correlation added to list.
        listOfTransformations.push_back(estimatedRotationScans);
        maximumHeightPeakList.push_back(maximumPeakOfThisTranslation);


        if (debug) {
            // Collect correlation shift data
            std::vector<double> correlationShiftData;
            for (int j = 0; j < N; j++) {
                for (int i = 0; i < N; i++) {
                    correlationShiftData.push_back(resultingCorrelationDouble[j + N * i]);
                }
            }
            csvData.resultingCorrelationShift.push_back(correlationShiftData);

            // Apply transformation for result voxels
            //Eigen::Matrix4d estimatedRotationScans1To2 = estimatedRotationScans.inverse();

            cv::Mat trans_mat = (cv::Mat_<double>(2, 3) << 1,
                    0,
                    estimatedRotationScans1To2(1, 3),
                    0,
                    1,
                    estimatedRotationScans1To2(0, 3));
            
            std::cout << "*** TRANS_MAT:" << trans_mat << std::endl;

            warpAffine(magTMP2, magTMP2, trans_mat, magTMP2.size());
            
            // Collect result voxel data
            std::vector<double> resultVoxel1Data, resultVoxel2Data;
            for (int j = 0; j < this->N; j++) {
                for (int i = 0; i < this->N; i++) {
                    resultVoxel1Data.push_back(voxelData1[j + this->N * i]);
                    resultVoxel2Data.push_back(voxelData2[j + this->N * i]);
                }
            }
            csvData.resultVoxel1.push_back(resultVoxel1Data);
            csvData.resultVoxel2.push_back(resultVoxel2Data);
        }
        angleIndex++;
    }

    //find maximum of maximumPeakOfThisTranslation
    auto minmax = std::max_element(maximumHeightPeakList.begin(), maximumHeightPeakList.end());
    long distanceToMaxElement = std::distance(maximumHeightPeakList.begin(), minmax);

    if (debug) {
        // Write transformation matrices to separate CSV file (all solutions)
        std::ofstream transformationFile;
        transformationFile.open(outputDir + "/registration_solutions_transformation.csv");
        
        // Write transformation matrix header
        transformationFile << "r11,r12,r13,tx,r21,r22,r23,ty,r31,r32,r33,tz,h41,h42,h43,h44\n";
        
        // Write each transformation matrix as a row
        for (const auto& transformation : listOfTransformations) {
            transformationFile << transformation(0,0) << "," << transformation(0,1) << "," << transformation(0,2) << "," << transformation(0,3) << ",";
            transformationFile << transformation(1,0) << "," << transformation(1,1) << "," << transformation(1,2) << "," << transformation(1,3) << ",";
            transformationFile << transformation(2,0) << "," << transformation(2,1) << "," << transformation(2,2) << "," << transformation(2,3) << ",";
            transformationFile << transformation(3,0) << "," << transformation(3,1) << "," << transformation(3,2) << "," << transformation(3,3) << "\n";
        }
        transformationFile.close();

        // Write all collected data to single CSV file
        std::ofstream csvFile;
        csvFile.open(outputDir + "/registration_results.csv");
        
        // Build header dynamically
        std::vector<std::string> headers;
        headers.push_back("numberOfSolutions");
        headers.push_back("indexOfBestSolution");
        
        // Add headers for correlation shift matrices
        for (int i = 0; i < csvData.resultingCorrelationShift.size(); i++) {
            headers.push_back("resultingCorrelationShift" + std::to_string(i));
        }
        
        // Add headers for result voxels
        for (int i = 0; i < csvData.resultVoxel1.size(); i++) {
            headers.push_back("resultVoxel1" + std::to_string(i));
            headers.push_back("resultVoxel2" + std::to_string(i));
        }
        
        // Write header
        for (size_t i = 0; i < headers.size(); i++) {
            csvFile << headers[i];
            if (i < headers.size() - 1) csvFile << ",";
        }
        csvFile << "\n";
        
        // Find maximum length among all vectors
        size_t maxLength = 1; // At least 1 for the scalar values
        for (const auto& vec : csvData.resultingCorrelationShift) {
            maxLength = std::max(maxLength, vec.size());
        }
        for (const auto& vec : csvData.resultVoxel1) {
            maxLength = std::max(maxLength, vec.size());
        }
        for (const auto& vec : csvData.resultVoxel2) {
            maxLength = std::max(maxLength, vec.size());
        }
        
        // Write data rows
        for (size_t row = 0; row < maxLength; row++) {
            // numberOfSolutions column (only in first row)
            csvFile << (row == 0 ? std::to_string(maximumHeightPeakList.size()) : "");
            csvFile << ",";
            
            // indexOfBestSolution column (only in first row)
            csvFile << (row == 0 ? std::to_string(distanceToMaxElement) : "");
            csvFile << ",";
            
            // resultingCorrelationShift columns
            for (size_t i = 0; i < csvData.resultingCorrelationShift.size(); i++) {
                csvFile << (row < csvData.resultingCorrelationShift[i].size() ? 
                           std::to_string(csvData.resultingCorrelationShift[i][row]) : "");
                csvFile << ",";
            }
            
            // resultVoxel columns
            for (size_t i = 0; i < csvData.resultVoxel1.size(); i++) {
                csvFile << (row < csvData.resultVoxel1[i].size() ? 
                           std::to_string(csvData.resultVoxel1[i][row]) : "");
                csvFile << ",";
                csvFile << (row < csvData.resultVoxel2[i].size() ? 
                           std::to_string(csvData.resultVoxel2[i][row]) : "");
                if (i < csvData.resultVoxel1.size() - 1) csvFile << ",";
            }
            csvFile << "\n";
        }
        
        csvFile.close();
    } else {
        // Write only the best transformation matrix to CSV file
        std::ofstream transformationFile;
        transformationFile.open(outputDir + "/registration_solutions_transformation.csv");
        
        // Write transformation matrix header
        transformationFile << "r11,r12,r13,tx,r21,r22,r23,ty,r31,r32,r33,tz,h41,h42,h43,h44\n";
        
        // Write only the best transformation matrix
        const auto& bestTransformation = listOfTransformations[distanceToMaxElement];
        transformationFile << bestTransformation(0,0) << "," << bestTransformation(0,1) << "," << bestTransformation(0,2) << "," << bestTransformation(0,3) << ",";
        transformationFile << bestTransformation(1,0) << "," << bestTransformation(1,1) << "," << bestTransformation(1,2) << "," << bestTransformation(1,3) << ",";
        transformationFile << bestTransformation(2,0) << "," << bestTransformation(2,1) << "," << bestTransformation(2,2) << "," << bestTransformation(2,3) << ",";
        transformationFile << bestTransformation(3,0) << "," << bestTransformation(3,1) << "," << bestTransformation(3,2) << "," << bestTransformation(3,3) << "\n";
        transformationFile.close();
    }

    return listOfTransformations[distanceToMaxElement];//robot transformation matrix from 1 to 2
}