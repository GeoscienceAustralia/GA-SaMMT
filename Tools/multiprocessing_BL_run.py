"""
Author: Zhi Huang
Organisation: Geoscience Australia
Email: Zhi.Huang@ga.gov.au
Last update: May 22, 2024
Python version: 3+
ArcGIS Pro: 2.6.4 and above """

import arcpy
from arcpy import env
from arcpy.sa import *
from datetime import datetime
from multiprocessing import Pool
import multiprocessing
# This math module must be imported in this script.
# It is not used directly in this script, but used in the imported toolbox.
import math

# This function adds a featID field with unique ID values
def addIDField(inFeat, fieldName):
    # inFeat: input featureclass (or table)
    # fieldName: the field in the inFeat to be calculated from the joinFeat

    fieldType = "LONG"
    fieldPrecision = 15

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(inFeat, fieldName, fieldType, fieldPrecision)

    expression = "!OBJECTID!"

    arcpy.CalculateField_management(inFeat, fieldName, expression, "PYTHON_9.3")

    arcpy.AddMessage(fieldName + " added and calculated")
    return


# This function creates temporary workspaces and folders,
# splits the input bathymetric low featureclass into subsets,
# copies a subset and input bathymetry and slope grids into each workspace,
# and specifies temporary head and foot featureclasses
def splitFeat(workspace, inFeat, inBathy, inSlope, noSplit):
    # workspace: the workspace which contains inFeat, inBathy and inSlope
    # inFeat: input bathymetric high or low featureclass
    # inBathy: input bathymetry grid
    # inSlope: input slope grid
    # noSplit: the number of subsets to split the inFeat into

    noFeat = int(arcpy.GetCount_management(inFeat).getOutput(0))
    featCount = int(noFeat / noSplit)

    featList = []
    headFeatList = []
    footFeatList = []
    bathyList = []
    slopeList = []
    tempfolderList = []
    workspaceList = []

    path = workspace.rstrip(workspace.split('/')[-1])
    path = path.rstrip('/')
    baseName = workspace.split('/')[-1]
    baseName = baseName.split('.')[0]
    inBathy = inBathy.split('/')[-1]
    inSlope = inSlope.split('/')[-1]
    inFeat = inFeat.split('/')[-1]

    # loop through subsets
    i = 1
    while i <= noSplit:
        # create a File Geodatabase
        gdbName = baseName + str(i) + '.gdb'
        arcpy.CreateFileGDB_management(path, gdbName)
        arcpy.AddMessage(gdbName + ' created')

        workspace = path + '/' + gdbName
        workspaceList.append(workspace)

        # copy inBathy
        data1 = path + '/' + gdbName + '/' + inBathy
        bathyList.append(data1)
        arcpy.Copy_management(inBathy, data1)
        arcpy.AddMessage(inBathy + ' copied')

        # copy inSlope
        data2 = path + '/' + gdbName + '/' + inSlope
        slopeList.append(data2)
        arcpy.Copy_management(inSlope, data2)
        arcpy.AddMessage(inSlope + ' copied')

        # select a subset of inFeat depending on the number of splits
        startID = (i - 1) * featCount
        if i == noSplit:
            endID = noFeat
        else:
            endID = i * featCount
        whereClause = '((OBJECTID > ' + str(startID) + ') And (OBJECTID <= ' + str(endID) + '))'
        outFeat = path + '/' + gdbName + '/' + inFeat + '_' + str(i)
        arcpy.analysis.Select(inFeat, outFeat, whereClause)
        arcpy.AddMessage(outFeat + ' generated')
        featList.append(outFeat)

        # create temp folder
        folderName = 'temp' + str(i)
        arcpy.CreateFolder_management(path, folderName)
        arcpy.AddMessage(folderName + ' created')
        tempFolder = path + '/' + folderName
        tempfolderList.append(tempFolder)
        # specify head and foot featureclass variables
        headFeat = outFeat + '_head'
        headFeatList.append(headFeat)
        footFeat = outFeat + '_foot'
        footFeatList.append(footFeat)

        i += 1
    return workspaceList, tempfolderList, featList, headFeatList, footFeatList, bathyList, slopeList


# This function calculates shape attributes for the bathymetric low features
def add_shape_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    headFeat = arg[3]
    footFeat = arg[4]
    inBathy = arg[5]
    additionalAttributes = arg[8]
    # importing the AddAttributes toolbox to calculate the shape attributes
    arcpy.ImportToolbox("C:/Tools/multiprocess_test/AddAttributes.pyt")
    env.workspace = workspaceName
    env.overwriteOutput = True
    arcpy.AddAttributes.Add_Shape_Attributes_Low_Tool(inFeat, inBathy, tempFolder, headFeat, footFeat,
                                                      additionalAttributes)

    return


