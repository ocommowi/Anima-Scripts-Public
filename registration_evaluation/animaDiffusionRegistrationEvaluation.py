#!/usr/bin/python3
# Warning: works only on unix-like systems, not windows where "python animaDiffusionRegistrationEvaluation.py ..." has to be run

import sys
import argparse
import tempfile

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

import os
import shutil
from subprocess import call

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
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

parser.add_argument('-r', '--ref-index', type=str, required=True, help='Reference image index')
parser.add_argument('-m', '--mov-index', type=str, required=True, help='Moving image index')
parser.add_argument('-d', '--data-folder', type=str, default=".", help='Data main folder')

args = parser.parse_args()
tmpFolder = tempfile.mkdtemp()

animaPyramidalBMRegistration = os.path.join(animaDir,"animaPyramidalBMRegistration")
animaDenseSVFBMRegistration = os.path.join(animaDir,"animaDenseSVFBMRegistration")
animaDenseTensorSVFBMRegistration = os.path.join(animaDir,"animaDenseTensorSVFBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir,"animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir,"animaApplyTransformSerie")
animaTensorApplyTransformSerie = os.path.join(animaDir,"animaTensorApplyTransformSerie")

dataDir = args.data_folder
f = open(os.path.join(dataDir, "Diffusion_Data_Preprocessed", "HCP105_Zenodo_Subjects_List.txt"), "r")
lines = f.readlines()
f.close()
refIndex = int(lines[args.ref_index])
movIndex = int(lines[args.mov_index])

# Start by the basic affine transformation (P1)

refStructuralDir = os.path.join(dataDir, "Structural_Data_Preprocessed", str(refIndex))
refDiffusionDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(refIndex))
movStructuralDir = os.path.join(dataDir, "Structural_Data_Preprocessed", str(movIndex))
movDiffusionDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(movIndex))

command = [animaPyramidalBMRegistration, "-r", os.path.join(refStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"),
           "-m", os.path.join(movStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"), "-o", os.path.join(tmpFolder, "moving_aff.nrrd"),
           "-O", os.path.join(tmpFolder, "moving_aff_tr.txt"), "-p", "4", "-l", "1", "--sp", "2", "--ot", "2", "--sym-reg", "2"]
call(command)

# Now apply transformation to diffusion tensor images

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "moving_aff_tr.txt"), "-o", os.path.join(tmpFolder, "moving_aff_tr.xml")]
call(command)

command = [animaTensorApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "Tensors.nrrd"), "-t", os.path.join(tmpFolder, "moving_aff_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingTensors_aff.nrrd")]
call(command)

# Moving to non linear anatomical registration

command = [animaDenseSVFBMRegistration, "-r", os.path.join(refStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"),
           "-m", os.path.join(tmpFolder, "moving_aff.nrrd"), "-o", os.path.join(tmpFolder, "moving_nl.nrrd"),
           "-O", os.path.join(tmpFolder, "moving_nl_tr.nrrd"), "--sym-reg", "2"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "moving_aff_tr.txt"), "-i", os.path.join(tmpFolder, "moving_nl_tr.nrrd"),
           "-o", os.path.join(tmpFolder, "moving_aff_tr.xml")]
call(command)

command = [animaTensorApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "Tensors.nrrd"), "-t", os.path.join(tmpFolder, "moving_nl_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingTensors_nl.nrrd")]
call(command)

shutil.rmtree(tmpFolder)
