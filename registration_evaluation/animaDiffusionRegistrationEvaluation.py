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
from subprocess import call, check_output

configFilePath = os.path.join(os.path.expanduser("~"), ".anima", "config.txt")
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')

# Argument parsing
parser = argparse.ArgumentParser(
    description="Performs registration pipelines and applies resulting transformations to evaluation data. Does this for registering a single data on another (HCP ids specified as input).")

parser.add_argument('-r', '--ref-index', type=str, required=True, help='Reference image index')
parser.add_argument('-m', '--mov-index', type=str, required=True, help='Moving image index')
parser.add_argument('-d', '--data-folder', type=str, default=".", help='Data main folder')

args = parser.parse_args()
tmpFolder = tempfile.mkdtemp()

animaPyramidalBMRegistration = os.path.join(animaDir, "animaPyramidalBMRegistration")
animaDenseSVFBMRegistration = os.path.join(animaDir, "animaDenseSVFBMRegistration")
animaDenseTensorSVFBMRegistration = os.path.join(animaDir, "animaDenseTensorSVFBMRegistration")
animaDenseMCMSVFBMRegistration = os.path.join(animaDir, "animaDenseMCMSVFBMRegistration")
animaTransformSerieXmlGenerator = os.path.join(animaDir, "animaTransformSerieXmlGenerator")
animaApplyTransformSerie = os.path.join(animaDir, "animaApplyTransformSerie")
animaTensorApplyTransformSerie = os.path.join(animaDir, "animaTensorApplyTransformSerie")
animaMCMApplyTransformSerie = os.path.join(animaDir, "animaMCMApplyTransformSerie")
animaFibersApplyTransformSerie = os.path.join(animaDir, "animaFibersApplyTransformSerie")
animaFibersCounter = os.path.join(animaDir, "animaFibersCounter")
animaDiceMeasure = os.path.join(animaDir, "animaDiceMeasure")
animaFuzzyDiceMeasure = os.path.join(animaDir, "animaFuzzyDiceMeasure")

dataDir = args.data_folder
f = open(os.path.join(dataDir, "Diffusion_Data_Preprocessed", "HCP105_Zenodo_Subjects_List.txt"), "r")
lines = f.readlines()
f.close()
refIndex = int(lines[int(args.ref_index)])
movIndex = int(lines[int(args.mov_index)])

# First runs 8 registration schemes with all possible combinations
# P1: affine registration
# P2: P1 + non linear anatomical registration
# P3: P1 + non linear tensor registration
# P4: P1 + non linear MCM registration
# P5: P2 + non linear tensor registration
# P6: P2 + non linear MCM registration
# P7: P3 + non linear MCM registration
# P8: P5 + non linear MCM registration

# Start by the basic affine transformation (P1)

refStructuralDir = os.path.join(dataDir, "Structural_Data_Preprocessed", str(refIndex))
refDiffusionDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(refIndex))
movStructuralDir = os.path.join(dataDir, "Structural_Data_Preprocessed", str(movIndex))
movDiffusionDir = os.path.join(dataDir, "Diffusion_Data_Preprocessed", str(movIndex))

resultsDir = os.path.join(dataDir, 'Results', 'Results_' + str(refIndex) + '_' + str(movIndex))
if os.path.exists(resultsDir):
    shutil.rmtree(resultsDir)

os.makedirs(resultsDir, exists_ok=True)

