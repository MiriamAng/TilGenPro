# -*- coding: utf-8 -*-
"""
Created on Thu Oct 14 18:39:06 2021

@author: angelomm
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Oct 14 17:56:50 2021

@author: angelomm
"""

import logging
import matplotlib.pyplot as plt
import numpy as np 
import operator
import os
import pandas as pd
import pickle
import subprocess
import sys 
import time

from PIL import Image

from tqdm import tqdm


### DEFINITION OF THE MAIN VARIABLES NECESSARY TO RUN THE SCRIPT
# 1) qupathProj --> absolute path to the QuPath project file (.qpproj)
# 2) groovyScript --> absolute path to the groovy script (.groovy) used for tiles generation
# 3) shellScript --> absolute path to the shell script (.sh) script
# 4) tilesDir --> absolute path to the directory where tiles will be created (default value: QuPath project directory)
# 5) resultsDir --> absolute path to the directory where the results from pre-processing will be stored (default value: QuPath project directory)
# 6) wsiDir -->  absolute path to the folder containing the dataframe storing information on the WSIs to process
# 7) wsiList --> list of WSIs to process
# 8) lowerPerc --> percentile correspondent to the dark threshold on the log10-transformed median intesity pixel values distribution for a given WSI
# 9) upperPerc --> percentile correspondent to the white threshold on the log10-transformed median intesity pixel values distribution for a given WSI

### AUXILIARY FUNCTIONS ###

