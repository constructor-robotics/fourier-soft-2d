clc
clear



nameOfFolder = "out";

%%


magnitudeFFTW1 = readmatrix(nameOfFolder+"/magnitudeFFTW1.csv");
N=sqrt(size(magnitudeFFTW1,1));

phaseFFTW1 = readmatrix(nameOfFolder+"/phaseFFTW1.csv");
voxelDataUsed1 = readmatrix(nameOfFolder+"/voxelDataFFTW1.csv");

magnitudeFFTW2 = readmatrix(nameOfFolder+"/magnitudeFFTW2.csv");
phaseFFTW2 = readmatrix(nameOfFolder+"/phaseFFTW2.csv");
voxelDataUsed2 = readmatrix(nameOfFolder+"/voxelDataFFTW2.csv");

magnitude1 =zeros(N,N);
phase1 =zeros(N,N);
voxelData1 =zeros(N,N);
magnitude2 =zeros(N,N);
phase2 =zeros(N,N);
voxelData2 =zeros(N,N);

for j =1:N
    for k =1:N
        magnitude1(k,j) = magnitudeFFTW1(k*N-N+j);
        phase1(k,j) = phaseFFTW1(k*N-N+j);
        voxelData1(k,j) = voxelDataUsed1((k-1)*N+j);
        magnitude2(k,j) = magnitudeFFTW2(k*N-N+j);
        phase2(k,j) = phaseFFTW2(k*N-N+j);
        voxelData2(k,j) = voxelDataUsed2((k-1)*N+j);
    end
end

magnitude1=fftshift(magnitude1);
phase1=fftshift(phase1);
magnitude2=fftshift(magnitude2);
phase2=fftshift(phase2);

figure(1)
clf

imagesc(squeeze(magnitude1));

title('Magnitude Voxel 1:', 'Interpreter', 'latex')
axis image
box on 


figure(2)
clf
imagesc((voxelData1))
axis image
title('Voxel Data 1:', 'Interpreter', 'latex')


figure(3)
clf

imagesc(squeeze(magnitude2));

title('Magnitude Voxel 2:', 'Interpreter', 'latex')
axis image

figure(4)

imagesc((voxelData2))

axis image
title('Voxel Data 2:', 'Interpreter', 'latex')
%%
resampledDataForSphere1 = readmatrix(nameOfFolder+"/resampledVoxel1.csv");
resampledDataForSphere2 = readmatrix(nameOfFolder+"/resampledVoxel2.csv");

resampledDataForSphereResult1 =zeros(N,N);
resampledDataForSphereResult2 =zeros(N,N);
for j = 1:N
    for i =1:N
            resampledDataForSphereResult1(j,i) = resampledDataForSphere1((i-1)*N+j);
            resampledDataForSphereResult2(j,i) = resampledDataForSphere2((i-1)*N+j);
    end
end
% can also be printed as 2D instead of a sphere
if 1
    figure(5)
    clf

    sphere(1000);
    ch = get(gca,'children');
    set(ch,'facecolor','texturemap','cdata',resampledDataForSphereResult2,'edgecolor','none');
    axis equal
    title('Resampled Sphere 2:', 'Interpreter', 'latex')
    figure(6)
    clf
    sphere(1000);
    ch = get(gca,'children');
    set(ch,'facecolor','texturemap','cdata',resampledDataForSphereResult1,'edgecolor','none');
    axis equal
    title('Resampled Sphere 1:', 'Interpreter', 'latex')
   
else
    figure(5)
    clf
    imagesc((resampledDataForSphereResult2));
    axis image
    title('Resampled Sphere as 2D 2:', 'Interpreter', 'latex')
    pbaspect([1 1 1])
    figure(6)
    clf
    imagesc((resampledDataForSphereResult1));
    axis image
    pbaspect([1 1 1])
    title('Resampled Sphere as 2D 1:', 'Interpreter', 'latex')
end

%%
figure(7)
correlationOfAngles = readmatrix(nameOfFolder+"/resultingCorrelation1D.csv");

anglesX = linspace(0,2*pi,size(correlationOfAngles,1));
[psor,lsor] = findpeaks(correlationOfAngles);
plot(anglesX,correlationOfAngles)

grid on
xlim([-0.2 2*pi+0.2])

box on 
xlabel("angle in rad", 'Interpreter', 'latex');
ylabel("Correlation Value", 'Interpreter', 'latex');

%%

dataInformation = readmatrix(nameOfFolder+"/dataForReadIn.csv");

numberOfSolutions = dataInformation(1);
bestSolution = dataInformation(2);


figure(8)
clf
%correlation
for i = 1:numberOfSolutions
        subplot(2,2,i)
    correlationMatrixShift1D = readmatrix(nameOfFolder+"/resultingCorrelationShift"+ string(num2str(i-1)) +".csv");
    resultSize = nthroot(length(correlationMatrixShift1D),2);
    correlationMatrixShift2D = reshape(correlationMatrixShift1D,resultSize,resultSize);
    [Xplot,Yplot]=meshgrid(1:resultSize,1:resultSize);
    surf(Xplot,Yplot,(correlationMatrixShift2D),'edgecolor', 'none');

    
    box on 
    title(num2str(i), 'Interpreter', 'latex')
    pbaspect([1 1 1])
end





%%



f = figure(9);
clf



% show results of registrated voxels, 
for i = 1:numberOfSolutions
    resultVoxel1TMP= readmatrix(nameOfFolder+"/resultVoxel1"+num2str(i-1)+".csv");
    resultVoxel2TMP= readmatrix(nameOfFolder+"/resultVoxel2"+num2str(i-1)+".csv");

    voxelResult1 =zeros(N,N);
    voxelResult2 =zeros(N,N);
    for j =1:N
        for k =1:N
            voxelResult1(k,j) = resultVoxel1TMP(k*N-N+j);
            voxelResult2(k,j) = resultVoxel2TMP(k*N-N+j);
    
        end
    end



    subplot(2,2,i)
    C = imfuse(voxelResult1,voxelResult2,'blend','Scaling','joint');
    imagesc(squeeze(C));

    title(num2str(i), 'Interpreter', 'latex')

    box on
    pbaspect([1 1 1])


end