command = [animaPyramidalBMRegistration, "-r", os.path.join(refStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"),
           "-m", os.path.join(movStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"), "-o", os.path.join(tmpFolder, "movingAnat_aff.nrrd"),
           "-O", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-p", "4", "-l", "1", "--sp", "2", "--ot", "2", "--sym-reg", "2"]
call(command)

# Now apply transformation to diffusion images

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-o", os.path.join(tmpFolder, "movingAnat_aff_tr.xml")]
call(command)

command = [animaTensorApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_Tensors.nrrd"), "-t", os.path.join(tmpFolder, "movingAnat_aff_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingTensors_aff_init.nrrd")]
call(command)

command = [animaMCMApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_MCM_avg.mcm"), "-t", os.path.join(tmpFolder, "movingAnat_aff_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingMCM_aff_init.mcm")]
call(command)

# Moving to non linear anatomical registration (P2 and base for P5+ except P7)

command = [animaDenseSVFBMRegistration, "-r", os.path.join(refStructuralDir, "Images", "T1w_acpc_dc_restore_brain.nii.gz"),
           "-m", os.path.join(tmpFolder, "movingAnat_aff.nrrd"), "-o", os.path.join(tmpFolder, "movingAnat_nl.nrrd"),
           "-O", os.path.join(tmpFolder, "movingAnat_nl_tr.nrrd"), "--sym-reg", "2"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingAnat_nl_tr.nrrd"),
           "-o", os.path.join(tmpFolder, "movingAnat_nl_tr.xml")]
call(command)

command = [animaTensorApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_Tensors.nrrd"), "-t", os.path.join(tmpFolder, "movingAnat_nl_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingAnatTensors_nl_init.nrrd")]
call(command)

command = [animaMCMApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_MCM_avg.mcm"), "-t", os.path.join(tmpFolder, "movingAnat_nl_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingAnatMCM_nl_init.mcm")]
call(command)

# Non linear tensor registration (P3 and base for P7)

command = [animaDenseTensorSVFBMRegistration, "-r", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"),
           "-m", os.path.join(tmpFolder, "movingTensors_aff_init.nrrd"), "-o", os.path.join(tmpFolder, "movingTensors_nl.nrrd"),
           "-O", os.path.join(tmpFolder, "movingTensors_nl_tr.nrrd"), "--sym-reg", "2", "--metric", "3", "-s", "0.001"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingTensors_nl_tr.nrrd"),
           "-o", os.path.join(tmpFolder, "movingTensors_nl_tr.xml")]
call(command)

command = [animaMCMApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_MCM_avg.mcm"), "-t", os.path.join(tmpFolder, "movingTensors_nl_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingTensorsMCM_nl_init.mcm")]
call(command)

# Non linear MCM registration (P4)

command = [animaDenseMCMSVFBMRegistration, "-r", os.path.join(refDiffusionDir, "Images", "data_MCM_avg.mcm"),
           "-m", os.path.join(tmpFolder, "movingMCM_aff_init.mcm"), "-o", os.path.join(tmpFolder, "movingMCM_nl.mcm"),
           "-O", os.path.join(tmpFolder, "movingMCM_nl_tr.nrrd"), "--sym-reg", "2", "--metric", "2", "-s", "0.001"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingMCM_nl_tr.nrrd"),
           "-o", os.path.join(tmpFolder, "movingMCM_nl_tr.xml")]
call(command)

# Non linear tensor registration after anatomical registration (P5)

command = [animaDenseTensorSVFBMRegistration, "-r", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"),
           "-m", os.path.join(tmpFolder, "movingAnatTensors_nl_init.nrrd"), "-o", os.path.join(tmpFolder, "movingAnatTensors_nl.nrrd"),
           "-O", os.path.join(tmpFolder, "movingAnatTensors_nl_tr.nrrd"), "--sym-reg", "2", "--metric", "3", "-s", "0.001", "--sr", "1"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingAnat_nl_tr.nrrd"),
           "-i", os.path.join(tmpFolder, "movingAnatTensors_nl.nrrd"), "-o", os.path.join(tmpFolder, "movingAnatTensors_nl_tr.xml")]
call(command)

command = [animaMCMApplyTransformSerie, "-i", os.path.join(movDiffusionDir, "Images", "data_MCM_avg.mcm"), "-t", os.path.join(tmpFolder, "movingAnatTensors_nl_tr.xml"),
           "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"), "-o", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl_init.mcm")]
call(command)

# Non linear MCM registration after tensor registration alone (P7)

command = [animaDenseMCMSVFBMRegistration, "-r", os.path.join(refDiffusionDir, "Images", "data_MCM_avg.mcm"),
           "-m", os.path.join(tmpFolder, "movingTensorsMCM_nl_init.mcm"), "-o", os.path.join(tmpFolder, "movingTensorsMCM_nl.mcm"),
           "-O", os.path.join(tmpFolder, "movingTensorsMCM_nl_tr.nrrd"), "--sym-reg", "2", "--metric", "2", "-s", "0.001", "--sr", "1"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingTensors_nl_tr.nrrd"),
           "-i", os.path.join(tmpFolder, "movingTensorsMCM_nl_tr.nrrd"), "-o", os.path.join(tmpFolder, "movingTensorsMCM_nl_tr.xml")]
call(command)

# Non linear MCM registration after anatomical + tensors registration (P8)

command = [animaDenseMCMSVFBMRegistration, "-r", os.path.join(refDiffusionDir, "Images", "data_MCM_avg.mcm"),
           "-m", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl_init.mcm"), "-o", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl.mcm"),
           "-O", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl_tr.nrrd"), "--sym-reg", "2", "--metric", "2", "-s", "0.001", "--sr", "1"]
call(command)

command = [animaTransformSerieXmlGenerator, "-i", os.path.join(tmpFolder, "movingAnat_aff_tr.txt"), "-i", os.path.join(tmpFolder, "movingAnat_nl_tr.nrrd"),
           "-i", os.path.join(tmpFolder, "movingAnatTensors_nl_tr.nrrd"), "-i", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl_tr.nrrd"),
           "-o", os.path.join(tmpFolder, "movingAnatTensorsMCM_nl_tr.xml")]
call(command)

# Now applying obtained transformations to evaluation fiber tracts and parcellations
# First apply to fiber tracts on HCP data (from Wasserthal et al) and build fuzzy images of them
# Then apply transforms to structural parcellations
# Finally compute Dice scores

tracksList = ['AF_left', 'AF_right', 'ATR_left', 'ATR_right', 'CA', 'CC_1', 'CC_2', 'CC_3', 'CC_4', 'CC_5', 'CC_6',
              'CC_7', 'CG_left', 'CG_right', 'CST_left', 'CST_right', 'MLF_left', 'MLF_right', 'FPT_left', 'FPT_right',
              'FX_left', 'FX_right', 'ICP_left', 'ICP_right', 'IFO_left', 'IFO_right', 'ILF_left', 'ILF_right', 'MCP',
              'OR_left', 'OR_right', 'POPT_left', 'POPT_right', 'SCP_left', 'SCP_right', 'SLF_I_left', 'SLF_I_right',
              'SLF_II_left', 'SLF_II_right', 'SLF_III_left', 'SLF_III_right', 'STR_left', 'STR_right', 'UF_left',
              'UF_right', 'CC', 'T_PREF_left', 'T_PREF_right', 'T_PREM_left', 'T_PREM_right', 'T_PREC_left',
              'T_PREC_right', 'T_POSTC_left', 'T_POSTC_right', 'T_PAR_left', 'T_PAR_right', 'T_OCC_left',
              'T_OCC_right', 'ST_FO_left', 'ST_FO_right', 'ST_PREF_left', 'ST_PREF_right', 'ST_PREM_left',
              'ST_PREM_right', 'ST_PREC_left', 'ST_PREC_right', 'ST_POSTC_left', 'ST_POSTC_right', 'ST_PAR_left',
              'ST_PAR_right', 'ST_OCC_left', 'ST_OCC_right']

transformsList = ['movingAnat_aff', 'movingAnat_nl', 'movingTensors_nl', 'movingMCM_nl', 'movingAnatTensors_nl', 'movingAnatMCM_nl', 'movingTensorsMCM_nl', 'movingAnatTensorsMCM_nl']

for track in tracksList:
    command = [animaFibersCounter, "-i", os.path.join(refDiffusionDir, 'Tracks', track + '.vtp'), "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"),
               "-o", os.path.join(tmpFolder, track + "_ref_fCount.nrrd"), "-P"]
    call(command)

for transform in transformsList:
    command = [animaApplyTransformSerie, "-i", os.path.join(movStructuralDir, 'Masks', "wmparc.nii.gz"),
               "-t", os.path.join(tmpFolder, transform + '_tr.xml'), "-g", os.path.join(refStructuralDir, 'Masks', "wmparc.nii.gz"),
               "-o", os.path.join(resultsDir, transform + "_parcellation.nrrd"), "-n", "nearest"]
    call(command)

    command = [animaDiceMeasure, "-r", os.path.join(refStructuralDir, 'Masks', "wmparc.nii.gz"), "-t", os.path.join(resultsDir, transform + "_parcellation.nrrd"),
               "-o", os.path.join(resultsDir, transform + "_parcellation_dice.csv"), "-X"]
    call(command)

    command = [animaDiceMeasure, "-r", os.path.join(refStructuralDir, 'Masks', "wmparc.nii.gz"), "-t", os.path.join(resultsDir, transform + "_parcellation.nrrd"),
               "-o", os.path.join(resultsDir, transform + "_parcellation_total_overlap.csv"), "-X", "-T"]
    call(command)

    outFileTracks = open(os.path.join(resultsDir, transform + "_tracks_fuzzy_dice.csv"),'w')
    for track in tracksList:
        command = [animaFibersApplyTransformSerie, "-i", os.path.join(movDiffusionDir, 'Tracks', track + '.vtp'),
                   "-t", os.path.join(tmpFolder, transform + '_tr.xml'), "-o", os.path.join(tmpFolder, track + '_' + transform + '.vtp')]
        call(command)

        command = [animaFibersCounter, "-i", os.path.join(tmpFolder, track + '_' + transform + '.vtp'), "-g", os.path.join(refDiffusionDir, "Images", "data_Tensors.nrrd"),
                   "-o", os.path.join(resultsDir, track + '_' + transform + "_fCount.nrrd"), "-P"]
        call(command)

        command = [animaFuzzyDiceMeasure, "-r", os.path.join(tmpFolder, track + "_ref_fCount.nrrd"), "-t", os.path.join(resultsDir, track + '_' + transform + "_fCount.nrrd")]
        fDiceData = float(check_output(command))
        outFileTracks.write(str(fDiceData) + ", ")

    outFileTracks.write("\n")
    outFileTracks.close()

shutil.rmtree(tmpFolder)