## Function 1
def tilesGenerator(qupathProj, shellScript, groovyScript, wsi=None):
    
    """ Generates tiles through the execution of a shell script that, in turn, runs the qupath command on the provided QuPath project and groovy script """
    
    if wsi is not None:
        p = subprocess.Popen(["sh", f"{shellScript}", f"{wsi}", f"{qupathProj}", \
                            f"{groovyScript}"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    else:
        p = subprocess.Popen(["sh", f"{shellScript}", f"{qupathProj}", f"{groovyScript}"], \
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
        retcode = p.poll() 
        line = p.stdout.readline()
        yield line
        if retcode is not None:
            return p.stderr

## Function 2
def readFiles(dirPath):

    ''' Returns the list of files contained in the folder provided in input.'''
    
    listFiles = [filename for filename in os.listdir(dirPath)] 
    return listFiles

## Function 3
def calculateIntensity(tilesPath, lowerPerc=10, upperPerc=90):

    '''For each WSI to process, the function returns in output:
    - the list of log10-transformed median intensity pixel values associated with each tile 
    - the log10-transformed median intensity pixel values correspondend to the 10th and 90th percentiles
    - a list of booleans indicating which tile needs to be kept (True) or discarded (False)
    '''
    
    # Note: the function "calculateIntensity" takes into account that all the tiles belonging to a WSI are saved in a single folder.
    # e.g. if the QuPath project includes 20 WSIs, we will have in output 20 folders, one for each WSI, and within each folder the tiles generated for that given WSI.
    
    # Store in a list all the median intensity values associated with each tile belonging to a given WSI
    tiles = readFiles(tilesPath)
    medianIntensities = [np.median(Image.open(os.path.join(tilesPath, filename))) for filename in tiles]
    logMedianIntensities = np.log10(np.array(medianIntensities))
    darkTh = np.percentile(logMedianIntensities, lowerPerc, interpolation = 'midpoint')
    whiteTh = np.percentile(logMedianIntensities, upperPerc, interpolation = 'midpoint')
    
    # Create a list where each element is a logical condition met by the tiles associated with the analyzed WSI:
    # tilesToKeep[i] = True if tile's log10 median intensity lays between the two thresholds, otherweise tilesToKeep[i] = False.
    tilesToKeep = (operator.ge(logMedianIntensities, darkTh) & operator.le(logMedianIntensities, whiteTh))

    return logMedianIntensities, darkTh, whiteTh, tilesToKeep
    
## Function 4
def histIntensities(logMedianIntensities, darkTh, whiteTh, filePath):
    
    '''Given the list of tiles log10-transformed median intensity pixel values associated with a given WSI,
    the function plots a histogram, highlighting the 10th and 90th percentiles, and save it in the specified file path'''
    
    n, bins, patches = plt.hist(logMedianIntensities, 60, density = False, facecolor = "r", alpha = 0.75)
    plt.xlabel('Median intensity value (log10)')
    plt.ylabel('Frequency')
    plt.title('Distribution of log10-transformed median intensity values')
    plt.axvline(x = darkTh)
    plt.axvline(x = whiteTh)
    plt.savefig(filePath)
    plt.clf()
    plt.close()
    
## Function 5
def extractInfo(tilesDir, preprocessingResDir, resDir, wsiDir):

    '''Provide in output a data frame containing information (e.g. initial number of tiles, number of tiles after pre-processing, etc) on the WSIs processed
    '''

    if wsiDir == None:
        df = pd.DataFrame(columns = ['Slide', 'numTilesInit', 'numTilesAfterPreproc'])
        df['Slide'] = os.listdir(tilesDir)

    elif os.path.exists(os.path.join(wsiDir, "slidesToProcess.csv")):
        df = pd.read_csv(os.path.join(wsiDir, "slidesToProcess.csv"))
        df['numTilesInit'] = ""
        df['numTilesAfterPreproc'] = ""
        for rowIdx in range(len(df)):
            wsiName = df.loc[rowIdx, 'Slide']
            newWsiName = os.path.splitext(wsiName)[0].replace(" ", "")
            df['Slide'].replace(to_replace = wsiName, value = newWsiName, inplace = True)
        
    for rowIdx in range(len(df)):
        numTiles_init = len(os.listdir(os.path.join(tilesDir, f"{df.loc[rowIdx,'Slide']}")))
        df.loc[rowIdx, "numTilesInit"] = numTiles_init
        picklePath = os.path.join(preprocessingResDir, f"normTiles/{df.loc[rowIdx,'Slide']}/normTiles_{df.loc[rowIdx,'Slide']}")
        pickleFile = pd.read_pickle(fr'{picklePath}')
        df.loc[rowIdx, "numTilesAfterPreproc"] = len(pickleFile)
    
    # Save the obtained data frame 
    df.to_csv(os.path.join(resDir, "infoWSIs.csv"), sep = ",", index = False)
    print("\n"         " ---------------------------------------------------------------------------------------------------------------------------------------------------------------")
    csv_filePath = os.path.join(resDir,"infoWSIs.csv")
    print("\n" f"The data-frame containing information on the WSIs processed has been saved under: {csv_filePath}")


def macenkoNorm(img, Io=240, alpha=1, beta=0.15):
    
    """
    Normalize the appearance of a source image to a reference image through the Macenko's method

     Reference: 
    [1] M Macenko, M Niethammer, JS Marron, D Borland, JT Woosley, X Guan, C 
        Schmitt, NE Thomas. "A method for normalizing histology slides for 
        quantitative analysis". IEEE International Symposium on Biomedical 
        Imaging: From Nano to Macro, 2009 vol.9, pp.1107-1110, 2009.
            
    Input:
        img: file path of the source image to normalize --> img = Image.open("img_name.png")
        Io: (optional) transmitted light intensity
        alpha = 1 (as recommend in the paper);  tolerance for the pseudo-min and pseudo-max
        beta = 0.15 (as recommend in the paper); OD threshold for transparent pixels        
        
    Output:
        Inorm: normalized source image
        
    Acknowledgements:
    The macenkoNorm function was inspired by Mitko Veta's and Geoffry F. Shau's "Staining Unmixing and Normalization in Python" code 
    available on https://github.com/schaugf/HEnorm_python/blob/master/normalizeStaining.py.
    
    Copyright (c) 2019, Mitko Veta(1), Geoffrey F. Schau(2)
    1 Image Sciences Institute
    University Medical Center
    Utrecht, The Netherlands

    2 Biomedical Engineering Department
    Oregon Health & Science University
    Portland, OR, USA
         
    """
    
    # Reference OD matrix
    HERef = np.array([[0.5626, 0.2159],
                      [0.7201, 0.8012],
                      [0.4062, 0.5581]])
        
    # Reference saturation vector
    maxCRef = np.array([1.9705, 1.0308])
    
    Img = Image.open(img)
    np_img = np.array(Img)
    
    # Define height, width and number of channels of the image
    h, w, c = np_img.shape
        
    # Reshape the image
    np_img = np_img.reshape((-1,3))
    
    # Calculate the optical density OD = -log(I/Io)
    # Add 1 to avoid log(0) in case any pixels in the image have a value of 0
    OD = -np.log((np_img.astype(np.float)+1)/Io)
        
    # Remove transparent pixels, i.e. OD intensities less than beta
    ODhat = OD[~np.any(OD<beta, axis=1)]
        
    # The Macenko method considers the projection of pixels into the 2D plane defined by the two
    # principle eigenvectors of the OD covariance matrix.
    # Calculate the optical density covariance matrix of the given image
    cov_ODhat = np.cov(ODhat.T)
        
    # Compute eigen values and eigenvectors to create the projection plane
    eigvals, eigvecs = np.linalg.eigh(cov_ODhat)
        
    # Project on the plane spanned by the eigenvectors corresponding to the two 
    # largest eigenvalues
    proj_plane = eigvecs[:,1:3]
    That = ODhat.dot(proj_plane)
        
    # Obtain the angle between point and first SVD direction
    phi = np.arctan2(That[:,1],That[:,0])
        
    # Identify angle's extremes
    minPhi = np.percentile(phi, alpha)
    maxPhi = np.percentile(phi, 100-alpha)
        
    # Convert to OD space and get the stain vectors for hematoxylin and eosin
    vMin = eigvecs[:,1:3].dot(np.array([(np.cos(minPhi), np.sin(minPhi))]).T)
    vMax = eigvecs[:,1:3].dot(np.array([(np.cos(maxPhi), np.sin(maxPhi))]).T)
        
    # Evaluate which between vMin and vMax refers to hematoxylin and eosin. This is done through a heuristic to make the vector 
    # corresponding to hematoxylin first and the one corresponding to eosin second
    if vMin[0] > vMax[0]:
        HE = np.array((vMin[:,0], vMax[:,0])).T
    else:
        HE = np.array((vMax[:,0], vMin[:,0])).T
        
    # Rows correspond to channels (RGB), columns to OD values
    Y = np.reshape(OD, (-1, 3)).T
        
    # Determine stain saturation
    C = np.linalg.lstsq(HE,Y, rcond=None)[0]
        
    # Normalize stain saturation
    maxC = np.array([np.percentile(C[0,:], 99), np.percentile(C[1,:], 99)])
    tmp = np.divide(maxC, maxCRef)
    C2 = np.divide(C, tmp[:,np.newaxis])
     
    # Recreate the image 
    Inorm = np.multiply(Io, np.exp(-HERef.dot(C2)))
    Inorm[Inorm > 255] = 254
    Inorm = np.reshape(Inorm.T, (h, w, 3)).astype(np.uint8)
        
    return Inorm

class pipeline:

    '''
    Pipeline for running tiles generation and pre-processing for each WSI provided in input.
    '''

    def __init__(self, qupathProj, groovyScript, shellScript, tilesDir, resultsDir, wsiDir, jpgNormTiles, wsiList=None, lowerPerc=10, upperPerc=90):
        
        self.qupathProj = qupathProj 
        self.groovyScript = groovyScript
        self.shellScript = shellScript
        self.tilesDir = tilesDir
        self.resultsDir = resultsDir
        self.wsiDir = wsiDir
        self.jpgNormTiles = jpgNormTiles
        self.wsiList = wsiList
        self.lowerPerc = lowerPerc
        self.upperPerc = upperPerc
            
    @staticmethod
    def saveRes(tilesDir, preprocessingResDir, file, t, g, jpgNormTiles, lowerPerc=10, upperPerc=90):
    
        os.makedirs(f"{preprocessingResDir}/normTiles/{file}", exist_ok=True)
        os.makedirs(f"{preprocessingResDir}/discTiles/{file}", exist_ok=True)
        normTilesFolder = f"{preprocessingResDir}/normTiles/{file}"
        
        if jpgNormTiles == True:
            os.makedirs(os.path.join(normTilesFolder, "jpgNormTiles"),exist_ok=True)
            jpgNormTilesFolder = os.path.join(normTilesFolder, "jpgNormTiles")
        else:
            jpgNormTilesFolder = None
        
        tilesDiscardedFolder = f"{preprocessingResDir}/discTiles/{file}"
        wsiTilesDir = os.path.join(tilesDir, file)
        tiles = readFiles(wsiTilesDir)
        
        logMedianIntensities, darkTh, whiteTh, tilesToKeep = calculateIntensity(wsiTilesDir, lowerPerc, upperPerc)
        
        log_file = os.path.join(normTilesFolder, f"{file}.log")
       
        # If tiles generation and pre-processing is performed more than once for the same slide, this check avoids that the new log file
        # will be appended to the previous one. Notably, if the log file already exists in that file path (i.e. the preprocessing pipeline has been run already once)
        # remove it otherwise proceed as usual.
        if os.path.exists(log_file):
            os.remove(log_file)
        else:
            pass
        
        logger = logging.getLogger(__name__)  
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(log_file)
        formatter    = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info("********** Tiles generation **********")
        logger.info(f"Number of tiles generated: {len(tiles)}")
        
        if file in t.keys():
            logger.info(f"Tiles generation took a total of {round(t[file])} secs.")
        else:
            logger.info(f"Tiles generation took a total of {round(t['Project'])} sec for the entire project")
        
        logger.info("********** Tiles pre-processing **********")
        
        logger.info(f"The following percentiles were chosen for tiles filtering: lower threshold = {lowerPerc}th; upper threshold = {upperPerc}th")
        
        for countPos, i in enumerate(tqdm(tiles, desc = f"{file} pre-processing", ncols= 100)):
            path = f"{tilesDir}/{file}/{i}"
            if tilesToKeep[countPos] == True:
                try:
                      g[i] = macenkoNorm(path)
                except Exception as e:
                      logger.debug(f"Tile {i} had problems during the Macenko normalization", exc_info=True)
                      
                if jpgNormTilesFolder != None:
                    normImg = Image.fromarray(g[i])
                    normImg.save(os.path.join(jpgNormTilesFolder, f"norm_{i}"))
                else:
                    pass
            else:
                logger.info(f"Tile {i} was excluded from further pre-processing due to thresholding")
                imgDiscarded = Image.open(os.path.join(wsiTilesDir, i))
                imgDiscarded.save(os.path.join(tilesDiscardedFolder, i))
        
        logger.info("********** End of the pre-processing pipeline **********")
        logger.info(f"A total of {len(tiles)-np.count_nonzero(tilesToKeep)} tiles were excluded from further pre-processing")
        # Remove all the handlers from the logger
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
        filePath = os.path.join(normTilesFolder, f"Hist_log_trans_RGB_{file}.png")
        histIntensities(logMedianIntensities, darkTh, whiteTh, filePath)
        filename = f"{normTilesFolder}/normTiles_{file}"
        outfile = open(filename,'wb')
        pickle.dump(g,outfile)
        outfile.close() 
        print('\n' f"Tiles pre-processing for {file} has been completed.", '\n' f"Results from pre-processing can be found under: {normTilesFolder}")

    
    def initialize(self):
        
        """For each WSI processed, a folder will be created to store results from pre-processing. 
        In particular, given a WSI, all the tiles associated whose log10-transformed median 
        intensity pixel value lays between the two thresholds (i.e. darkTh and whiteTh) will be normalized and
        stored in a pikle files as python dictonary. """
        
        timeDict = {}
        normTilesDict = {}
        
        preprocessingResDir = f"{self.resultsDir}/preprocessingRes"
        
        os.makedirs(preprocessingResDir, exist_ok=True)
        os.makedirs(f"{preprocessingResDir}/normTiles", exist_ok=True)
        os.makedirs(f"{preprocessingResDir}/discTiles", exist_ok=True)
        
        # If the WSIs to process are provided in the form of a list
        if self.wsiList is not None:
            
            # The first thing to do is generating tiles. For each WSI belonging to the input wsiList, tiles generation is handled by the function 
            # tilesGenerator and a message is printed in output as soon all tiles belonging to the WSI have been generated.
            for i in self.wsiList:
                # Remove file extension as well as all possible white spaces from the WSI name
                file = os.path.splitext(i)[0].replace(" ", "")
                print('\n\n'     "---------------------------------------------------------------------------------------------------------------------------------------------------------------")
                print('\n' f'************ Slide being processed: {file} ************')
                print('\n' f'Tiles generation for {file} has been started.')
                # When generating tiles the original file name (included the extension) is used to match the one in the QuPath project.
                time_start = time.time()
                for line in tilesGenerator(self.qupathProj, self.shellScript, self.groovyScript, wsi = i):
                    print(line)
                time_end = time.time()
                print('\n' f"Tiles generation for {file} has been completed.", '\n' f"Tiles can be found under: {os.path.join(self.tilesDir, file)}")
                timeDict[f"{file}"] = (time_end-time_start)
                
                # After tiles generation, tiles filtering and normalization is performed.
                normTilesDict.clear()
                print('\n' f'Tiles pre-processing for {file} has been started.')
                self.saveRes(self.tilesDir, preprocessingResDir, file, timeDict, normTilesDict, self.jpgNormTiles, self.lowerPerc, self.upperPerc)
                
        # If no list of WSIs is provided in input to the pipeline, the entire QuPath project will be processed.
        else:
            #print('\n\n'     "---------------------------------------------------------------------------------------------------------------------------------------------------------------")
            print('\n\n'     "----------------------------------------------------------------------- Tiles generation ----------------------------------------------------------------------")
            time_start = time.time()
            for line in tilesGenerator(self.qupathProj, self.shellScript, self.groovyScript):
                print(line)
            time_end = time.time()
            print('\n' "Tiles generation for the entire project has been completed", '\n' f'Tiles can be found under: {self.tilesDir}')
            timeDict["Project"] = (time_end-time_start)
            
            print('\n\n'     "--------------------------------------------------------------------- Tiles pre-processing ---------------------------------------------------------------------")
            
            for i in os.listdir(self.tilesDir):
                
                normTilesDict.clear()
                
                print('\n' f'************ Slide being processed: {i} ************')
                self.saveRes(self.tilesDir, preprocessingResDir, i, timeDict, normTilesDict, self.jpgNormTiles, self.lowerPerc, self.upperPerc)
                
        extractInfo(self.tilesDir, preprocessingResDir, self.resultsDir, self.wsiDir)
                
        print('\n'   "----------------------------------------------------------------------------------------------------------------------------------------------------------------")
        print(       "                                                             Tiles pre-processing completed!                                                                    ")
        print(       "----------------------------------------------------------------------------------------------------------------------------------------------------------------")
        print('\n')