# This function calculates topographic attributes for the bathymetric low features
def add_topographic_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat = arg[2]
    headFeat = arg[3]
    footFeat = arg[4]
    inBathy = arg[5]
    inSlope = arg[6]
    # importing the AddAttributes toolbox to calculate the topographic attributes
    arcpy.ImportToolbox("C:/Tools/multiprocess_test/AddAttributes.pyt")
    env.workspace = workspaceName
    env.overwriteOutput = True
    arcpy.AddAttributes.Add_Topographic_Attributes_Low_Tool(inFeat, inBathy, inSlope, headFeat, footFeat)

    return


# This function calculates profile attributes for the bathymetric low features
def add_profile_attributes_low_function(arg):
    """ pass a featureclass"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[5]
    areaT = arg[7]
    # importing the AddAttributes toolbox to calculate the profile attributes
    arcpy.ImportToolbox("C:/Tools/multiprocess_test/AddAttributes.pyt")
    env.workspace = workspaceName
    env.overwriteOutput = True
    arcpy.AddAttributes.Add_Profile_Attributes_Low_Tool(inFeat, inBathy, areaT, tempFolder)

    return

# main function
if __name__ == '__main__':
    # report a message
    print('Starting task...')
    time1 = datetime.now()

    env.overwriteOutput = True
    # import the Python toolbox
    arcpy.ImportToolbox("C:/Tools/multiprocess_test/AddAttributes.pyt")
    # set input parameters
    env.workspace = 'C:/temp3/test.gdb'
    inFeatClass = 'test_BL_48'
    inBathy = 'Grid12_box'
    inSlope = 'Grid12_box_slope'
    tempFolder = 'C:/semi_automation/temp'
    areaT = '1 SquareMeters'
    # whether to add additional shape attributes
    additionalAttributes = True
    headFeatClass = inFeatClass + '_head'
    footFeatClass = inFeatClass + '_foot'

    # get the number of logical processors in your computer for the multiprocessing
    nCPU = multiprocessing.cpu_count()
    # You can specify a more appropriate number of logical processors for the multiprocessing
    # Otherwise, comment out the following line
    nCPU = 6
    arcpy.AddMessage("Using " + str(nCPU) + " CPU processors for multiprocessing")

    workspaceName = env.workspace

    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    # check the 'featID' field exists
    # if not, add and calculate it
    if "featID" not in field_names:
        arcpy.AddMessage("Adding an unique featID...")
        addIDField(inFeatClass, "featID")

    # call the splitFeat() to split the input features into subsets, copy bathy and slope, etc
    workspaceList, tempfolderList, featList, headFeatList, footFeatList, bathyList, slopeList = splitFeat(
        workspaceName, inFeatClass, inBathy, inSlope, nCPU)
    # building argList
    argList = []
    i = 0
    while i < len(featList):
        argList.append(
            [workspaceList[i], tempfolderList[i], featList[i], headFeatList[i], footFeatList[i], bathyList[i],
             slopeList[i], areaT, additionalAttributes])
        i += 1

    print(argList)
    # create the process pool for multiprocessing

    # calculating shape attributes
    arcpy.AddMessage('calculating shape attributes ...')
    with Pool(nCPU) as pool:
        # perform calculations
        results1 = pool.map(add_shape_attributes_low_function, argList)

    # calculating topographic attributes
    arcpy.AddMessage('calculating topographic attributes ...')
    with Pool(nCPU) as pool:
        # perform calculations
        results2 = pool.map(add_topographic_attributes_low_function, argList)

    # calculating profile attributes
    arcpy.AddMessage('calculating profile attributes ...')
    with Pool(nCPU) as pool:
        # perform calculations
        results3 = pool.map(add_profile_attributes_low_function, argList)

    # merge the subsets of the input features
    outFeatClass = "mergedFeat"
    arcpy.Merge_management(featList, outFeatClass)
    outFeatClass1 = "mergedFeat1"
    arcpy.Merge_management(headFeatList, outFeatClass1)
    outFeatClass2 = "mergedFeat2"
    arcpy.Merge_management(footFeatList, outFeatClass2)
    arcpy.AddMessage('final merge done')
    # copy the merged features and replace the input featureclass
    arcpy.Copy_management(outFeatClass, inFeatClass)
    arcpy.Copy_management(outFeatClass1, headFeatClass)
    arcpy.Copy_management(outFeatClass2, footFeatClass)
    arcpy.AddMessage('final copy done')
    arcpy.Delete_management(outFeatClass)
    arcpy.Delete_management(outFeatClass1)
    arcpy.Delete_management(outFeatClass2)

    # compact the geodatabase to reduce its size
    arcpy.Compact_management(workspaceName)
    arcpy.AddMessage("Compacted the geodatabase")

    # delete all temporary workspaces and folders
    for workspace in workspaceList:
        arcpy.Delete_management(workspace)
    arcpy.AddMessage("All temporary workspaces are deleted")

    for folder in tempfolderList:
        arcpy.Delete_management(folder)
    arcpy.AddMessage("All temporary folders are deleted")

    time2 = datetime.now()
    diff = time2 - time1
    print('took', diff, 'to finish')
