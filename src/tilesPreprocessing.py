# -*- coding: utf-8 -*-
"""
Created on Fri Apr 22 15:00:23 2022

@author: angelomm
"""
from preprocessing import pipeline
import argparse
import click
import os
import pandas as pd

def create_parser():
    Description = "********* The pipeline performs tiles generation and pre-processing starting from a QuPath project. *********"

    Epilog = "Example of usage: tilesPreprocessing.py <QUPATH_PROJ>"

    # Create the parser
    parser = argparse.ArgumentParser(description = Description, epilog = Epilog, formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    # Add the positional argument to the parser
    
    parser.add_argument('QUPATH_PROJ', type = str, help = 'Absolute path to the .qpproj file')

    # Add the optional arguments to the parser

    parser.add_argument('--groovyScript', nargs = '?', default = os.path.join(os.getcwd(), "generateTiles.groovy"), type = str, dest = 'GROOVY_SCRIPT_DIR', help = 'Absolute path to the .groovy script used for tiles generation')

    parser.add_argument('--shellScript', nargs = '?', default = os.path.join(os.getcwd(), "runQupath.sh"), type = str, dest = 'SHELL_SCRIPT_DIR', help = 'Absolute path to the .sh script used for tiles generation')

    parser.add_argument('--tilesDir', nargs = '?', type = str, dest = "TILES_DIR", help = 'Absolute path to the directory where the generated tiles will be stored')

    parser.add_argument('--outputDir', nargs = '?', type = str, dest = "OUTPUT_DIR", help = 'Absolute path to the directory where results from pre-processing will be stored')

    parser.add_argument('--wsiDir', nargs = '?', default = None, type = str, dest = "WSIs_DIR", help = 'Absolute path to the folder containing the dataframe storing information on the WSIs to process')

    parser.add_argument('--jpgNormTiles', action = 'store_true', dest = 'JPG_NORM_TILES', help = 'Save the normalized tiles in JPG other than as a pickle file')
    
    parser.add_argument('--wsiList', nargs = '+', default = None, type = str, dest = "WSIs_LIST", help = 'Name of the WSIs to process')

    parser.add_argument('--lowerPerc', nargs = '?', default = 10, type = int, dest = "LOWER_PERCENTILE", help = 'Lower percentile for tiles filtering')

    parser.add_argument('--upperPerc', nargs = '?', default = 90, type = int, dest = "UPPER_PERCENTILE", help = 'Upper percentile for tiles filtering')
    
    return parser

# Parse arguments
parser = create_parser()
args = parser.parse_args()

# Set the default value of both tiles and results directory to the QuPath project directory
if args.TILES_DIR is None:
    dirname = os.path.dirname(args.QUPATH_PROJ)
    args.TILES_DIR = os.path.join(dirname,"tiles")
elif args.TILES_DIR is not None:
    if "tiles" != os.path.basename(os.path.normpath(args.TILES_DIR)):
        args.TILES_DIR = os.path.join(args.TILES_DIR, "tiles")
    
if args.OUTPUT_DIR is None:
    dirname = os.path.dirname(args.QUPATH_PROJ)
    args.OUTPUT_DIR = os.path.join(dirname, "results")


print('\n\n\n\n', "================================================================ TILES PRE-PROCESSING PIPELINE ================================================================")

print('\n',       "===============================================================================================================================================================")

print('\n\n' "The following absolute paths will be used for tiles pre-processing:", "\n\n" f"QUPATH_PROJ: {args.QUPATH_PROJ}", "\n\n" f"GROOVY_SCRIPT_DIR: {args.GROOVY_SCRIPT_DIR}", "\n\n" f"SHELL_SCRIPT_DIR: {args.SHELL_SCRIPT_DIR}")

print('\n' f"The tiles to pre-process will be stored under: {args.TILES_DIR}")

if args.WSIs_DIR == None and args.WSIs_LIST == None:
    print("\n" "No information was provided on the WSIs to process. The entire QuPath project will be processed.")
    
    qupath = click.prompt('\n'"Proceed with tiles generation and pre-processing? y/n")
    if qupath == 'y':
        wsiList = args.WSIs_DIR
        os.makedirs(f"{args.OUTPUT_DIR}/preprocessingRes", exist_ok=True)
        logfile = os.path.join(f"{args.OUTPUT_DIR}/preprocessingRes", "logfile.log")
    else:
        exit()

elif args.WSIs_DIR != None:
    print('\n' f"The following absolute path to the file <slidesToProcess.csv> was provided in input: {args.WSIs_DIR}")
    
    wsi_dir = click.prompt('\n'"Proceed with tiles generation and pre-processing? y/n")
    if wsi_dir == 'y':
        wsiDir = args.WSIs_DIR
        wsiDf = pd.read_csv(os.path.join(wsiDir, "slidesToProcess.csv"))
        wsiList = wsiDf['Slide'].tolist()
    else:
        exit()

elif args.WSIs_LIST != None:
    print('\n' f"The following WSI(s) will be processed: {args.WSIs_LIST}")
    
    wsi_list = click.prompt('\n'"Proceed with tiles generation and pre-processing? y/n")
    if wsi_list == 'y':
        wsiList = args.WSIs_LIST
    else:
        exit()

else:
    print('\n''You provided inconsistent arguments. Please check again.')
    exit()

with open(f'{args.GROOVY_SCRIPT_DIR}','r') as fn:
    ln = fn.readlines()
for idx, i in enumerate(ln):
    if i.startswith("def pathOutput = buildFilePath"):
        ln[idx] = f"def pathOutput = buildFilePath('{args.TILES_DIR}', name_n)\n"
    elif i.startswith("File logfile = new File"):
        ln[idx] = f"File logfile = new File('{args.OUTPUT_DIR}', 'logfile.log')\n"
with open(f'{args.GROOVY_SCRIPT_DIR}','w') as fn:
    fn.writelines(ln)
    fn.close()
      
# Check if the results directory exists, otherwise create it
outputDir = args.OUTPUT_DIR
check_outputDir = os.path.isdir(outputDir)
if not check_outputDir:
	os.makedirs(outputDir)
	print('\n\n' f"The folder {args.OUTPUT_DIR} has been created.", "Results from tiles pre-processing will be stored here.")
else:
	print('\n\n' f"Results from tiles pre-processing will be stored under: {args.OUTPUT_DIR}")

tilesPreprocessing = pipeline(args.QUPATH_PROJ, args.GROOVY_SCRIPT_DIR, args.SHELL_SCRIPT_DIR, args.TILES_DIR, args.OUTPUT_DIR, args.WSIs_DIR, jpgNormTiles = args.JPG_NORM_TILES, wsiList = wsiList, lowerPerc = args.LOWER_PERCENTILE, upperPerc = args.UPPER_PERCENTILE)

tilesPreprocessing.initialize()
