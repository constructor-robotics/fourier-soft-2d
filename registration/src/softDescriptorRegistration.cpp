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


    if (debug) {
        std::ofstream myFile1, myFile2, myFile3, myFile4, myFile5, myFile6;
        myFile1.open(
                outputDir + "/magnitudeFFTW1.csv");
        myFile2.open(outputDir + "/phaseFFTW1.csv");
        myFile3.open(
                outputDir + "/voxelDataFFTW1.csv");
        myFile4.open(
                outputDir + "/magnitudeFFTW2.csv");
        myFile5.open(outputDir + "/phaseFFTW2.csv");
        myFile6.open(
                outputDir + "/voxelDataFFTW2.csv");
        for (int j = 0; j < N; j++) {
            for (int i = 0; i < N; i++) {
                myFile1 << magnitude1[j + N * i]; // real part
                myFile1 << "\n";
                myFile2 << phase1[j + N * i]; // imaginary part
                myFile2 << "\n";
                myFile3 << voxelData1Input[j + N * i]; // imaginary part
                myFile3 << "\n";
                myFile4 << magnitude2[j + N * i]; // real part
                myFile4 << "\n";
                myFile5 << phase2[j + N * i]; // imaginary part
                myFile5 << "\n";
                myFile6 << voxelData2Input[j + N * i]; // imaginary part
                myFile6 << "\n";
            }
        }

        myFile1.close();
        myFile2.close();
        myFile3.close();
        myFile4.close();
        myFile5.close();
        myFile6.close();
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
        std::ofstream myFile7, myFile8;
        myFile7.open(
                outputDir + "/resampledVoxel1.csv");
        myFile8.open(
                outputDir + "/resampledVoxel2.csv");

        for (int j = 0; j < N; j++) {
            for (int k = 0; k < N; k++) {
                myFile7 << resampledMagnitudeSO3_1[j + k * bandwidth * 2]; // real part
                myFile7 << "\n";
                myFile8 << resampledMagnitudeSO3_2[j + k * bandwidth * 2]; // real part
                myFile8 << "\n";
            }
        }
        myFile7.close();
        myFile8.close();
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
        std::ofstream myFile9;
        myFile9.open(
                outputDir + "/resultingCorrelation1D.csv");

        for (int i = 0; i < correlationAveraged.size(); i++) {
            myFile9 << correlationAveraged[i]; // real part
            myFile9 << "\n";

        }
        myFile9.close();
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

        //transformation and peak height of correlation added to list.
        listOfTransformations.push_back(estimatedRotationScans);
        maximumHeightPeakList.push_back(maximumPeakOfThisTranslation);


        if (debug) {
            std::ofstream myFile10;
            myFile10.open(
                    outputDir + "/resultingCorrelationShift" +
                    std::to_string(angleIndex) + ".csv");

            for (int j = 0; j < N; j++) {
                for (int i = 0; i < N; i++) {
                    myFile10 << resultingCorrelationDouble[j + N * i];
                    myFile10 << "\n";
                }
            }
            myFile10.close();

            Eigen::Matrix4d estimatedRotationScans1To2 = estimatedRotationScans.inverse();


            cv::Mat trans_mat = (cv::Mat_<double>(2, 3) << 1,
                    0,
                    estimatedRotationScans1To2(1, 3),
                    0,
                    1,
                    estimatedRotationScans1To2(0, 3));


            warpAffine(magTMP2, magTMP2, trans_mat, magTMP2.size());
            std::ofstream myFile1, myFile2;
            myFile1.open(
                    outputDir + "/resultVoxel1" +
                    std::to_string(angleIndex) + ".csv");
            myFile2.open(
                    outputDir + "/resultVoxel2" +
                    std::to_string(angleIndex) + ".csv");
            for (int j = 0; j < this->N; j++) {
                for (int i = 0; i < this->N; i++) {
                    myFile1 << voxelData1[j + this->N * i]; // real part
                    myFile1 << "\n";
                    myFile2 << voxelData2[j + this->N * i]; // imaginary part
                    myFile2 << "\n";
                }
            }
            myFile1.close();
            myFile2.close();

        }
        angleIndex++;
    }

    //find maximum of maximumPeakOfThisTranslation
    auto minmax = std::max_element(maximumHeightPeakList.begin(), maximumHeightPeakList.end());
    long distanceToMaxElement = std::distance(maximumHeightPeakList.begin(), minmax);

    if (debug) {
        std::ofstream myFile12;
        myFile12.open(outputDir + "/dataForReadIn.csv");

        myFile12 << maximumHeightPeakList.size();//number of possible solutions
        myFile12 << "\n";
        myFile12 << distanceToMaxElement;//best Solution
        myFile12 << "\n";

        myFile12.close();

    }

    return listOfTransformations[distanceToMaxElement];//robot transformation matrix from 1 to 2
}