#!/usr/bin/python3
# Warning: works only on unix-like systems, not windows where "python animaPrepareAdditionalDiffusionDataForRegistration.py ..." has to be run

import sys
import argparse
import tempfile

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
import glob
import shutil
from subprocess import call, check_output

configFilePath = os.path.join(os.path.expanduser("~"), ".anima", "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Performs registration pipelines and applies resulting transformations to evaluation data. Does this for registering a single data on another (HCP ids specified as input).")

parser.add_argument('-i', '--index', type=str, required=True, help='Image index')
parser.add_argument('-d', '--data-folder', type=str, default=".", help='Data main folder')

args = parser.parse_args()
tmpFolder = tempfile.mkdtemp()

pythonExecutable = sys.executable
animaMCMEstimationScript = os.path.join(animaScriptsDir, "diffusion", "animaMultiCompartmentModelEstimation.py")
animaDTIEstimator = os.path.join(animaDir, "animaDTIEstimator")

dataDir = args.data_folder
f = open(os.path.join(dataDir, "Diffusion_Data_Preprocessed", "HCP105_Zenodo_Subjects_List.txt"), "r")
lines = f.readlines()
f.close()
dataIndex = int(lines[int(args.index)])

diffDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(dataIndex), "Images")
maskDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(dataIndex), "Masks")

# Estimate tensors

command = [animaDTIEstimator, "-i", os.path.join(diffDir, "data.nii.gz"), "-b", os.path.join(diffDir, "data.bval"),
           "-g", os.path.join(diffDir, "data.bvec"), "-m", os.path.join(maskDir, "nodif_brain_mask.nii.gz"), "-o", os.path.join(diffDir, "data_Tensors.nrrd")]
call(command)

# Estimate tensor DCM (with model averaging)

command = [pythonExecutable, animaMCMEstimationScript, "-i", os.path.join(diffDir, "data.nii.gz"), "-b", os.path.join(diffDir, "data.bval"),
           "-g", os.path.join(diffDir, "data.bvec"), "-m", os.path.join(maskDir, "nodif_brain_mask.nii.gz"), "-t", "tensor", "-n", "3", "--hcp"]
call(command)

# Remove unused files

for f in glob.glob(os.path.join(diffDir, "data_MCM_avg_*.nrrd")) + glob.glob(os.path.join(diffDir, "*List.txt")) + glob.glob(os.path.join(diffDir, "data_MCM_N*")):
    if os.path.isdir(f):
        shutil.rmtree(f)
    else:
        os.remove(f)
