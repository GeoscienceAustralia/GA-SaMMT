"""
Author: Zhi Huang
Organisation: Geoscience Australia
Email: Zhi.Huang@ga.gov.au
Last update: June 04, 2024
Python version: 3+
ArcGIS Pro: 2.6.4 and above """

import math
import os
import sys
from datetime import datetime

import arcpy
import numpy as np
import pandas as pd
from arcpy import env
from arcpy.sa import *

from multiprocessing import Pool
import multiprocessing

from importlib import reload
import HelperFunctions

arcpy.CheckOutExtension("Spatial")

# All the helper functions are defined here

# This function executes the multiprocessing to calculate the shape attributes for the bathymetric high features
def execute_shape_BH(argList, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    # use python window instead of ArcGIS Pro application for the multiprocessing
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        results = pool.map(add_shape_attributes_high_function, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function executes the multiprocessing to calculate the shape attributes for the bathymetric low features
def execute_shape_BL(argList, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        results = pool.map(add_shape_attributes_low_function, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function executes the multiprocessing to calculate the profile attributes for the bathymetric high features
def execute_profile_BH(argList, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        results = pool.map(add_profile_attributes_high_function, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function executes the multiprocessing to calculate the profile attributes for the bathymetric low features
def execute_profile_BL(argList, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        results = pool.map(add_profile_attributes_low_function, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function calculates the shape attributes for the bathymetric high features
def add_shape_attributes_high_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    # calling individual functions to calculate the shape features
    calculateCompactness(inFeat)
    calculateCircularity_Convexity_Solidity(workspaceName, inFeat)
    calculateSinuosity_LwR(workspaceName, tempFolder, inFeat, inBathy)

    return

# This function calculates the shape attributes for the bathymetric low features
def add_shape_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    headFeat = arg[3]
    footFeat = arg[4]
    inBathy = arg[5]
    additionalOption = arg[6]
    # calling individual functions to calculate the shape features
    calculateCompactness(inFeat)
    calculateCircularity_Convexity_Solidity(workspaceName, inFeat)
    calculateSinuosity_LwR_WdR_Slopes(workspaceName, tempFolder, inFeat, inBathy, headFeat, footFeat, additionalOption)

    return

# This function calculates the profile attributes for the bathymetric high features
def add_profile_attributes_high_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    areaT = arg[4]
    # calling individual functions to calculate the shape features
    calculateProfileBH(workspaceName, tempFolder, inFeat, inBathy, areaT)

    return

# This function calculates the profile attributes for the bathymetric low features
def add_profile_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    areaT = arg[4]
    # calling individual functions to calculate the shape features
    calculateProfileBL(workspaceName, tempFolder, inFeat, inBathy, areaT)

    return


# This function splits each polygon in the featureclass into multiple sub-polygons along its long axis
def splitPolygon(workspace, inFeatClass, MbrFeatClass, splitFeatClass):
    # workspace: location of workspace
    # inFeatClass: input Bathymetric High (Low) features
    # MbrFeatClass: input bounding rectangle featureclass
    # splitFeatClass: output featureclass containing the splitted features

    mergeList = []
    itemList = []
    inFeat = workspace + "/" + "selection"
    MbrFeat = workspace + "/" + "MBR_selection"
    itemList.append(MbrFeat)
    itemList.append(inFeat)
    MbrPoints = workspace + "/" + "bounding_rectangle_points"
    itemList.append(MbrPoints)
    fishnetFeat = workspace + "/" + "fishnet"
    itemList.append(fishnetFeat)
    # loop through each polygon
    cursor1 = arcpy.SearchCursor(inFeatClass)
    i = 1
    for row1 in cursor1:
        if i % 100 == 1:
            arcpy.Compact_management(workspace)
            arcpy.AddMessage("Compacted the geodatabase")
        time1 = datetime.now()
        featID = row1.getValue("featID")
        MbrL = row1.getValue("rectangle_Length")
        MbrW = row1.getValue("rectangle_Width")
        whereClause = '"featID" = ' + str(featID)
        arcpy.AddMessage("working on featID: " + str(featID))
        # select one polygon and its bounding polygon
        arcpy.Select_analysis(inFeatClass, inFeat, whereClause)
        arcpy.Select_analysis(workspace + "/" + MbrFeatClass, MbrFeat, whereClause)
        arcpy.AddMessage("selection done")

        # convert bounding rectangle to points
        arcpy.FeatureVerticesToPoints_management(MbrFeat, MbrPoints, "ALL")
        arcpy.AddMessage("bounding to points done")
        # add x and y
        arcpy.AddXY_management(MbrPoints)
        arcpy.AddMessage("Add x and y done")
        # get x and y values for the starting and ending points
        cursor = arcpy.SearchCursor(MbrPoints)
        row = cursor.next()
        start_x = row.getValue("POINT_X")
        start_y = row.getValue("POINT_Y")

        row = cursor.next()
        end_x = row.getValue("POINT_X")
        end_y = row.getValue("POINT_Y")

        del cursor, row

        # create fishnet

        # Set coordinate system of the output fishnet as the input dataset
        env.outputCoordinateSystem = arcpy.Describe(MbrFeat).spatialReference
        # Set the origin of the fishnet
        originCoordinate = str(start_x) + " " + str(start_y)
        # Set the orientation
        yAxisCoordinate = str(end_x) + " " + str(end_y)
        # Set the number of rows and columns together with origin and opposite corner
        # determine the size of each cell (sub-polygon) based on the length of bounding rectangle (unit: metre)
        if MbrL > 10000:
            numRows = int(MbrL / 200) + 1
        elif MbrL > 1000:
            numRows = int(MbrL / 100) + 1
        elif MbrL > 50:
            numRows = int(MbrL / 50) + 1
        else:
            numRows = 2

        cellSizeWidth = MbrW
        cellSizeHeight = MbrL / numRows
        numColumns = 1

        oppositeCorner = "#"
        # Create a point label feature class
        labels = "NO_LABELS"
        # Extent is set by origin and opposite corner - no need to use a template fc
        templateExtent = "#"
        # Each output cell will be a polygon
        geometryType = "POLYGON"
        arcpy.CreateFishnet_management(
            fishnetFeat,
            originCoordinate,
            yAxisCoordinate,
            cellSizeWidth,
            cellSizeHeight,
            numRows,
            numColumns,
            oppositeCorner,
            labels,
            templateExtent,
            geometryType,
        )
        arcpy.AddMessage("Fishnet done")

        # intersect
        intersectOut1 = workspace + "/" + "intersectOut" + str(featID)
        itemList.append(intersectOut1)
        mergeList.append(intersectOut1)
        inFeats = [inFeat, fishnetFeat]
        arcpy.Intersect_analysis(inFeats, intersectOut1)
        arcpy.AddMessage("intersect done")
        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to split this polygon.")

        i += 1

    del cursor1, row1

    # merge all features together

    arcpy.Merge_management(mergeList, splitFeatClass)
    arcpy.AddMessage("merge done")
    HelperFunctions.deleteDataItems(itemList)



# This functions calculates Compactness
def calculateCompactness(inFeatClass):
    # inFeatClass: input Bathymetry High (Low) features

    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    fieldName = "Compactness"
    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(
            inFeatClass, fieldName, fieldType, fieldPrecision, fieldScale
        )

    # This is the compactness equation
    expression = (
        "4*math.pi*"
        + "!"
        + "SHAPE_AREA"
        + "!"
        + "/"
        + "!"
        + "SHAPE_LENGTH"
        + "!"
        + "/"
        + "!"
        + "SHAPE_LENGTH"
        + "!"
    )
    arcpy.CalculateField_management(
        inFeatClass, fieldName, expression, "PYTHON3"
    )
    arcpy.AddMessage(fieldName + " added and calculated")


# This function calculates Circularity, Convexity and Solidity
def calculateCircularity_Convexity_Solidity(workspace, inFeatClass):
    # workspace: the location of the workspace
    # inFeatClass: input Bathymetry High (Low) features

    itemList = []
    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]

    env.workspace = workspace
    env.overwriteOutput = True
    # generate bounding convex hull
    chFeat = "convex_hull"
    itemList.append(chFeat)
    arcpy.MinimumBoundingGeometry_management(
        inFeatClass, chFeat, "CONVEX_HULL", "NONE", "", "MBG_FIELDS"
    )
    # add area and perimeter fields of chFeat to inFeatClass

    field = "convexhull_Area"
    inID = "featID"
    joinID = "featID"
    expression = "!" + chFeat + "." + "SHAPE_AREA" + "!"
    HelperFunctions.addField(inFeatClass, chFeat, field, inID, joinID, expression)
    field = "convexhull_Perimeter"
    expression = "!" + chFeat + "." + "SHAPE_LENGTH" + "!"
    HelperFunctions.addField(inFeatClass, chFeat, field, inID, joinID, expression)
    arcpy.AddMessage("two convex hull fields added")

    fieldList = ["Circularity", "Convexity", "Solidity"]
    for fieldName in fieldList:
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(
                inFeatClass, fieldName, fieldType, fieldPrecision, fieldScale
            )

        if fieldName == "Circularity":
            # Circularity equation
            expression = (
                "4*math.pi*"
                + "!"
                + "SHAPE_AREA"
                + "!"
                + "/"
                + "!"
                + "convexhull_Perimeter"
                + "!"
                + "/"
                + "!"
                + "convexhull_Perimeter"
                + "!"
            )
        elif fieldName == "Convexity":
            # Convexity equation
            expression = (
                "!"
                + "convexhull_Perimeter"
                + "!"
                + "/"
                + "!"
                + "SHAPE_LENGTH"
                + "!"
            )
        elif fieldName == "Solidity":
            # Solidity equation
            expression = (
                "!" + "SHAPE_AREA" + "!" + "/" + "!" + "convexhull_Area" + "!"
            )

        arcpy.CalculateField_management(
            inFeatClass, fieldName, expression, "PYTHON3"
        )
    arcpy.AddMessage(" Circularity, Convexity and Solidity added and calculated")
    HelperFunctions.deleteDataItems(itemList)


# This functions calculates sinuosity, length to width ratio,
# and other shape attributes for the Bathymetric High features
def calculateSinuosity_LwR(workspace, tempFolder, inFeatClass, inBathy):
    # workspace: the location of the workspace
    # tempFolder: the location of the temporary folder
    # inFeatClass: input Bathymetry High (Low) features
    # inBathy: input bathymetry grid

    env.workspace = workspace
    env.overwriteOutput = True

    time1 = datetime.now()
    itemList = []
    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    # generate bounding rectangle
    MbrFeatClass = "bounding_rectangle"
    itemList.append(MbrFeatClass)
    arcpy.MinimumBoundingGeometry_management(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    # add MBG_LENGTH, MBG_WIDTH AND MBG_ORIENTATION to inFeatClass
    field = "rectangle_Length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + MbrFeatClass + "." + "MBG_Length" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    field = "rectangle_Width"
    expression = "!" + MbrFeatClass + "." + "MBG_Width" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    field = "rectangle_Orientation"
    expression = "!" + MbrFeatClass + "." + "MBG_Orientation" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    arcpy.AddMessage("three bounding rectangle fields added")

    fieldList = [
        "head_foot_length",
        "sinuous_length",
        "Sinuosity",
        "mean_width",
        "LengthWidthRatio",
    ]

    for fieldName in fieldList:
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(
                inFeatClass, fieldName, fieldType, fieldPrecision, fieldScale
            )
    # call the helper function to split each polygon in the inFeatClass into multiple polygons
    splitFeatClass = workspace + "/" + "inFeatClass_splitted"
    itemList.append(splitFeatClass)
    splitPolygon(workspace, inFeatClass, MbrFeatClass, splitFeatClass)
    arcpy.AddMessage("inFeatClass splitted")
    # convert polygon to line
    lineFeatClass1 = workspace + "/" + "lineFeatClass1"
    itemList.append(lineFeatClass1)
    arcpy.PolygonToLine_management(splitFeatClass, lineFeatClass1)
    arcpy.AddMessage("polygon to line done")
    # selection
    lineFeatClass2 = workspace + "/" + "lineFeatClass2"
    itemList.append(lineFeatClass2)
    whereClause = "LEFT_FID <> -1"
    arcpy.Select_analysis(lineFeatClass1, lineFeatClass2, whereClause)
    arcpy.AddMessage("selection done")
    # spatial join
    lineFeatClass3 = workspace + "/" + "lineFeatClass3"
    itemList.append(lineFeatClass3)
    arcpy.SpatialJoin_analysis(
        lineFeatClass2,
        inFeatClass,
        lineFeatClass3,
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        "#",
        "WITHIN",
    )
    arcpy.AddMessage("spatial join done")
    # summary statistics
    outTab1 = "outTab1"
    itemList.append(outTab1)
    statsField = [["Shape_Length", "SUM"]]
    caseField = ["RIGHT_FID", "featID"]
    arcpy.Statistics_analysis(lineFeatClass3, outTab1, statsField, caseField)

    outTab2 = "outTab2"
    itemList.append(outTab2)
    statsField = [["SUM_Shape_Length", "MEAN"]]
    caseField = "featID"
    arcpy.Statistics_analysis(outTab1, outTab2, statsField, caseField)
    arcpy.AddMessage("summary statistics done")
    # add mean_width field
    field = "mean_width"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "outTab2" + "." + "MEAN_SUM_Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)
    arcpy.AddMessage("add mean_width field done")
    # convert feature vertices to points
    inFeatVertices = workspace + "/" + "inFeatVertices"
    itemList.append(inFeatVertices)
    arcpy.FeatureVerticesToPoints_management(inFeatClass, inFeatVertices, "ALL")
    arcpy.AddMessage("feature vertices to points done")

    # add x and y
    arcpy.AddXY_management(inFeatVertices)
    arcpy.AddMessage("Add x and y done")

    # export table as csv file
    csvFile1 = tempFolder + "/inFile1.csv"
    itemList.append(csvFile1)
    # delete schema.ini which may contains incorrect data types (2023-04-20)
    schemaFile = tempFolder + "/" + "schema.ini"
    if os.path.isfile(schemaFile):
        os.remove(schemaFile)
    # delete not required fields (2023-06-20)
    fieldsToKeep = ["featID", "rectangle_Orientation", "POINT_X", "POINT_Y"]
    HelperFunctions.keepSelectedFields(inFeatVertices, fieldsToKeep)
    arcpy.AddMessage("delete fields done")

    arcpy.CopyRows_management(inFeatVertices, csvFile1)
    arcpy.AddMessage("export to first csv done")
    # read the csv file as a pandas data frame, add dtype parameter (2023-06-20)
    # this is to prevent mix type warning and potentially improve efficiency in reading a large csv file
    dtypeD = {
        "OBJECTID": np.int64,
        "featID": np.int64,
        "rectangle_Orientation": np.float64,
        "POINT_X": np.float64,
        "POINT_Y": np.float64,
    }
    testDF1 = pd.read_csv(csvFile1, sep=",", header=0, dtype=dtypeD)
    testDF1.set_index("OBJECTID", inplace=True)
    headfootList = []
    ids = np.unique(testDF1.featID)
    # loop through each feature which contains a number of points
    # The idea is to find a point representing 'head' (or first)
    # and a point representing 'foot' (or last) of the feature
    for id in ids:
        x = testDF1.loc[testDF1.featID == id]
        angle = round(x.rectangle_Orientation.values[0], 2)
        arcpy.AddMessage(angle)
        if (angle >= 45) & (angle <= 135):
            y1 = x.loc[x.POINT_X == x.POINT_X.min()]
            y2 = x.loc[x.POINT_X == x.POINT_X.max()]
            for i in y1.index:
                headfootList.append(i)
            for i in y2.index:
                headfootList.append(i)
        else:
            y1 = x.loc[x.POINT_Y == x.POINT_Y.min()]
            y2 = x.loc[x.POINT_Y == x.POINT_Y.max()]
            for i in y1.index:
                headfootList.append(i)
            for i in y2.index:
                headfootList.append(i)

    # generate 'head' and 'foot' featureclass
    text = "("
    for i in headfootList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    pointFeat1 = workspace + "/" + "pointFeat1"
    itemList.append(pointFeat1)
    arcpy.Select_analysis(inFeatVertices, pointFeat1, whereClause)
    arcpy.AddMessage("selection done")

    # extract bathy values to points

    # expand inBathy
    inFocal = inBathy + "_focal"
    itemList.append(inFocal)
    outFocalStat = FocalStatistics(
        inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
    )
    outFocalStat.save(inFocal)

    inRasterList = [[inBathy, "depth"], [inFocal, "depth1"]]
    ExtractMultiValuesToPoints(pointFeat1, inRasterList, "NONE")
    arcpy.AddMessage("extract bathy values done")

    # export table as csv file
    csvFile2 = tempFolder + "/inFile2.csv"
    itemList.append(csvFile2)
    # delete schema.ini which may contains incorrect data types (2023-04-20)
    schemaFile = tempFolder + "/" + "schema.ini"
    if os.path.isfile(schemaFile):
        os.remove(schemaFile)

        
    # modified the codes as below to fix a weird error when running the tools in ArcGIS Pro Python command window (2025-08-05)
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    arcpy.Copy_management(pointFeat1, pointFeat2)
    arcpy.CopyRows_management(pointFeat2, csvFile2)
    arcpy.AddMessage("export to second csv done")
    
    # read the csv file as a pandas data frame, add dtype parameter (2023-06-20)
    dtypeD = {
        "OBJECTID": np.int64,
        "featID": np.int64,
        "rectangle_Orientation": np.float64,
        "POINT_X": np.float64,
        "POINT_Y": np.float64,
        "depth": np.float64,
        "depth1": np.float64,
    }
    testDF2 = pd.read_csv(csvFile2, sep=",", header=0, dtype=dtypeD)
    testDF2.set_index("OBJECTID", inplace=True)
    # if depth has nan, replace them with depth1
    depthList = testDF2.loc[testDF2.depth.isnull(), "depth1"]
    if depthList.size > 0:
        testDF2.loc[testDF2.depth.isnull(), "depth"] = depthList

    # get 'head' (first) and 'foot' (last) of each feature
    ids = np.unique(testDF2.featID)
    firstList = []
    lastList = []
    for id in ids:
        x = testDF2.loc[testDF2.featID == id]
        angle = round(x.rectangle_Orientation.values[0], 2)
        if (angle >= 45) & (angle <= 135):
            y1 = x.loc[x.POINT_X == x.POINT_X.min()]
            depth1 = y1.depth.max()
            y2 = x.loc[x.POINT_X == x.POINT_X.max()]
            depth2 = y2.depth.max()
            if depth1 > depth2:
                z1 = y1.loc[y1.depth == depth1]
                z2 = y2.loc[y2.depth == y2.depth.min()]

                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
            else:
                z1 = y1.loc[y1.depth == y1.depth.min()]
                z2 = y2.loc[y2.depth == depth2]

                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
        else:
            y1 = x.loc[x.POINT_Y == x.POINT_Y.min()]
            depth1 = y1.depth.max()
            y2 = x.loc[x.POINT_Y == x.POINT_Y.max()]
            depth2 = y2.depth.max()
            if depth1 > depth2:
                z1 = y1.loc[y1.depth == depth1]
                z2 = y2.loc[y2.depth == y2.depth.min()]

                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
            else:
                z1 = y1.loc[y1.depth == y1.depth.min()]
                z2 = y2.loc[y2.depth == depth2]

                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])

    # generate first points featureclass
    text = "("
    for i in firstList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    firstFeatClass = workspace + "/" + "firstPoints"
    itemList.append(firstFeatClass)
    arcpy.Select_analysis(pointFeat1, firstFeatClass, whereClause)
    # generate last points featureclass
    text = "("
    for i in lastList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    lastFeatClass = workspace + "/" + "lastPoints"
    itemList.append(lastFeatClass)
    arcpy.Select_analysis(pointFeat1, lastFeatClass, whereClause)
    arcpy.AddMessage("generate first and last points features done")

    # polygon to point
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    # Use FeatureToPoint function to find a point inside each part
    arcpy.FeatureToPoint_management(splitFeatClass, pointFeat2, "CENTROID")
    arcpy.AddMessage("feature to point done")

    # sort the points
    pointFeat2_1 = workspace + "/" + "pointFeat2_1"
    itemList.append(pointFeat2_1)
    pointFeat2_2 = workspace + "/" + "pointFeat2_2"
    itemList.append(pointFeat2_2)
    arcpy.Sort_management(pointFeat2, pointFeat2_1, [["ORIG_FID", "ASCENDING"]])
    arcpy.Sort_management(pointFeat2, pointFeat2_2, [["ORIG_FID", "DESCENDING"]])

    # add x and y
    arcpy.AddXY_management(pointFeat2_1)
    arcpy.AddXY_management(pointFeat2_2)
    arcpy.AddMessage("Add x and y done")

    # merge the first point, the centre points of each sub-polygon, then the last point
    mergedFeats = [firstFeatClass, pointFeat2_1, lastFeatClass]
    mergedFeat1_1 = workspace + "/" + "merged_points1_1"
    itemList.append(mergedFeat1_1)
    arcpy.Merge_management(mergedFeats, mergedFeat1_1)

    mergedFeats = [firstFeatClass, pointFeat2_2, lastFeatClass]
    mergedFeat1_2 = workspace + "/" + "merged_points1_2"
    itemList.append(mergedFeat1_2)
    arcpy.Merge_management(mergedFeats, mergedFeat1_2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat1_1 = "curveLine1"
    itemList.append(lineFeat1_1)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat1_1, lineFeat1_1, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat1_1):
        arcpy.AddMessage(lineFeat1_1 + " exists")
    else:
        myPointsToLine(mergedFeat1_1, lineFeat1_1, lineField, tempFolder)

    lineFeat1_2 = "curveLine2"
    itemList.append(lineFeat1_2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat1_2, lineFeat1_2, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat1_2):
        arcpy.AddMessage(lineFeat1_2 + " exists")
    else:
        myPointsToLine(mergedFeat1_2, lineFeat1_2, lineField, tempFolder)
        
    arcpy.AddMessage("points to curve line done")

    # merge curvelines
    # We do not know which curveline is the true curveline connecting the points in correct order.
    # Thus we merge the two curvelines together and select the one with shorter length, which is the correct one
    mergedFeats = [lineFeat1_1, lineFeat1_2]
    mergedCurveFeat = workspace + "/" + "merged_curves"
    itemList.append(mergedCurveFeat)
    arcpy.Merge_management(mergedFeats, mergedCurveFeat)
    arcpy.AddMessage("merged curves done")

    # summary statistics
    # in order to select the shorter curveline
    outTab3 = "outTab3"
    itemList.append(outTab3)
    statsField = [["Shape_Length", "MIN"]]
    caseField = ["featID"]
    arcpy.Statistics_analysis(mergedCurveFeat, outTab3, statsField, caseField)

    # merge to create a straight line connecting the first
    # and last point in order to calculate the straight length (head to foot length)
    mergedFeats = [firstFeatClass, lastFeatClass]
    mergedFeat2 = workspace + "/" + "merged_points2"
    itemList.append(mergedFeat2)
    arcpy.Merge_management(mergedFeats, mergedFeat2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat2 = "straightLine"
    itemList.append(lineFeat2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat2, lineFeat2, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat2):
        arcpy.AddMessage(lineFeat2 + " exists")
    else:
        myPointsToLine(mergedFeat2, lineFeat2, lineField, tempFolder)
            
    arcpy.AddMessage("points to straight line done")

    # add sinuous_length field
    field = "sinuous_length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "outTab3" + "." + "MIN_Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, outTab3, field, inID, joinID, expression)
    arcpy.AddMessage("add sinuous_length field done")
    # add head_foot_length field
    field = "head_foot_length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "straightLine" + "." + "Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, lineFeat2, field, inID, joinID, expression)
    arcpy.AddMessage("add heat_foot_length field done")
    field = "Sinuosity"
    expression = "!sinuous_length! / !head_foot_length!"
    arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate Sinuosity field done")
    field = "LengthWidthRatio"
    expression = "!sinuous_length! / !mean_width!"
    arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate LengthWidthRatio field done")
    HelperFunctions.deleteDataItems(itemList)
    arcpy.AddMessage("data deletion done")
    time2 = datetime.now()
    diff = time2 - time1
    arcpy.AddMessage("took " + str(diff) + " to have all attributes generated.")


# This function calculates mean_segment_slope attribute.
# mean_segment_slope: A number of linear segments are created by connecting the head,
# each point of minimum depth on a profile, and the foot.
# The slopes of the segments are calculated and averaged as this mean_segment_slope value.
def calculate_segmentSlope(
    inFeat, inTab, dissolveLineFeat, headFeat, footFeat, outFeat
):
    # inFeat: input point featureclass represents points along the cross-feature profiles,
    # each point must have a depth value
    # inTab: input table that has some statistical values calculated from inFeat
    # dissolveLineFeat: the name of the line featureclass resulted from dissolving the inLineFeat
    # headFeat: input head feature
    # footFeat: input foot feature
    # outFeat: output point featureclass represents the start and end points of line segments

    itemList = []
    # for each profile, select a point with the minimum depth
    # the outFeat is the output also used in the Near_analysis function that follow this function
    field = "min_depth"
    inID = "RIGHT_FID"
    joinID = "RIGHT_FID"
    expression = "!" + inTab + "." + "MIN_RASTERVALU" + "!"
    HelperFunctions.addField(inFeat, inTab, field, inID, joinID, expression)
    outFeat2 = "inFeat_selected"
    itemList.append(outFeat2)
    whereClause = '"RASTERVALU" = "min_depth"'
    arcpy.Select_analysis(inFeat, outFeat2, whereClause)
    arcpy.Copy_management(outFeat2, outFeat)
    # count the number of profiles
    noLines = int(arcpy.GetCount_management(dissolveLineFeat).getOutput(0))

    if noLines < 2:  # only one profile
        # get head depth
        cursor = arcpy.SearchCursor(headFeat)
        row = cursor.next()
        headX = row.getValue("POINT_X")
        headY = row.getValue("POINT_Y")
        headDepth = row.getValue("depth1")
        del row, cursor
        # get foot depth
        cursor = arcpy.SearchCursor(footFeat)
        row = cursor.next()
        footX = row.getValue("POINT_X")
        footY = row.getValue("POINT_Y")
        footDepth = row.getValue("depth1")
        del row, cursor
        # calculate distance between head and foot
        distance = calculateDistance(headX, headY, footX, footY)
        # calculate slope between head and foot as the mean_segment_slope
        meanSlope = abs(calculateSlope(footDepth, headDepth, distance))
    else:
        # each feature in outFeat2 represents one or multiple points that have the minimum depth along a profile
        # multiple points along a profile may have the same depth value as the minimum depth
        # in this case, only one point is selected by compiling an ids_tobeDeleted list
        # add and calculate field
        # sort
        outFeat3 = "outFeat2_sorted"
        itemList.append(outFeat3)
        sortField = [["RIGHT_FID", "Descending"]]
        arcpy.Sort_management(outFeat2, outFeat3, sortField)
        # get a list of ids and fids
        cursor = arcpy.SearchCursor(outFeat3)
        idList = []
        fidList = []
        for row in cursor:
            idV = row.getValue("OBJECTID")
            fidV = row.getValue("RIGHT_FID")
            idList.append(idV)
            fidList.append(fidV)
        del cursor, row
        ids_tobeDeleted = []
        i = 0
        while i < len(idList):
            fidV = fidList[i]
            if i == len(idList) - 1:
                break
            else:
                idV1 = idList[i + 1]
                fidV1 = fidList[i + 1]
                if fidV == fidV1:
                    ids_tobeDeleted.append(idV1)
            i += 1

        if len(ids_tobeDeleted) > 0:
            outFeat4 = "outFeat3_selected"
            itemList.append(outFeat4)
            text = "("
            for i in ids_tobeDeleted:
                text = text + str(i) + ","
            text = text[0:-1] + ")"
            whereClause = "OBJECTID NOT IN " + text
            arcpy.Select_analysis(outFeat3, outFeat4, whereClause)
            arcpy.Copy_management(outFeat4, outFeat)
        else:
            arcpy.Copy_management(outFeat3, outFeat)
        # startX and startY represent the XY of the start point of the line segment
        # endX and endY represent the XY of the end point the line segment
        # note that the end point of the first segment is the start point of the second segment, and so on
        arcpy.AddXY_management(outFeat)
        cursor = arcpy.SearchCursor(outFeat)
        startXList = []
        startYList = []
        endXList = []
        endYList = []
        startDepthList = []
        endDepthList = []
        for row in cursor:
            x = row.getValue("POINT_X")
            y = row.getValue("POINT_Y")
            depth = row.getValue("min_depth")
            startXList.append(x)
            startYList.append(y)
            startDepthList.append(depth)

        del cursor, row
        cursor = arcpy.SearchCursor(outFeat)
        row = cursor.next()
        row = cursor.next()
        while row:
            x = row.getValue("POINT_X")
            y = row.getValue("POINT_Y")
            depth = row.getValue("min_depth")
            endXList.append(x)
            endYList.append(y)
            endDepthList.append(depth)
            row = cursor.next()

        del cursor, row
        # calculate each segment slope using the XY coordinates of the start and end points
        slopeList = []
        i = 0
        while i < len(endXList):
            startX = startXList[i]
            startY = startYList[i]
            endX = endXList[i]
            endY = endYList[i]
            distance = calculateDistance(startX, startY, endX, endY)
            slope = abs(
                calculateSlope(endDepthList[i], startDepthList[i], distance)
            )
            slopeList.append(slope)
            i += 1
        # calculate mean segment slope
        meanSlope = np.nanmean(np.asarray(slopeList))
    HelperFunctions.deleteDataItems(itemList)
    return meanSlope


# This function calculates 8 additional attributes: mean_width_thickness_ratio, std_width_thickness_ratio,
# mean_thickness, mean_segment_slope, width_distance_slope, width_distance_correlation, thick_distance_slope,
# and thick_distance_correlation. These attributes are used to classify Gully, Valley and Channel, and Canyon features.
# mean_thickness: the mean feature thickness (top depth minus bottom depth) of a number of cross-feature profiles
# mean_width_thickness_ratio: mean ratio between the width and the thickness of a number of profiles
# std_width_thickness_ratio: standard deviation of the ratios between the width
# and the thickness of a number of profiles
# mean_segment_slope: A number of linear segments are created by connecting the head,
# each point of minimum depth on a profile, and the foot.
# The slopes of the segments are calculated and averaged as this value.
# width_distance_slope: The slope of the linear fitting line between the widths of the sub-polygons
# and the distances of the sub-polygons to the feature head
# width_distance_correlation: The correlation coefficient between the widths of the sub-polygons
# and the distances of the sub-polygons to the feature head
# thick_distance_slope: The slope of the linear fitting line between the thicknesses of the sub-polygons
# and the distances of the sub-polygons to the feature head
# thick_distance_correlation: The correlation coefficient between the thicknesses of the sub-polygons
# and the distances of the sub-polygons to the feature head
def calculate_Ratio_Slopes(
    inLineFeat, inBathy, dissolveLineFeat, headFeat, footFeat
):
    # inLineFeat: input line featureclass represents cross-feature profiles
    # inBathy: input bathymetry grid (must be extended several cells from the original bathymetry grid)
    # dissolveLineFeat: the name of the line featureclass resulted from dissolving the inLineFeat
    # headFeat: input head feature
    # footFeat: input foot feature

    itemList = []
    itemList.append(inLineFeat)
    itemList.append(dissolveLineFeat)
    itemList.append(headFeat)
    itemList.append(footFeat)
    # The input inLineFeat effectively contains cross-feature profiles

    # dissolve line features
    dissolvedField = "RIGHT_FID"
    arcpy.Dissolve_management(inLineFeat, dissolveLineFeat, dissolvedField)

    # convert line to vertices, effectively identify the start and end points of the profiles
    outVerticeFeat1 = "dissolveLineFeat_vertices1"
    itemList.append(outVerticeFeat1)
    arcpy.FeatureVerticesToPoints_management(
        dissolveLineFeat, outVerticeFeat1, "All"
    )

    # extract depth values
    depthFeat1 = "outVerticeFeat_depths1"
    itemList.append(depthFeat1)
    ExtractValuesToPoints(outVerticeFeat1, inBathy, depthFeat1)

    # summary statistics
    # This calculates the minimum depth of the start and end points of the profile,
    # which represents the surface depth of the feature
    outTab1 = "outFeat_min1"
    itemList.append(outTab1)
    statField = [["RASTERVALU", "MIN"]]
    caseField = "RIGHT_FID"
    arcpy.Statistics_analysis(depthFeat1, outTab1, statField, caseField)

    # densify line features so that we have more points along the profile
    distance = "10 Meters"
    arcpy.Densify_edit(dissolveLineFeat, "DISTANCE", distance)

    # convert line to vertices
    outVerticeFeat2 = "dissolveLineFeat_vertices2"
    itemList.append(outVerticeFeat2)
    arcpy.FeatureVerticesToPoints_management(
        dissolveLineFeat, outVerticeFeat2, "All"
    )

    # extract depth values
    depthFeat2 = "outVerticeFeat_depths2"
    itemList.append(depthFeat2)
    ExtractValuesToPoints(outVerticeFeat2, inBathy, depthFeat2)

    # summary statistics
    # This calculates the minimum depth of the profile which represents the bottom depth of the feature
    outTab2 = "outFeat_min2"
    itemList.append(outTab2)
    statField = [["RASTERVALU", "MIN"]]
    caseField = "RIGHT_FID"
    arcpy.Statistics_analysis(depthFeat2, outTab2, statField, caseField)

    # call the helper function to calculate mean_segment_Slope
    outFeat1 = "outFeat_selected_final"
    itemList.append(outFeat1)
    meanSlope = calculate_segmentSlope(
        depthFeat2, outTab2, dissolveLineFeat, headFeat, footFeat, outFeat1
    )

    # calculate distance of the minimum depth point of each profile to the feature head
    arcpy.Near_analysis(outFeat1, headFeat)

    # add and calculate fields
    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6
    fields = arcpy.ListFields(dissolveLineFeat)
    field_names = [f.name for f in fields]

    fieldList = [
        "surface_depth",
        "min_depth",
        "thickness",
        "widthThicknessRatio",
        "distance",
    ]

    for fieldName in fieldList:
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(
                dissolveLineFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )

    field = "surface_depth"
    inID = "RIGHT_FID"
    joinID = "RIGHT_FID"
    expression = "!" + outTab1 + "." + "MIN_RASTERVALU" + "!"
    HelperFunctions.addField(dissolveLineFeat, outTab1, field, inID, joinID, expression)

    field = "min_depth"
    inID = "RIGHT_FID"
    joinID = "RIGHT_FID"
    expression = "!" + outTab2 + "." + "MIN_RASTERVALU" + "!"
    HelperFunctions.addField(dissolveLineFeat, outTab2, field, inID, joinID, expression)

    field = "distance"
    inID = "RIGHT_FID"
    joinID = "RIGHT_FID"
    expression = "!" + outFeat1 + "." + "NEAR_DIST" + "!"
    HelperFunctions.addField(dissolveLineFeat, outFeat1, field, inID, joinID, expression)

    # feature thickness equals surface depth minus bottom depth
    field = "thickness"
    expression = "!surface_depth! - !min_depth!"
    arcpy.CalculateField_management(
        dissolveLineFeat, field, expression, "PYTHON3"
    )

    field = "widthThicknessRatio"
    # need to handle in rare case of thickness = 0; added on 20240604
    codeblock = """
import numpy as np
def divisionZero(a, b):
    if b == 0:
        return np.nan
    else:
        return a / b
            """
    expression = "divisionZero(!Shape_Length!, !thickness!)"
    arcpy.CalculateField_management(
        dissolveLineFeat, field, expression, "PYTHON3", codeblock
    )

    ratioList = []
    widthList = []
    distList = []
    thickList = []
    cursor = arcpy.SearchCursor(dissolveLineFeat)
    # loop through each profile
    for row in cursor:
        ratio = row.getValue("widthThicknessRatio")
        if ratio is None:  # caused by thickness = 0
            ratioList.append(np.nan)
        else:
            ratioList.append(ratio)
        thickness = row.getValue("thickness")
        thickList.append(thickness)
        width = row.getValue("Shape_Length")
        widthList.append(width)
        dist = row.getValue("distance")
        distList.append(dist)
    del row, cursor
    arcpy.AddMessage("ratioList:" + str(ratioList))
    # obtain the number of profiles
    nuLines = int(arcpy.GetCount_management(dissolveLineFeat).getOutput(0))
    # obtain the number of non-nan value(s) in the ratioList. nan in ratioList is caused by thickness = 0
    nu_notNan = np.asarray(ratioList).size - np.isnan(np.asarray(ratioList)).sum()

    if nuLines < 2:  # only one profile, set to default values
        stdRatio = -999
        widthDistSlope = -999
        widthDistCor = -999
        thickDistSlope = -999
        thickDistCor = -999
        if nu_notNan < 1:  # all ratio values are nan
            meanRatio = -999
        else:
            meanRatio = np.nanmean(np.asarray(ratioList))
    else:
        # calculate linear regression slopes and correlation coefficients
        widthArr = np.asarray(widthList)
        thickArr = np.asarray(thickList)
        distArr = np.asarray(distList)

        arcpy.AddMessage("widthList:" + str(widthArr))
        arcpy.AddMessage("thickList:" + str(thickArr))
        arcpy.AddMessage("distList:" + str(distArr))

        if (
            np.unique(widthArr).size == 1
        ):  # if all elements in widthList have the same value, the slope and correlation values are not meaningful
            widthDistSlope = -999
            widthDistCor = -999
        else:
            widthDistSlope, widthDistIntercept = np.polyfit(distArr, widthArr, 1)
            widthDistCor = np.corrcoef(distArr, widthArr)[0, 1]

        if nu_notNan < 1:
            meanRatio = -999
            stdRatio = -999
            thickDistSlope = -999
            thickDistCor = -999
        elif nu_notNan < 2:
            meanRatio = np.nanmean(np.asarray(ratioList))
            stdRatio = -999
            thickDistSlope = -999
            thickDistCor = -999
        else:
            stdRatio = np.nanstd(np.asarray(ratioList))
            meanRatio = np.nanmean(np.asarray(ratioList))

            if (
                np.unique(thickArr).size == 1
            ):  # if all elements in thickList have the same value
                thickDistSlope = -999
                thickDistCor = -999
            else:
                thickDistSlope, thickDistIntercept = np.polyfit(
                    distArr, abs(thickArr), 1
                )
                thickDistCor = np.corrcoef(distArr, abs(thickArr))[0, 1]

    meanThick = np.nanmean(np.asarray(thickList))

    HelperFunctions.deleteDataItems(itemList)
    return (
        meanRatio,
        stdRatio,
        meanThick,
        meanSlope,
        widthDistSlope,
        widthDistCor,
        thickDistSlope,
        thickDistCor,
    )


# This function calculates the mean segment slope attribute. This attribute is used to
# classify Gully, Valley and Channel, and Canyon features.
# mean_segment_slope: A number of linear segments are created by connecting the head,
# each point of minimum depth on a profile, and the foot.
# The slopes of the segments are calculated and averaged as this value.
def calculate_meansegment_Slopes(
    inLineFeat, inBathy, dissolveLineFeat, headFeat, footFeat
):
    # inLineFeat: input line featureclass represents cross-feature profiles
    # inBathy: input bathymetry grid (must be extended several cells from the original bathymetry grid)
    # dissolveLineFeat: the name of the line featureclass resulted from dissolving the inLineFeat
    # headFeat: input head feature
    # footFeat: input foot feature

    itemList = []
    itemList.append(inLineFeat)
    itemList.append(dissolveLineFeat)
    itemList.append(headFeat)
    itemList.append(footFeat)
    # The input inLineFeat effectively contains cross-feature profiles

    # dissolve line features
    dissolvedField = "RIGHT_FID"
    arcpy.Dissolve_management(inLineFeat, dissolveLineFeat, dissolvedField)

    # convert line to vertices, effectively identify the start and end points of the profiles
    outVerticeFeat1 = "dissolveLineFeat_vertices1"
    itemList.append(outVerticeFeat1)
    arcpy.FeatureVerticesToPoints_management(
        dissolveLineFeat, outVerticeFeat1, "All"
    )

    # extract depth values
    depthFeat1 = "outVerticeFeat_depths1"
    itemList.append(depthFeat1)
    ExtractValuesToPoints(outVerticeFeat1, inBathy, depthFeat1)

    # summary statistics
    # This calculates the minimum depth of the start and end points of the profile,
    # which represents the surface depth of the feature
    outTab1 = "outFeat_min1"
    itemList.append(outTab1)
    statField = [["RASTERVALU", "MIN"]]
    caseField = "RIGHT_FID"
    arcpy.Statistics_analysis(depthFeat1, outTab1, statField, caseField)

    # densify line features so that we have more points along the profile
    distance = "10 Meters"
    arcpy.Densify_edit(dissolveLineFeat, "DISTANCE", distance)

    # convert line to vertices
    outVerticeFeat2 = "dissolveLineFeat_vertices2"
    itemList.append(outVerticeFeat2)
    arcpy.FeatureVerticesToPoints_management(
        dissolveLineFeat, outVerticeFeat2, "All"
    )

    # extract depth values
    depthFeat2 = "outVerticeFeat_depths2"
    itemList.append(depthFeat2)
    ExtractValuesToPoints(outVerticeFeat2, inBathy, depthFeat2)

    # summary statistics
    # This calculates the minimum depth of the profile which represents the bottom depth of the feature
    outTab2 = "outFeat_min2"
    itemList.append(outTab2)
    statField = [["RASTERVALU", "MIN"]]
    caseField = "RIGHT_FID"
    arcpy.Statistics_analysis(depthFeat2, outTab2, statField, caseField)

    # call the helper function to calculate mean_segment_Slope
    outFeat1 = "outFeat_selected_final"
    itemList.append(outFeat1)
    meanSlope = calculate_segmentSlope(
        depthFeat2, outTab2, dissolveLineFeat, headFeat, footFeat, outFeat1
    )

    HelperFunctions.deleteDataItems(itemList)
    return meanSlope


# This function calculates sinuosity, length to width ratio, width to depth (thickness) ratio,
# and a number of other attributes for the Bathymetric Low features
def calculateSinuosity_LwR_WdR_Slopes(
    workspace,
    tempFolder,
    inFeatClass,
    inBathy,
    headFeatClass,
    footFeatClass,
    additionalOption,
):
    # workspace: the location of the workspace
    # tempFolder: the location of the temporary folder
    # inFeatClass: input Bathymetry High (Low) features
    # inBathy: input bathymetry grid
    # headFeatClass: input head featureclass
    # footFeatClass: input foot featureclass
    # additionalOption: option of whether to calculate 7 additional attributes

    env.workspace = workspace
    time1 = datetime.now()
    itemList = []
    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    # generate bounding rectangle
    MbrFeatClass = "bounding_rectangle"
    itemList.append(MbrFeatClass)
    arcpy.MinimumBoundingGeometry_management(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    # add MBG_LENGTH, MBG_WIDTH AND MBG_ORIENTATION to inFeatClass
    field = "rectangle_Length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + MbrFeatClass + "." + "MBG_Length" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    field = "rectangle_Width"
    expression = "!" + MbrFeatClass + "." + "MBG_Width" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    field = "rectangle_Orientation"
    expression = "!" + MbrFeatClass + "." + "MBG_Orientation" + "!"
    HelperFunctions.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
    arcpy.AddMessage("three bounding rectangle fields added")

    # the list of attributes to be calculated and added
    if additionalOption == "true":
        arcpy.AddMessage("Will calculate additional attributes")
        fieldList = [
            "head_foot_length",
            "sinuous_length",
            "Sinuosity",
            "mean_width",
            "LengthWidthRatio",
            "mean_width_thickness_ratio",
            "std_width_thickness_ratio",
            "mean_thickness",
            "mean_segment_slope",
            "width_distance_slope",
            "width_distance_correlation",
            "thick_distance_slope",
            "thick_distance_correlation",
        ]
    else:
        arcpy.AddMessage("Won't calculate additional attributes")
        fieldList = [
            "head_foot_length",
            "sinuous_length",
            "Sinuosity",
            "mean_width",
            "LengthWidthRatio",
            "mean_segment_slope",
        ]

    for fieldName in fieldList:
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(
                inFeatClass, fieldName, fieldType, fieldPrecision, fieldScale
            )
    # call the helper function to split each polygon in the inFeatClass into multiple sub-polygons
    splitFeatClass = workspace + "/" + "inFeatClass_splitted"
    itemList.append(splitFeatClass)
    splitPolygon(workspace, inFeatClass, MbrFeatClass, splitFeatClass)
    arcpy.AddMessage("inFeatClass splitted")
    # convert polygon to line
    lineFeatClass1 = workspace + "/" + "lineFeatClass1"
    itemList.append(lineFeatClass1)
    arcpy.PolygonToLine_management(splitFeatClass, lineFeatClass1)
    arcpy.AddMessage("polygon to line done")
    # selection
    lineFeatClass2 = workspace + "/" + "lineFeatClass2"
    itemList.append(lineFeatClass2)
    whereClause = "LEFT_FID <> -1"
    arcpy.Select_analysis(lineFeatClass1, lineFeatClass2, whereClause)
    arcpy.AddMessage("selection done")
    # spatial join
    lineFeatClass3 = workspace + "/" + "lineFeatClass3"
    itemList.append(lineFeatClass3)
    arcpy.SpatialJoin_analysis(
        lineFeatClass2,
        inFeatClass,
        lineFeatClass3,
        "JOIN_ONE_TO_ONE",
        "KEEP_ALL",
        "#",
        "WITHIN",
    )
    arcpy.AddMessage("spatial join done")
    # summary statistics
    outTab1 = "outTab1"
    itemList.append(outTab1)
    statsField = [["Shape_Length", "SUM"]]
    caseField = ["RIGHT_FID", "featID"]
    arcpy.Statistics_analysis(lineFeatClass3, outTab1, statsField, caseField)

    outTab2 = "outTab2"
    itemList.append(outTab2)
    statsField = [["SUM_Shape_Length", "MEAN"]]
    caseField = "featID"
    arcpy.Statistics_analysis(outTab1, outTab2, statsField, caseField)
    arcpy.AddMessage("summary statistics done")
    # add mean_width field
    field = "mean_width"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "outTab2" + "." + "MEAN_SUM_Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)
    arcpy.AddMessage("add mean_width field done")
    # convert feature vertices to points
    inFeatVertices = workspace + "/" + "inFeatVertices"
    itemList.append(inFeatVertices)
    arcpy.FeatureVerticesToPoints_management(inFeatClass, inFeatVertices, "ALL")
    arcpy.AddMessage("feature vertices to points done")

    # add x and y
    arcpy.AddXY_management(inFeatVertices)
    arcpy.AddMessage("Add x and y done")

    # export table as csv file
    csvFile1 = tempFolder + "/inFile1.csv"
    itemList.append(csvFile1)
    # delete schema.ini which may contains incorrect data types (2023-04-20)
    schemaFile = tempFolder + "/" + "schema.ini"
    if os.path.isfile(schemaFile):
        os.remove(schemaFile)

    # delete not required fields (2023-06-20)
    fieldsToKeep = ["featID", "rectangle_Orientation", "POINT_X", "POINT_Y"]
    HelperFunctions.keepSelectedFields(inFeatVertices, fieldsToKeep)
    arcpy.AddMessage("delete fields done")

    arcpy.CopyRows_management(inFeatVertices, csvFile1)
    arcpy.AddMessage("export to first csv done")
    # read the csv file as a pandas data frame, add dtype parameter (2023-06-20)
    dtypeD = {
        "OBJECTID": np.int64,
        "featID": np.int64,
        "rectangle_Orientation": np.float64,
        "POINT_X": np.float64,
        "POINT_Y": np.float64,
    }
    testDF1 = pd.read_csv(csvFile1, sep=",", header=0, dtype=dtypeD)
    testDF1.set_index("OBJECTID", inplace=True)
    headfootList = []
    ids = np.unique(testDF1.featID)
    # loop through each feature which contains a number of points
    # The idea is to find a point representing 'head' (first)
    # and a point representing 'foot' (last) of the Bathymetric Low feature
    for id in ids:
        x = testDF1.loc[testDF1.featID == id]
        angle = round(x.rectangle_Orientation.values[0], 2)
        arcpy.AddMessage(angle)
        if (angle >= 45) & (angle <= 135):
            y1 = x.loc[x.POINT_X == x.POINT_X.min()]
            y2 = x.loc[x.POINT_X == x.POINT_X.max()]
            for i in y1.index:
                headfootList.append(i)
            for i in y2.index:
                headfootList.append(i)
        else:
            y1 = x.loc[x.POINT_Y == x.POINT_Y.min()]
            y2 = x.loc[x.POINT_Y == x.POINT_Y.max()]
            for i in y1.index:
                headfootList.append(i)
            for i in y2.index:
                headfootList.append(i)

    # generate head and foot featureclass
    text = "("
    for i in headfootList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    pointFeat1 = workspace + "/" + "pointFeat1"
    itemList.append(pointFeat1)
    arcpy.Select_analysis(inFeatVertices, pointFeat1, whereClause)
    arcpy.AddMessage("selection done")

    # extract bathy values to points
    # expand inBathy
    inFocal = inBathy + "_focal"
    itemList.append(inFocal)
    outFocalStat = FocalStatistics(
        inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
    )
    outFocalStat.save(inFocal)

    # mosaic to new raster
    mosaicBathy = "mosaicBathy"
    itemList.append(mosaicBathy)
    inputRasters = [inBathy, inFocal]
    arcpy.MosaicToNewRaster_management(
        inputRasters,
        workspace,
        mosaicBathy,
        inBathy,
        "32_BIT_FLOAT",
        "#",
        "1",
        "FIRST",
        "FIRST",
    )
    arcpy.AddMessage("mosaic done")
    mosaicBathy = workspace + "/" + "mosaicBathy"

    inRasterList = [[inBathy, "depth"], [inFocal, "depth1"]]
    ExtractMultiValuesToPoints(pointFeat1, inRasterList, "NONE")
    arcpy.AddMessage("extract bathy values done")
    # export table as csv file
    csvFile2 = tempFolder + "/inFile2.csv"
    itemList.append(csvFile2)
    # delete schema.ini which may contains incorrect data types (2023-04-20)
    schemaFile = tempFolder + "/" + "schema.ini"
    if os.path.isfile(schemaFile):
        os.remove(schemaFile)

    # modified the codes as below to fix a weird error when running the tools in ArcGIS Pro Python command window (2025-08-05)
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    arcpy.Copy_management(pointFeat1, pointFeat2)
    arcpy.CopyRows_management(pointFeat2, csvFile2)
    arcpy.AddMessage("export to second csv done")
        
    # read the csv file as a pandas data frame, add dtype parameter (2023-06-20)
    dtypeD = {
        "OBJECTID": np.int64,
        "featID": np.int64,
        "rectangle_Orientation": np.float64,
        "POINT_X": np.float64,
        "POINT_Y": np.float64,
        "depth": np.float64,
        "depth1": np.float64,
    }
    testDF2 = pd.read_csv(csvFile2, sep=",", header=0, dtype=dtypeD)
    testDF2.set_index("OBJECTID", inplace=True)
    # if depth has nan, replace them with depth1
    depthList = testDF2.loc[testDF2.depth.isnull(), "depth1"]
    if depthList.size > 0:
        testDF2.loc[testDF2.depth.isnull(), "depth"] = depthList
    # get head and foot of each feature
    ids = np.unique(testDF2.featID)
    headList = []
    footList = []
    firstList = []
    lastList = []
    for id in ids:
        x = testDF2.loc[testDF2.featID == id]
        angle = round(x.rectangle_Orientation.values[0], 2)
        if (angle >= 45) & (angle <= 135):
            y1 = x.loc[x.POINT_X == x.POINT_X.min()]
            depth1 = y1.depth.max()
            y2 = x.loc[x.POINT_X == x.POINT_X.max()]
            depth2 = y2.depth.max()
            if depth1 > depth2:
                z1 = y1.loc[y1.depth == depth1]
                z2 = y2.loc[y2.depth == y2.depth.min()]
                headList.append(z1.index.values[0])
                footList.append(z2.index.values[0])
                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
            else:
                z1 = y1.loc[y1.depth == y1.depth.min()]
                z2 = y2.loc[y2.depth == depth2]
                footList.append(z1.index.values[0])
                headList.append(z2.index.values[0])
                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
        else:
            y1 = x.loc[x.POINT_Y == x.POINT_Y.min()]
            depth1 = y1.depth.max()
            y2 = x.loc[x.POINT_Y == x.POINT_Y.max()]
            depth2 = y2.depth.max()
            if depth1 > depth2:
                z1 = y1.loc[y1.depth == depth1]
                z2 = y2.loc[y2.depth == y2.depth.min()]
                headList.append(z1.index.values[0])
                footList.append(z2.index.values[0])
                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
            else:
                z1 = y1.loc[y1.depth == y1.depth.min()]
                z2 = y2.loc[y2.depth == depth2]
                footList.append(z1.index.values[0])
                headList.append(z2.index.values[0])
                firstList.append(z1.index.values[0])
                lastList.append(z2.index.values[0])
    # generate head featureclass
    text = "("
    for i in headList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    arcpy.Select_analysis(pointFeat1, headFeatClass, whereClause)
    # generate foot featureclass
    text = "("
    for i in footList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    arcpy.Select_analysis(pointFeat1, footFeatClass, whereClause)
    arcpy.AddMessage("generate head and foot features done")

    # generate first points featureclass
    text = "("
    for i in firstList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    firstFeatClass = workspace + "/" + "firstPoints"
    itemList.append(firstFeatClass)
    arcpy.Select_analysis(pointFeat1, firstFeatClass, whereClause)
    # generate last points featureclass
    text = "("
    for i in lastList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    lastFeatClass = workspace + "/" + "lastPoints"
    itemList.append(lastFeatClass)
    arcpy.Select_analysis(pointFeat1, lastFeatClass, whereClause)
    arcpy.AddMessage("generate first and last points features done")

    # polygon to point
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    # Use FeatureToPoint function to find a point inside each part
    arcpy.FeatureToPoint_management(splitFeatClass, pointFeat2, "CENTROID")
    arcpy.AddMessage("feature to point done")

    # sort the points
    pointFeat2_1 = workspace + "/" + "pointFeat2_1"
    itemList.append(pointFeat2_1)
    pointFeat2_2 = workspace + "/" + "pointFeat2_2"
    itemList.append(pointFeat2_2)
    arcpy.Sort_management(pointFeat2, pointFeat2_1, [["ORIG_FID", "ASCENDING"]])
    arcpy.Sort_management(pointFeat2, pointFeat2_2, [["ORIG_FID", "DESCENDING"]])

    # add x and y
    arcpy.AddXY_management(pointFeat2_1)
    arcpy.AddXY_management(pointFeat2_2)
    print("Add x and y done")

    # merge the first point, the centre points of each sub-polygon, then the last point
    mergedFeats = [firstFeatClass, pointFeat2_1, lastFeatClass]
    mergedFeat1_1 = workspace + "/" + "merged_points1_1"
    itemList.append(mergedFeat1_1)
    arcpy.Merge_management(mergedFeats, mergedFeat1_1)

    mergedFeats = [firstFeatClass, pointFeat2_2, lastFeatClass]
    mergedFeat1_2 = workspace + "/" + "merged_points1_2"
    itemList.append(mergedFeat1_2)
    arcpy.Merge_management(mergedFeats, mergedFeat1_2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat1_1 = "curveLine1"
    itemList.append(lineFeat1_1)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat1_1, lineFeat1_1, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat1_1):
        arcpy.AddMessage(lineFeat1_1 + " exists")
    else:
        myPointsToLine(mergedFeat1_1, lineFeat1_1, lineField, tempFolder)

    lineFeat1_2 = "curveLine2"
    itemList.append(lineFeat1_2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat1_2, lineFeat1_2, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat1_2):
        arcpy.AddMessage(lineFeat1_2 + " exists")
    else:
        myPointsToLine(mergedFeat1_2, lineFeat1_2, lineField, tempFolder)
        
    arcpy.AddMessage("points to curve line done")

    # merge curvelines
    # We do not know which curveline is the true curveline connecting the points in correct order.
    # Thus we merge the two curvelines together and select the one with shorter length, which is the correct one
    mergedFeats = [lineFeat1_1, lineFeat1_2]
    mergedCurveFeat = workspace + "/" + "merged_curves"
    itemList.append(mergedCurveFeat)
    arcpy.Merge_management(mergedFeats, mergedCurveFeat)
    arcpy.AddMessage("merged curves done")

    # summary statistics
    # in order to select the shorter curveline
    outTab3 = "outTab3"
    itemList.append(outTab3)
    statsField = [["Shape_Length", "MIN"]]
    caseField = ["featID"]
    arcpy.Statistics_analysis(mergedCurveFeat, outTab3, statsField, caseField)

    # merge to create a straight line connecting the first
    # and last point in order to calculate the straight length (head to foot length)
    mergedFeats = [firstFeatClass, lastFeatClass]
    mergedFeat2 = workspace + "/" + "merged_points2"
    itemList.append(mergedFeat2)
    arcpy.Merge_management(mergedFeats, mergedFeat2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat2 = "straightLine"
    itemList.append(lineFeat2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.PointsToLine_management(mergedFeat2, lineFeat2, lineField, sortField)
    # If the above function fails silently, call my own replicated function
    if arcpy.Exists(lineFeat2):
        arcpy.AddMessage(lineFeat2 + " exists")
    else:
        myPointsToLine(mergedFeat2, lineFeat2, lineField, tempFolder)
        
    arcpy.AddMessage("points to straight line done")

    # add sinuous_length field
    field = "sinuous_length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "outTab3" + "." + "MIN_Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, outTab3, field, inID, joinID, expression)
    arcpy.AddMessage("add sinuous_length field done")
    # calculate and add head_foot_length, sinuosity and LengthWidthRatio fields
    field = "head_foot_length"
    inID = "featID"
    joinID = "featID"
    expression = "!" + "straightLine" + "." + "Shape_Length" + "!"
    HelperFunctions.addField(inFeatClass, lineFeat2, field, inID, joinID, expression)
    arcpy.AddMessage("add heat_foot_length field done")
    field = "Sinuosity"
    expression = "!sinuous_length! / !head_foot_length!"
    arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate Sinuosity field done")
    field = "LengthWidthRatio"
    expression = "!sinuous_length! / !mean_width!"
    arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate LengthWidthRatio field done")

    # calculate mean widthThicknessRatio,mean segment slope and other slope parameters
    arcpy.AddMessage(
        "calculating mean widthThicknessRatio, mean segment slope and other slope parameters"
    )
    # using update cursor because we are going to assign new values to these attributes for each feature
    cursor = arcpy.UpdateCursor(inFeatClass)
    # loop through each feature
    i = 1
    for row in cursor:
        # only do this every 100 iterations
        if i % 100 == 1:
            arcpy.Compact_management(
                workspace
            )  # compact the geodatabase to reduce its size and potentially improve the performance
            arcpy.AddMessage("Compacted the geodatabase")
        featID = row.getValue("featID")
        lwRatio = float(row.getValue("LengthWidthRatio"))
        arcpy.AddMessage("lwRatio: " + str(lwRatio))

        if additionalOption == "true":  # calculate all 8 attributes
            # These 8 attributes: mean_width_thickness_ratio, std_width_thickness_ratio, mean_thickness,
            # mean_segment_slope, width_distance_slope, width_distance_correlation, thick_distance_slope,
            # and thick_distance_correlation are used to classify Gully, Valley and Channel features.
            # These three types of features are elongated features with large LengthWidthRatio.
            if (
                lwRatio < 5
            ):  # skipping the non-elongated features and assigning them default values.
                # This saves a lot of time calculating these attributes.
                arcpy.AddMessage("skipping " + str(featID))
                meanRatio = -999
                stdRatio = -999
                meanThick = -999
                meanSlope = -999
                widthDistSlope = -999
                widthDistCor = -999
                thickDistSlope = -999
                thickDistCor = -999
            else:  # only calculate these 8 attributes for elongated features
                arcpy.AddMessage("working on " + str(featID))
                time1 = datetime.now()
                lineFeatClass4 = workspace + "/" + "lineFeatClass4"
                whereClause = "featID = " + str(featID)
                arcpy.Select_analysis(lineFeatClass3, lineFeatClass4, whereClause)
                dissolveLineFeat = workspace + "/" + "lineFeatClass4_dissolved"

                headFeat1 = workspace + "/" + "headFeat1"
                footFeat1 = workspace + "/" + "footFeat1"
                arcpy.Select_analysis(headFeatClass, headFeat1, whereClause)
                arcpy.Select_analysis(footFeatClass, footFeat1, whereClause)
                # call the helper function to calculate the 8 attributes
                # the input lineFeatClass4 effectively contains cross-feature profiles
                (
                    meanRatio,
                    stdRatio,
                    meanThick,
                    meanSlope,
                    widthDistSlope,
                    widthDistCor,
                    thickDistSlope,
                    thickDistCor,
                ) = calculate_Ratio_Slopes(
                    lineFeatClass4,
                    mosaicBathy,
                    dissolveLineFeat,
                    headFeat1,
                    footFeat1,
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage(
                    "took " + str(diff) + " to calculate these parameters."
                )
            # assign the new values
            row.setValue("mean_width_thickness_ratio", meanRatio)
            row.setValue("std_width_thickness_ratio", stdRatio)
            row.setValue("mean_thickness", meanThick)
            row.setValue("mean_segment_slope", meanSlope)
            row.setValue("width_distance_slope", widthDistSlope)
            row.setValue("width_distance_correlation", widthDistCor)
            row.setValue("thick_distance_slope", thickDistSlope)
            row.setValue("thick_distance_correlation", thickDistCor)
        else:  # calculate only the mean_segment slope attribute
            if (
                lwRatio < 5
            ):  # skipping the non-elongated features and assigning them default values.
                # This saves a lot of time calculating these attributes.
                arcpy.AddMessage("skipping " + str(featID))
                meanSlope = -999
            else:  # only calculate this attribute for elongated features
                arcpy.AddMessage("working on " + str(featID))
                time1 = datetime.now()
                lineFeatClass4 = workspace + "/" + "lineFeatClass4"
                whereClause = "featID = " + str(featID)
                arcpy.Select_analysis(lineFeatClass3, lineFeatClass4, whereClause)
                dissolveLineFeat = workspace + "/" + "lineFeatClass4_dissolved"

                headFeat1 = workspace + "/" + "headFeat1"
                footFeat1 = workspace + "/" + "footFeat1"
                arcpy.Select_analysis(headFeatClass, headFeat1, whereClause)
                arcpy.Select_analysis(footFeatClass, footFeat1, whereClause)
                # call the helper function to calculate the attribute
                # the input lineFeatClass4 effectively contains cross-feature profiles
                meanSlope = calculate_meansegment_Slopes(
                    lineFeatClass4,
                    mosaicBathy,
                    dissolveLineFeat,
                    headFeat1,
                    footFeat1,
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage(
                    "took " + str(diff) + " to calculate these parameters."
                )

            # assign the new values
            row.setValue("mean_segment_slope", meanSlope)

        cursor.updateRow(row)
        i += 1

    del cursor, row

    HelperFunctions.deleteDataItems(itemList)
    arcpy.AddMessage("data deletion done")
    time2 = datetime.now()
    diff = time2 - time1
    arcpy.AddMessage("took " + str(diff) + " to have all attributes generated.")
    return


# This function generates five profiles passing through the centre point
def create_profiles1(inFeat, rectangleFeat, outPointFeat, tempFolder):
    # inFeat: input polygon feature represents a Bathymetry High (Low) feature
    # rectangleFeat: input polygon feature represents the bounding rectangle of the Bathymetry High (Low) feature
    # outPointFeat: output point featureclass represents all profile points
    # tempFolder: the location of temporal folder

    itemList = []
    # generate centre point
    centreFeat = "centreFeat"
    itemList.append(centreFeat)
    arcpy.FeatureToPoint_management(inFeat, centreFeat, "CENTROID")
    tempLayer = "tempLayer"
    itemList.append(tempLayer)
    arcpy.MakeFeatureLayer_management(centreFeat, tempLayer)
    # if the centre point is not inside the polygon
    # (e.g., in case of a multipart feature after using the connection tools)
    # we need to force it
    arcpy.SelectLayerByLocation_management(tempLayer, "WITHIN", inFeat)

    matchcount = int(arcpy.management.GetCount(tempLayer)[0])
    if matchcount == 0:
        arcpy.FeatureToPoint_management(inFeat, centreFeat, "INSIDE")
    arcpy.AddMessage("centre point generated")
    # add x and y
    arcpy.AddXY_management(centreFeat)
    arcpy.AddMessage("Add x and y to centre point")

    cursor = arcpy.SearchCursor(rectangleFeat)
    row = cursor.next()
    angle = row.getValue("MBG_Orientation")
    length = row.getValue("MBG_Length")
    del cursor, row
    # generate five profile lines, passing through the centre point
    angle = float(angle)
    distance = float(length) + 10
    csvFile = tempFolder + "/" + "temp_point_locations.csv"
    itemList.append(csvFile)
    lineFC = "temp_lines"
    itemList.append(lineFC)
    angleList = []
    angleList.append(angle)

    i = 0
    while i < 4:
        angle = angle + 36
        if angle >= 180:
            angle = angle - 180

        angleList.append(angle)
        i += 1
    # get the coordinates of from and to points, in order to generate profile lines
    fil = open(csvFile, "w")
    fil.write("id,from_x,from_y,to_x,to_y,angle" + "\n")
    cursor = arcpy.SearchCursor(centreFeat)
    for row in cursor:
        fid = row.getValue("ORIG_FID")
        centre_x = row.getValue("POINT_X")
        centre_y = row.getValue("POINT_Y")
        for angle in angleList:
            from_x = math.sin(math.radians(angle)) * distance + centre_x
            from_y = math.cos(math.radians(angle)) * distance + centre_y
            to_x = math.sin(math.radians(angle + 180)) * distance + centre_x
            to_y = math.cos(math.radians(angle + 180)) * distance + centre_y
            fil.write(
                str(fid)
                + ","
                + str(from_x)
                + ","
                + str(from_y)
                + ","
                + str(to_x)
                + ","
                + str(to_y)
                + ","
                + str(round(angle, 2))
                + "\n"
            )

    fil.close()
    del cursor, row

    arcpy.XYToLine_management(
        csvFile,
        lineFC,
        "from_x",
        "from_y",
        "to_x",
        "to_y",
        "GEODESIC",
        "angle",
        inFeat,
    )
    arcpy.AddMessage(lineFC + " is created")
    # loop through each profile
    cursor = arcpy.SearchCursor(lineFC)
    mergeFCList = []

    for row in cursor:
        oID = row.getValue("OID")
        whereClause = '"OID" = ' + str(oID)
        sFeat = "selection_" + str(oID)
        arcpy.Select_analysis(lineFC, sFeat, whereClause)
        # intersect each profile with the feature polygon
        fcList = [sFeat, inFeat]
        lineFC1 = "lineFC1"
        arcpy.Intersect_analysis(fcList, lineFC1, "ALL", "", "LINE")

        # convert profile line to profile points along the line
        # normally, the lineFC1 should only have one feature, but occasionally
        # it has 2 or more features due to the default cluster tolerance setting in the above intersect analysis
        # the following codes obtain the length of the main line
        nuLines = int(arcpy.GetCount_management(lineFC1).getOutput(0))
        if nuLines < 1:  # if lineFC1 has no feature, skip this profile
            arcpy.Delete_management(sFeat)
            arcpy.Delete_management(lineFC1)
        else:
            lineLengthList = []
            cursor2 = arcpy.SearchCursor(lineFC1)
            for row2 in cursor2:
                lineLength = row2.getValue("Shape_Length")
                lineLengthList.append(lineLength)

            del cursor2, row2
            lineLength = max(lineLengthList)

            pointFC = "pointFC_" + str(oID)
            pointFC1 = "pointFC_sorted_" + str(oID)
            itemList.append(pointFC1)
            mergeFCList.append(pointFC1)
            # set dist parameter depending on the profile length
            # the dist parameter is used in the densify function next
            # modified on 20240308, to limit the number of vertices generated for a very long profile
            if lineLength > 100000:
                dist = int(lineLength / 300)
            elif lineLength > 40000:
                dist = int(lineLength / 200)
            elif lineLength > 10000:
                dist = 100
            elif lineLength > 1000:
                dist = 50
            elif lineLength > 50:
                dist = 10
            else:
                dist = lineLength / 2
                if dist > 10:
                    dist = 10
            # densify the vertices of the profile lines, effectively adding a vertice at each dist
            arcpy.Densify_edit(lineFC1, "DISTANCE", str(dist) + " Meters")
            # add an ID field
            fieldType = "LONG"
            fieldPrecision = 10
            fieldName = "profileID"
            arcpy.AddField_management(lineFC1, fieldName, fieldType, fieldPrecision)
            expression = oID
            arcpy.CalculateField_management(
                lineFC1, fieldName, expression, "PYTHON3"
            )

            arcpy.FeatureVerticesToPoints_management(lineFC1, pointFC, "ALL")
            # spatial sort
            sort_fields = [["Shape", "ASCENDING"]]
            # Use UR algorithm
            sort_method = "UR"
            arcpy.Sort_management(pointFC, pointFC1, sort_fields, sort_method)

            arcpy.Delete_management(sFeat)
            arcpy.Delete_management(lineFC1)
            arcpy.Delete_management(pointFC)

    del cursor, row

    arcpy.Merge_management(mergeFCList, outPointFeat)
    arcpy.AddMessage("merge done")
    HelperFunctions.deleteDataItems(itemList)


# This function generates five cross-feature profiles
def create_profiles2(inFeat, rectangleFeat, outPointFeat, tempFolder):
    # inFeat: input polygon feature represents a Bathymetry High (Low) feature
    # rectangleFeat: input polygon feature represents the bounding rectangle of the Bathymetry High (Low) feature
    # outPointFeat: output point featureclass represents all profile points
    # tempFolder: the location of temporal folder

    itemList = []
    cursor = arcpy.SearchCursor(rectangleFeat)
    row = cursor.next()
    MbrL = row.getValue("MBG_Length")
    MbrW = row.getValue("MBG_Width")
    del cursor, row

    # bounding rectangle to points
    MbrPoints = "bounding_rectangle_points"
    itemList.append(MbrPoints)
    arcpy.FeatureVerticesToPoints_management(rectangleFeat, MbrPoints, "ALL")
    arcpy.AddMessage("bounding to points done")
    # add x and y
    arcpy.AddXY_management(MbrPoints)
    arcpy.AddMessage("Add x and y done")
    # get x and y values for the starting and ending points
    cursor = arcpy.SearchCursor(MbrPoints)
    row = cursor.next()
    start_x = row.getValue("POINT_X")
    start_y = row.getValue("POINT_Y")
    row = cursor.next()
    end_x = row.getValue("POINT_X")
    end_y = row.getValue("POINT_Y")
    del cursor, row

    # create fishnet
    # this fishnet is used to generate five cross-feature profiles

    # Set coordinate system of the output fishnet
    env.outputCoordinateSystem = arcpy.Describe(rectangleFeat).spatialReference

    fishnetFeat = "fishnet"
    itemList.append(fishnetFeat)
    # Set the origin of the fishnet
    originCoordinate = str(start_x) + " " + str(start_y)

    # Set the orientation
    yAxisCoordinate = str(end_x) + " " + str(end_y)

    numRows = 6
    cellSizeWidth = MbrW
    cellSizeHeight = MbrL / numRows
    numColumns = 1

    oppositeCorner = "#"

    # Create a point label feature class
    labels = "NO_LABELS"

    # Extent is set by origin and opposite corner - no need to use a template fc
    templateExtent = "#"

    # Each output cell will be polyline
    geometryType = "POLYLINE"

    arcpy.CreateFishnet_management(
        fishnetFeat,
        originCoordinate,
        yAxisCoordinate,
        cellSizeWidth,
        cellSizeHeight,
        numRows,
        numColumns,
        oppositeCorner,
        labels,
        templateExtent,
        geometryType,
    )
    arcpy.AddMessage("Fishnet done")

    cursor = arcpy.SearchCursor(fishnetFeat)
    mergeFCList = []

    noFeat1 = 0
    for row in cursor:
        oID = row.getValue("OID")
        # select the 2nd to 6th lines as profiles
        if (oID > 1) & (oID < 7):
            whereClause = '"OID" = ' + str(oID)
            sFeat = "selection_" + str(oID)
            arcpy.Select_analysis(fishnetFeat, sFeat, whereClause)
            fcList = [sFeat, inFeat]
            lineFC1 = "lineFC1"

            arcpy.Intersect_analysis(fcList, lineFC1, "ALL", "", "LINE")

            # normally, the lineFC1 should only have one feature, but occasionally
            # it has 0 feature due to intersecting with a point or not intersecting the feature at all
            # (e.g., in case of the feature is linearly connected multipart feature)
            # or >=2 features due to the default cluster tolerance setting in the above intersect analysis
            # the following codes obtain the length of the main line
            nuLines = int(arcpy.GetCount_management(lineFC1).getOutput(0))
            noFeat1 += nuLines

            if nuLines < 1:  # if lineFC1 has no feature, skip this profile
                arcpy.Delete_management(sFeat)
                arcpy.Delete_management(lineFC1)
            else:  # if lineFC1 has 1 or more features
                lineLengthList = []
                cursor2 = arcpy.SearchCursor(lineFC1)
                for row2 in cursor2:
                    lineLength = row2.getValue("Shape_Length")
                    lineLengthList.append(lineLength)

                del cursor2, row2
                lineLength = max(lineLengthList)
                pointFC = "pointFC_" + str(oID)
                pointFC1 = "pointFC_sorted_" + str(oID)
                itemList.append(pointFC1)
                mergeFCList.append(pointFC1)
                # set dist parameter depending on the profile length
                # the dist parameter is used in the densify function next
                # modified on 20240308, to limit the number of vertices generated for a very long profile
                if lineLength > 100000:
                    dist = int(lineLength / 300)
                elif lineLength > 40000:
                    dist = int(lineLength / 200)
                elif lineLength > 10000:
                    dist = 100
                elif lineLength > 1000:
                    dist = 50
                elif lineLength > 50:
                    dist = 10
                else:
                    dist = lineLength / 2
                    if dist > 10:
                        dist = 10
                # densify the vertices of the profile lines, effectively adding a vertice at each dist
                arcpy.Densify_edit(lineFC1, "DISTANCE", str(dist) + " Meters")

                # add an ID field
                fieldType = "LONG"
                fieldPrecision = 10
                fieldName = "profileID"
                arcpy.AddField_management(
                    lineFC1, fieldName, fieldType, fieldPrecision
                )
                expression = oID
                arcpy.CalculateField_management(
                    lineFC1, fieldName, expression, "PYTHON3"
                )

                arcpy.FeatureVerticesToPoints_management(lineFC1, pointFC, "ALL")
                # spatial sort
                sort_fields = [["Shape", "ASCENDING"]]
                # Use UR algorithm
                sort_method = "UR"
                arcpy.Sort_management(pointFC, pointFC1, sort_fields, sort_method)

                arcpy.Delete_management(sFeat)
                arcpy.Delete_management(lineFC1)
                arcpy.Delete_management(pointFC)

    del cursor, row

    if noFeat1 > 0:
        arcpy.AddMessage(
            str(noFeat1) + " cross-section profiles have actually been created."
        )
        arcpy.Merge_management(mergeFCList, outPointFeat)
        arcpy.AddMessage("merge done")
    # when none of the five cross-section profiles cross the input feature,
    # we force it to generate one profile passing through the centre point
    else:
        arcpy.AddMessage(
            "None of the five cross-section profiles cross the input feature. "
            + "Instead, we are creating one profile passing through the centre point."
        )
        create_profiles3(inFeat, rectangleFeat, outPointFeat, tempFolder)

    HelperFunctions.deleteDataItems(itemList)


# This function generates one profile passing through the centre point
def create_profiles3(inFeat, rectangleFeat, outPointFeat, tempFolder):
    # inFeat: input polygon feature represents a Bathymetry High (Low) feature
    # rectangleFeat: input polygon feature represents the bounding rectangle of the Bathymetry High (Low) feature
    # outPointFeat: output point featureclass represents all profile points
    # tempFolder: the location of temporal folder

    itemList = []
    # generate centre point
    centreFeat = "centreFeat"
    itemList.append(centreFeat)
    arcpy.FeatureToPoint_management(inFeat, centreFeat, "CENTROID")

    tempLayer = "tempLayer"
    itemList.append(tempLayer)
    arcpy.MakeFeatureLayer_management(centreFeat, tempLayer)
    # if the centre point is not inside the polygon
    # (e.g., in case of a multipart feature after using the connection tools)
    # we need to force it
    arcpy.SelectLayerByLocation_management(tempLayer, "WITHIN", inFeat)

    matchcount = int(arcpy.management.GetCount(tempLayer)[0])
    if matchcount == 0:
        arcpy.FeatureToPoint_management(inFeat, centreFeat, "INSIDE")
    arcpy.AddMessage("centre point generated")
    # add x and y
    arcpy.AddXY_management(centreFeat)
    arcpy.AddMessage("Add x and y to centre point")

    cursor = arcpy.SearchCursor(rectangleFeat)
    row = cursor.next()
    angle = row.getValue("MBG_Orientation")
    length = row.getValue("MBG_Length")
    del cursor, row
    # generate one profile line, passing through the centre point
    angle = float(angle)
    distance = float(length) + 10
    csvFile = tempFolder + "/" + "temp_point_locations.csv"
    itemList.append(csvFile)
    lineFC = "temp_lines"
    itemList.append(lineFC)

    angle = angle + 36
    if angle >= 180:
        angle = angle - 180

    # get the coordinates of from and to points, in order to generate profile lines
    fil = open(csvFile, "w")
    fil.write("id,from_x,from_y,to_x,to_y,angle" + "\n")
    cursor = arcpy.SearchCursor(centreFeat)
    for row in cursor:
        fid = row.getValue("ORIG_FID")
        centre_x = row.getValue("POINT_X")
        centre_y = row.getValue("POINT_Y")
        from_x = math.sin(math.radians(angle)) * distance + centre_x
        from_y = math.cos(math.radians(angle)) * distance + centre_y
        to_x = math.sin(math.radians(angle + 180)) * distance + centre_x
        to_y = math.cos(math.radians(angle + 180)) * distance + centre_y
        fil.write(
            str(fid)
            + ","
            + str(from_x)
            + ","
            + str(from_y)
            + ","
            + str(to_x)
            + ","
            + str(to_y)
            + ","
            + str(round(angle, 2))
            + "\n"
        )

    fil.close()
    del cursor, row

    arcpy.XYToLine_management(
        csvFile,
        lineFC,
        "from_x",
        "from_y",
        "to_x",
        "to_y",
        "GEODESIC",
        "angle",
        inFeat,
    )
    arcpy.AddMessage(lineFC + " is created")
    # loop through each profile
    cursor = arcpy.SearchCursor(lineFC)
    mergeFCList = []

    for row in cursor:
        oID = row.getValue("OID")
        whereClause = '"OID" = ' + str(oID)
        sFeat = "selection_" + str(oID)
        arcpy.Select_analysis(lineFC, sFeat, whereClause)
        # intersect each profile with the feature polygon
        fcList = [sFeat, inFeat]
        lineFC1 = "lineFC1"

        arcpy.Intersect_analysis(fcList, lineFC1, "ALL", "", "LINE")

        # convert profile line to profile points along the line
        # normally, the lineFC1 should only have one feature, but occasionally
        # it has 2 or more features due to the default cluster tolerance setting in the above intersect analysis
        # the following codes obtain the length of the main line
        lineLengthList = []
        cursor2 = arcpy.SearchCursor(lineFC1)
        for row2 in cursor2:
            lineLength = row2.getValue("Shape_Length")
            lineLengthList.append(lineLength)

        del cursor2, row2
        lineLength = max(lineLengthList)

        pointFC = "pointFC_" + str(oID)
        pointFC1 = "pointFC_sorted_" + str(oID)
        itemList.append(pointFC1)
        mergeFCList.append(pointFC1)
        # set dist parameter depending on the profile length
        # the dist parameter is used in the densify function next
        # modified on 20240308, to limit the number of vertices generated for a very long profile
        if lineLength > 100000:
            dist = int(lineLength / 300)
        elif lineLength > 40000:
            dist = int(lineLength / 200)
        elif lineLength > 10000:
            dist = 100
        elif lineLength > 1000:
            dist = 50
        elif lineLength > 50:
            dist = 10
        else:
            dist = lineLength / 2
            if dist > 10:
                dist = 10
        # densify the vertices of the profile lines, effectively adding a vertice at each dist
        arcpy.Densify_edit(lineFC1, "DISTANCE", str(dist) + " Meters")
        # add an ID field
        fieldType = "LONG"
        fieldPrecision = 10
        fieldName = "profileID"
        arcpy.AddField_management(lineFC1, fieldName, fieldType, fieldPrecision)
        expression = oID
        arcpy.CalculateField_management(
            lineFC1, fieldName, expression, "PYTHON3"
        )

        arcpy.FeatureVerticesToPoints_management(lineFC1, pointFC, "ALL")
        # spatial sort
        sort_fields = [["Shape", "ASCENDING"]]
        # Use UR algorithm
        sort_method = "UR"
        arcpy.Sort_management(pointFC, pointFC1, sort_fields, sort_method)

        arcpy.Delete_management(sFeat)
        arcpy.Delete_management(lineFC1)
        arcpy.Delete_management(pointFC)

    del cursor, row

    arcpy.Merge_management(mergeFCList, outPointFeat)
    arcpy.AddMessage("merge done")
    HelperFunctions.deleteDataItems(itemList)


# This function calculates Euclidean distance between two points
def calculateDistance(x1, y1, x2, y2):
    # x1,y1: coordinates of the start point
    # x2,y2: coordinates of the end point
    distance = np.sqrt(np.power(x1 - x2, 2) + np.power(y1 - y2, 2))
    return distance


# This function calculates slope gradient of the line segment connecting two points
def calculateSlope(e1, e2, d):
    # e1: elevation of the end point
    # e2: elevation of the start point
    # d: Euclidean distance between the two point
    if d == 0:
        slope = 90.0
    else:
        slope = (e1 - e2) / d
        slope = np.degrees(np.arctan(slope))  # slope as degree
    return slope


# This function calculates a slope threshold from an elevation (depth) profile
# the slope threshold is the slope between the point with the maximum elevation and the point with the minimum elevation
def calculateSlopeThreshold(profileDF, depthCol, xCol, yCol):
    # profileDF: profile data as a pandas dataframe
    # depthCol: the name of the depth column in the profileDF
    # xCol: the name of the x coordinate column in the profileDF
    # yCol: the name of the y coordinate column in the profileDF
    maxDepth = profileDF.loc[profileDF[depthCol] == profileDF[depthCol].max()]
    minDepth = profileDF.loc[profileDF[depthCol] == profileDF[depthCol].min()]
    dist = calculateDistance(
        maxDepth[xCol].values[0],
        maxDepth[yCol].values[0],
        minDepth[xCol].values[0],
        minDepth[yCol].values[0],
    )
    slope = calculateSlope(
        maxDepth[depthCol].values[0], minDepth[depthCol].values[0], dist
    )
    return slope


# This is the main function conducting the profile analysis
# The function is used to find knickpoint(s) along the profile
def profileAnalysis(profileDF, depthCol, xCol, yCol, idArr, slopeThreshold):
    # profileDF: profile data as a pandas dataframe
    # depthCol: the name of the depth column in the profileDF
    # xCol: the name of the x coordinate column in the profileDF
    # yCol: the name of the y coordinate column in the profileDF
    # idArr: the id array
    # slopeThreshold: the designated slope threshold
    s1List = []
    s2List = []
    # loop through each point in the profile
    for i in profileDF.index:
        # split the profile into two sections: upstream and downstream of the point
        upstream = profileDF.loc[profileDF.index < i]
        downstream = profileDF.loc[profileDF.index > i]
        # get the x, y and depth values of the point being processed
        x = profileDF.loc[i, xCol]
        y = profileDF.loc[i, yCol]
        depth = profileDF.loc[i, depthCol]
        # doing upstream first
        # calculating the slope of the point to each of the upstream point(s)
        upSlopeList = []
        if upstream.index.size == 0:
            upSlope = np.nan
        else:
            for j in upstream.index:
                x1 = upstream.loc[j, xCol]
                y1 = upstream.loc[j, yCol]
                depth1 = upstream.loc[j, depthCol]
                dist1 = calculateDistance(x, y, x1, y1)
                slope1 = calculateSlope(depth, depth1, dist1)
                upSlopeList.append(slope1)
            # slope of the upstream section is the mean of the individual upstream slopes
            upSlope = np.mean(np.asarray(upSlopeList))
        s1List.append(upSlope)
        # doing the same for the downstream
        downSlopeList = []
        if downstream.index.size == 0:
            downSlope = np.nan
        else:
            for j in downstream.index:
                x1 = downstream.loc[j, xCol]
                y1 = downstream.loc[j, yCol]
                depth1 = downstream.loc[j, depthCol]
                dist1 = calculateDistance(x, y, x1, y1)
                slope1 = calculateSlope(depth1, depth, dist1)
                downSlopeList.append(slope1)
            downSlope = np.mean(np.asarray(downSlopeList))
        s2List.append(downSlope)

    # add three new columns to the profile data
    profileDF.loc[:, "upSlope"] = s1List
    profileDF.loc[:, "downSlope"] = s2List
    profileDF.loc[:, "diffSlope"] = np.abs(
        profileDF.loc[:, "upSlope"] - profileDF.loc[:, "downSlope"]
    )

    # calculate the 95th percentile of the diffSlope, as the slope threshold for the following round(s)
    diffSlope_95 = profileDF.diffSlope.quantile(0.95)

    # select the row(s) (knick point(s))that satisfying the following criteria from the profile data
    # 1. must be larger than the 99th percentile of the diffSlope;
    # 2. must be larger than the designated slope threshold;
    # 3. must be at least larger than 1.0 degree (to remove very flat profile).
    # selectedID = profileDF.loc[
    #   profileDF.diffSlope>=max(profileDF.diffSlope.mean()+2*profileDF.diffSlope.std(),slopeThreshold,1)
    #   ].index.values
    selectedID = profileDF.loc[
        profileDF.diffSlope
        >= max(profileDF.diffSlope.quantile(0.99), slopeThreshold, 1)
    ].index.values

    # removing the above row(s) from the profile data
    # profileDF = profileDF.loc[
    #   profileDF.diffSlope<max(profileDF.diffSlope.mean()+2*profileDF.diffSlope.std(),slopeThreshold,1)]
    profileDF = profileDF.loc[
        profileDF.diffSlope
        < max(profileDF.diffSlope.quantile(0.99), slopeThreshold, 1)
    ].copy()
    # append the selected row ids into the input array to generate an updated id array
    idArr_new = np.append(idArr, selectedID)
    # return the updated profile data, the input id array, the updated id array, and the 95th percentile of
    # the original profile data as the slope threshold for the following round(s)
    return profileDF, idArr, idArr_new, diffSlope_95


# This function identifies group knick points, with gap less than the designated value
def findGroup(arr, gap):
    # arr: input id array, sorted with ascending order
    # gap: maximum gap allowed between knick points to form the group

    # create an empty array with type=int, to hold the ids of the knick points within the group
    arr1 = np.arange(0)
    # append the first element of the input array into the newly created array
    arr1 = np.append(arr1, arr[0])
    # update the input array after removing the first element
    mask = np.ones(len(arr), dtype=bool)
    mask[0] = False
    arr = arr[mask]
    # loop through the remaining elements in the input id array and append them into the group if the difference
    # is less than the gap
    while arr.size > 0:
        a = arr1[-1]
        b = arr[0]
        if b - a < gap:
            arr1 = np.append(arr1, arr[0])
            mask = np.ones(len(arr), dtype=bool)
            mask[0] = False
            arr = arr[mask]
        else:
            break
    # return the list of id groups and the updated id array
    return arr1.tolist(), arr


# This function calculates the slope for each profile segment, connecting the knick points
def profileSlope(profileDF, xCol, yCol, depthCol):
    # profileDF: profile data as a pandas dataframe
    # depthCol: the name of the depth column in the profileDF
    # xCol: the name of the x coordinate column in the profileDF
    # yCol: the name of the y coordinate column in the profileDF
    xColIndex = np.where(profileDF.columns.values == xCol)[0][0]
    yColIndex = np.where(profileDF.columns.values == yCol)[0][0]
    dColIndex = np.where(profileDF.columns.values == depthCol)[0][0]
    slList = []
    dList = []
    i = 0
    while i < profileDF.index.size:
        # the slope for the line segment connecting the last and first point of the profile
        if i == profileDF.index.size - 1:
            dist = calculateDistance(
                profileDF.iloc[i, xColIndex],
                profileDF.iloc[i, yColIndex],
                profileDF.iloc[0, xColIndex],
                profileDF.iloc[0, yColIndex],
            )
            slope = abs(
                calculateSlope(
                    profileDF.iloc[i, dColIndex], profileDF.iloc[0, dColIndex], dist
                )
            )
            slList.append(slope)
            dList.append(dist)
        # other profile segments
        else:
            dist = calculateDistance(
                profileDF.iloc[i, xColIndex],
                profileDF.iloc[i, yColIndex],
                profileDF.iloc[i + 1, xColIndex],
                profileDF.iloc[i + 1, yColIndex],
            )
            slope = abs(
                calculateSlope(
                    profileDF.iloc[i + 1, dColIndex],
                    profileDF.iloc[i, dColIndex],
                    dist,
                )
            )
            slList.append(slope)
            dList.append(dist)
        i += 1

    return dList, slList


# This function calculates the angles of the polygon formed by the profile segments, connecting the knick points
def profileAngle(profileDF, slopeCol):
    # profileDF: profile data as a pandas dataframe
    # slopeCol: the name of the slope column in the profileDF
    sColIndex = np.where(profileDF.columns.values == slopeCol)[0][0]
    i = 0
    angleList = []
    while i < profileDF.index.size:
        # the first polygon angle
        if i == 0:
            angle = abs(
                profileDF.iloc[i, sColIndex] - profileDF.iloc[-1, sColIndex]
            )
        # the last polygon angle
        elif i == profileDF.index.size - 1:
            angle = abs(
                profileDF.iloc[-1, sColIndex] - profileDF.iloc[i - 1, sColIndex]
            )
        # other polygon angle
        else:
            angle = 180 - abs(
                profileDF.iloc[i - 1, sColIndex] - profileDF.iloc[i, sColIndex]
            )

        angleList.append(angle)
        i += 1
    return angleList


# This function classifies the slope into several categories
def slopeClass(slope):
    if slope < 5:
        sClass = "flat"
    elif slope < 10:
        sClass = "gentle"
    elif slope < 30:
        sClass = "moderate"
    else:
        sClass = "steep"
    return sClass


# This function calculates the profile attributes for the Bathymetric High features
def calculate_profile_attributes_high(profileDF, depthCol, xCol, yCol, gap):
    # profileDF: profile data as a pandas dataframe
    # depthCol: the name of the depth column in the profileDF
    # xCol: the name of the x coordinate column in the profileDF
    # yCol: the name of the y coordinate column in the profileDF
    # gap: the maximum gap allowed between knick points to form the group
    xColIndex = np.where(profileDF.columns.values == xCol)[0][0]
    yColIndex = np.where(profileDF.columns.values == yCol)[0][0]
    distL = []
    x = profileDF.iloc[0, xColIndex]
    y = profileDF.iloc[0, yColIndex]
    # loop through each profile
    for i in profileDF.index:
        x1 = profileDF.loc[i, xCol]
        y1 = profileDF.loc[i, yCol]
        dist = calculateDistance(x, y, x1, y1)
        distL.append(dist)
    profileDF.loc[:, "distance"] = distL

    profileDF_copy = profileDF.copy(deep=True)

    # initialise an id array
    idArr = np.arange(0)
    # calculate a slope threshold
    slopeThreshold = abs(
        calculateSlopeThreshold(profileDF_copy, depthCol, xCol, yCol)
    )

    # conduct the first round of profile analysis using the slopeThreshold
    profileDF_copy, idArr1, idArr2, diffSlope_95 = profileAnalysis(
        profileDF_copy, depthCol, xCol, yCol, idArr, slopeThreshold
    )

    # conduct the following round(s) of profile analysis using the diffSlope_95 as the slopeThreshold
    # stop the loop when there is no element to be appended into the new array,
    # thus the size of the input id array equals the size of the updated id array
    while idArr2.size > idArr1.size:
        profileDF_copy, idArr1, idArr2, dumy_95 = profileAnalysis(
            profileDF_copy, depthCol, xCol, yCol, idArr2, diffSlope_95
        )

    # sort the id array
    idArray = np.sort(idArr2)
    idList = idArray.tolist()
    i = 0
    # find the ids groups
    while i < len(idList):
        if idArray.size > 0:
            idList[i], idArray = findGroup(idArray, gap)
        i += 1

    i = 0
    # create a list holding the ids groups
    idGroups = []
    while i < len(idList):
        if type(idList[i]) == list:
            idGroups.append(idList[i])
        i += 1

    # identify one single knick point from each id group (ie. knick group)
    # the selected knick point represents the first (last) point in the knick group if the group
    # is closer to the start (end) point of the profile
    # select key profileDF from the original profile data
    # the selected key profileDF include the first point, the last point, and the knick profileDF in between

    # a temporary list, holding the values that are used to identify the knick profileDF
    z1 = []

    for idGroup in idGroups:
        z2 = []
        for i in idGroup:
            m1 = i - 1
            m2 = profileDF.index.size - i
            m3 = abs(m2 - m1)
            z2.append(m3)

        z1.append(z2)

    i = 0
    # another temporary list, holding the ids of the selected key profileDF
    z2 = []
    while i < len(idGroups):
        z_1 = idGroups[i]
        z1_1 = z1[i]
        # the index of the minimum value in the list
        indexX = z1_1.index(min(z1_1))
        # select the minimum value from the id list and append it into the temporary list
        # the minimum value indicates the id of the knick point
        z2.append(z_1[indexX])
        i += 1
    # select the key profileDF from the profile data to form a simplified profile (profileDF1)
    z2.insert(0, profileDF.index[0])
    z2.insert(len(z2), profileDF.index[-1])
    profileDF1 = profileDF.loc[z2].copy()
    # add 'knick_point' column
    profileDF.loc[:, "knick_point"] = profileDF.loc[:, "distance"] < 0
    profileDF.loc[z2, "knick_point"] = True

    dList, slList = profileSlope(profileDF1, xCol, yCol, depthCol)
    profileDF1.loc[:, "slope"] = slList
    profileDF1.loc[:, "dist"] = dList
    angleList = profileAngle(profileDF1, "slope")
    profileDF1.loc[:, "polygonAngle"] = angleList

    # calculate profile attributes
    # topSlopeClass: the slope class of the top of a bathymetric high; 'no top' indicates a triangle shape without top
    # sideSlopeClass: the slope class of the sides of a bathymetric high
    # shape: profile shape
    # concave: profile concavity
    # symmetry: profile symmetry
    # topDepth: the depth of the top of a bathymetric high
    # height: the height of the profile
    # length: the length of the profile

    sColIndex = np.where(profileDF1.columns.values == "slope")[0][0]
    dColIndex = np.where(profileDF1.columns.values == "dist")[0][0]
    # use profile skewness to determine shape symmetry
    # add 'numeric_only = True' option to deal with the new Pandas version (2023-04-06)
    skewness = profileDF.skew(axis=0, numeric_only=True)[depthCol]
    if abs(skewness) < 0.2:
        symmetry = "Symmetric"
    else:
        symmetry = "Asymmetric"

    if profileDF1.index.size == 2:  # The simplified profile has only two points
        shape = "Flat"
        symmetry = "NA"
        topClass = "flat"
        concave = "NA"
        slClass = "NA"
    elif (
        profileDF1.index.size == 3
    ):  # The simplified profile has only three profileDF, forming a triangle
        # calculate weighted averaged side slope
        slope1 = abs(profileDF1.iloc[0, sColIndex])
        slope2 = abs(profileDF1.iloc[1, sColIndex])
        dist1 = abs(profileDF1.iloc[0, dColIndex])
        dist2 = abs(profileDF1.iloc[1, dColIndex])
        # to prevent divide by 0; changed on 2023-04-19
        if (dist1 == 0) or (dist2 == 0):
            sideSlope = (slope1 + slope2) / 2
        else:
            sideSlope = slope1 * dist1 / (dist1 + dist2) + slope2 * dist2 / (
                dist1 + dist2
            )
        slClass = slopeClass(sideSlope)
        topClass = "no top"
        concave = "Convex"
        shape = "Triangle"
    else:  # The simplified profile has more than three profileDF, forming a polygon
        slope1 = abs(profileDF1.iloc[0, sColIndex])
        slope2 = abs(profileDF1.iloc[-2, sColIndex])
        dist1 = abs(profileDF1.iloc[0, dColIndex])
        dist2 = abs(profileDF1.iloc[-2, dColIndex])
        # to prevent divide by 0; changed on 20230419
        if (dist1 == 0) or (dist2 == 0):
            sideSlope = (slope1 + slope2) / 2
        else:
            sideSlope = slope1 * dist1 / (dist1 + dist2) + slope2 * dist2 / (
                dist1 + dist2
            )
        slClass = slopeClass(sideSlope)
        sList = []
        i = 1
        while i < profileDF1.index.size - 2:
            s1 = profileDF1.iloc[i, sColIndex]
            sList.append(s1)
            i += 1
        # top slope equals the mean of the slopes of all non-side segments
        topSlope = abs(sum(sList) / len(sList))
        topClass = slopeClass(topSlope)
        # if the polygon has any angles larger than 180, it is considered as concave and irregular in shape
        if profileDF1.polygonAngle.max() > 180:
            concave = "Concave"
            shape = "Irregular"
        else:
            concave = "Convex"
            shape = "Regular"

    sideSlopeClass = slClass
    topSlopeClass = topClass

    if profileDF1.index.size == 2:
        topDepth = "NA"
        height = "NA"
        length = "NA"
    else:
        topDepth = str(abs(profileDF[depthCol].max()))
        height = str(profileDF[depthCol].max() - profileDF[depthCol].min())
        length = str(
            calculateDistance(
                profileDF.iloc[-1, xColIndex],
                profileDF1.iloc[-1, yColIndex],
                profileDF1.iloc[0, xColIndex],
                profileDF1.iloc[0, yColIndex],
            )
        )

    return (
        shape,
        symmetry,
        concave,
        topSlopeClass,
        sideSlopeClass,
        topDepth,
        height,
        length,
    )


# This function calculates the profile attributes for the Bathymetric Low features
def calculate_profile_attributes_low(profileDF, depthCol, xCol, yCol, gap):
    # profileDF: profile data as a pandas dataframe
    # depthCol: the name of the depth column in the profileDF
    # xCol: the name of the x coordinate column in the profileDF
    # yCol: the name of the y coordinate column in the profileDF
    # gap: the maximum gap allowed between knick points to form the group

    xColIndex = np.where(profileDF.columns.values == xCol)[0][0]
    yColIndex = np.where(profileDF.columns.values == yCol)[0][0]
    distL = []
    x = profileDF.iloc[0, xColIndex]
    y = profileDF.iloc[0, yColIndex]
    for i in profileDF.index:
        x1 = profileDF.loc[i, xCol]
        y1 = profileDF.loc[i, yCol]
        dist = calculateDistance(x, y, x1, y1)
        distL.append(dist)
    profileDF.loc[:, "distance"] = distL
    profileDF_copy = profileDF.copy(deep=True)

    # initialise an id array
    idArr = np.arange(0)
    # calculate a slope threshold
    slopeThreshold = abs(
        calculateSlopeThreshold(profileDF_copy, depthCol, xCol, yCol)
    )
    # conduct the first round of profile analysis using the slopeThreshold
    profileDF_copy, idArr1, idArr2, diffSlope_95 = profileAnalysis(
        profileDF_copy, depthCol, xCol, yCol, idArr, slopeThreshold
    )
    # conduct the following round(s) of profile analysis using the diffSlope_95 as the slopeThreshold
    # stop the loop when there is no element to be appended into the new array,
    # thus the size of the input id array equals the size of the updated id array
    while idArr2.size > idArr1.size:
        profileDF_copy, idArr1, idArr2, dumy_95 = profileAnalysis(
            profileDF_copy, depthCol, xCol, yCol, idArr2, diffSlope_95
        )

    # sort the id array
    idArray = np.sort(idArr2)
    idList = idArray.tolist()
    i = 0
    # find the ids groups
    while i < len(idList):
        if idArray.size > 0:
            idList[i], idArray = findGroup(idArray, gap)
        i += 1

    i = 0
    # create a list holding the ids groups
    idGroups = []
    while i < len(idList):
        if type(idList[i]) == list:
            idGroups.append(idList[i])
        i += 1

    # identify one single knick point from each id group (ie. knick group)
    # the selected knick point represents the first (last) point in the knick group if the group
    # is closer to the start (end) point of the profile
    # select key profileDF from the original profile data
    # the selected key profileDF include the first point, the last point, and the knick profileDF in between

    # a temporary list, holding the values that are used to identify the knick profileDF
    z1 = []

    for idGroup in idGroups:
        z2 = []
        for i in idGroup:
            m1 = i - 1
            m2 = profileDF.index.size - i
            m3 = abs(m2 - m1)
            z2.append(m3)

        z1.append(z2)

    i = 0
    # another temporary list, holding the ids of the selected key profileDF
    z2 = []
    while i < len(idGroups):
        z_1 = idGroups[i]
        z1_1 = z1[i]
        # the index of the minimum value in the list
        indexX = z1_1.index(min(z1_1))
        # select the minimum value from the id list and append it into the temporary list
        # the minimum value indicates the id of the knick point
        z2.append(z_1[indexX])
        i += 1
    # select the key profileDF from the profile data to form a simplified profile (profileDF1)
    z2.insert(0, profileDF.index[0])
    z2.insert(len(z2), profileDF.index[-1])
    profileDF1 = profileDF.loc[z2].copy()
    # add 'knick_point' column
    profileDF.loc[:, "knick_point"] = profileDF.loc[:, "distance"] < 0
    profileDF.loc[z2, "knick_point"] = True

    dList, slList = profileSlope(profileDF1, xCol, yCol, depthCol)
    profileDF1.loc[:, "slope"] = slList
    profileDF1.loc[:, "dist"] = dList
    angleList = profileAngle(profileDF1, "slope")
    profileDF1.loc[:, "polygonAngle"] = angleList

    # calculate profile attributes
    # bottomSlopeClass: the slope class of the bottom of a bathymetric low;
    # 'no bottom' indicates a triangle shape without bottom
    # sideSlopeClass: the slope class of the sides of a bathymetric high
    # shape: profile shape
    # concave: profile concavity
    # symmetry: profile symmetry
    # bottomDepth: the depth of the bottom of a bathymetric low
    # height: the relief of the profile
    # length: the length of the profile

    sColIndex = np.where(profileDF1.columns.values == "slope")[0][0]
    dColIndex = np.where(profileDF1.columns.values == "dist")[0][0]
    # use profile skewness to determine shape symmetry
    # add 'numeric_only = True' option to deal with the new Pandas version (2023-04-06)
    skewness = profileDF.skew(axis=0, numeric_only=True)[depthCol]
    if abs(skewness) < 0.2:
        symmetry = "Symmetric"
    else:
        symmetry = "Asymmetric"

    if profileDF1.index.size == 2:  # The simplified profile has only two points
        shape = "Flat"
        symmetry = "NA"
        bottomClass = "flat"
        concave = "NA"
        slClass = "NA"
    elif (
        profileDF1.index.size == 3
    ):  # The simplified profile has only three profileDF, forming a triangle
        # calculate weighted averaged side slope
        slope1 = abs(profileDF1.iloc[0, sColIndex])
        slope2 = abs(profileDF1.iloc[1, sColIndex])
        dist1 = abs(profileDF1.iloc[0, dColIndex])
        dist2 = abs(profileDF1.iloc[1, dColIndex])
        # to prevent divide by 0; changed on 2023-04-19
        if (dist1 == 0) or (dist2 == 0):
            sideSlope = (slope1 + slope2) / 2
        else:
            sideSlope = slope1 * dist1 / (dist1 + dist2) + slope2 * dist2 / (
                dist1 + dist2
            )
        slClass = slopeClass(sideSlope)
        bottomClass = "no bottom"
        concave = "Convex"
        shape = "Triangle"
    else:  # The simplified profile has more than three profileDF, forming a polygon
        slope1 = abs(profileDF1.iloc[0, sColIndex])
        slope2 = abs(profileDF1.iloc[-2, sColIndex])
        dist1 = abs(profileDF1.iloc[0, dColIndex])
        dist2 = abs(profileDF1.iloc[-2, dColIndex])
        # to prevent divide by 0; changed on 2023-04-19
        if (dist1 == 0) or (dist2 == 0):
            sideSlope = (slope1 + slope2) / 2
        else:
            sideSlope = slope1 * dist1 / (dist1 + dist2) + slope2 * dist2 / (
                dist1 + dist2
            )
        slClass = slopeClass(sideSlope)
        sList = []
        i = 1
        while i < profileDF1.index.size - 2:
            s1 = profileDF1.iloc[i, sColIndex]
            sList.append(s1)
            i += 1
        # top slope equals the mean of the slopes of all non-side segments
        bottomSlope = abs(sum(sList) / len(sList))
        bottomClass = slopeClass(bottomSlope)
        # if the polygon has any angles larger than 180, it is considered as concave and irregular in shape
        if profileDF1.polygonAngle.max() > 180:
            concave = "Concave"
            shape = "Irregular"
        else:
            concave = "Convex"
            shape = "Regular"

    sideSlopeClass = slClass
    bottomSlopeClass = bottomClass

    if profileDF1.index.size == 2:
        bottomDepth = "NA"
        height = "NA"
        length = "NA"
    else:
        # fix bottomDepth, using .min() instead of .max() (2023-04-19)
        bottomDepth = str(abs(profileDF[depthCol].min()))
        height = str(profileDF[depthCol].max() - profileDF[depthCol].min())
        length = str(
            calculateDistance(
                profileDF.iloc[-1, xColIndex],
                profileDF1.iloc[-1, yColIndex],
                profileDF1.iloc[0, xColIndex],
                profileDF1.iloc[0, yColIndex],
            )
        )

    return (
        shape,
        symmetry,
        concave,
        bottomSlopeClass,
        sideSlopeClass,
        bottomDepth,
        height,
        length,
    )

# This function is a replicate of the PointsToLine_management function in ArcGIS.PointsToLine_management.
# It is only used when the PointsToLine_management function fails silently for some unknown reasons,
# in case of implementing multiprocessing using a python script.
def myPointsToLine(inPoints, outLines, lineField, tempFolder):
    # inPoints: input point featureclass
    # outLines: output line featureclass
    # tempFolder: temporary folder to store temporary data/file

    # sort the inPoints first
    sortFeat = "inPoints_sorted"
    sortField = [[lineField, "ASCENDING"]]
    arcpy.Sort_management(inPoints, sortFeat, sortField)
    # loop through the sortFeat and populate these three lists for the information we need
    idList = []
    xList = []
    yList = []
    cursor = arcpy.SearchCursor(sortFeat)
    for row in cursor:
        featID = row.getValue(lineField)
        idList.append(featID)
        x = row.getValue("POINT_X")
        xList.append(x)
        y = row.getValue("POINT_Y")
        yList.append(y)
    del row, cursor
    # convert the lists to a data frame
    pointsPD = pd.DataFrame()
    pointsPD['id'] = idList
    pointsPD['x'] = xList
    pointsPD['y'] = yList
    # group the data frame
    pointsGroup = pointsPD.groupby("id")
    # loop through the data frame and write the id, x and y to a csv file
    csvFile = tempFolder + "/" + "pointToLineTemp.csv"
    fil = open(csvFile, "w")
    fil.write(str(lineField) + ",from_x,from_y,to_x,to_y" + "\n")
    for pts in pointsGroup.groups:
        points = pointsGroup.get_group(pts)
        i = 0
        while i < points.id.size - 1:
            fid = points.iloc[i].id
            from_x = points.iloc[i].x
            from_y = points.iloc[i].y
            to_x = points.iloc[i+1].x
            to_y = points.iloc[i+1].y
            fil.write(str(fid) + "," + str(from_x) + "," + str(from_y) + "," + str(to_x) + "," + str(to_y) + "\n")
            i += 1

    fil.close()
    # convert XY table (the csv file) to lines, then dissolve
    lineFeat = "xyLines"
    arcpy.XYToLine_management(
        csvFile,
        lineFeat,
        "from_x",
        "from_y",
        "to_x",
        "to_y",
        "GEODESIC",
        lineField,
        inPoints,
    )

    arcpy.Dissolve_management(lineFeat, outLines, lineField)
    arcpy.Delete_management(sortFeat)
    arcpy.Delete_management(csvFile)
    arcpy.Delete_management(lineFeat)

    return

# This function creates temporary workspaces and folders, splits the input featureclass into subsets,
# and copies a subset and input bathymetry grid into each workspace
def splitFeat(workspace, inFeat, inBathy, noSplit):
    # workspace: the input workspace which contains the inFeat and inBathy
    # inFeat: input featureclass of bathymetric high or low features
    # inBathy: input bathymetry grid
    # noSplit: number of subsets to split

    noFeat = int(arcpy.GetCount_management(inFeat).getOutput(0))
    featCount = int(noFeat / noSplit)
    featList = []
    bathyList = []
    tempfolderList = []
    path = workspace.rstrip(workspace.split('/')[-1])
    path = path.rstrip('/')
    baseName = workspace.split('/')[-1]
    baseName = baseName.split('.')[0]
    inBathy = inBathy.split('/')[-1]
    inFeat = inFeat.split('/')[-1]
    arcpy.AddMessage(inBathy)

    i = 1
    while i <= noSplit:
        # create a File Geodatabase
        gdbName = baseName + str(i) + '.gdb'
        arcpy.CreateFileGDB_management(path, gdbName)
        arcpy.AddMessage(gdbName + ' created')

        # copy inBathy
        data1 = path + '/' + gdbName + '/' + inBathy
        bathyList.append(data1)
        arcpy.Copy_management(inBathy, data1)
        arcpy.AddMessage(inBathy + ' copied')

        # select a subset of inFeat depending on the number of splits
        startID = (i-1)*featCount
        if i == noSplit:
            endID = noFeat
        else:
            endID = i*featCount
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
        i += 1
    return featList, bathyList, tempfolderList

# This function calculates profile attributes for bathymetric high features
def calculateProfileBH(workspaceName, tempFolder, inFeatClass, inBathy, areaT):
    # workspaceName: input workspace
    # tempFolder: input temporary folder
    # inFeatClass: input bathymetric high featureclass
    # inBathy: input bathymetry grid
    # areaT: area threshold parameter

    env.workspace = workspaceName
    env.overwriteOutput = True
    # eight profile attributes to be added to the input feature
    fieldList = [
        "profileShape",
        "profileSymmetry",
        "profileConcavity",
        "profile_top_SlopeClass",
        "profile_side_SlopeClass",
        "profile_top_Depth",
        "profileRelief",
        "profileLength",
    ]
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    for field in fieldList:
        if field in field_names:
            arcpy.AddMessage(field + " already exists and will be deleted")
            arcpy.DeleteField_management(inFeatClass, field)

    # expand inBathy
    # This is to ensure that the profile point(s) at the edge of bathymetry grid have depth values
    inFocal = inBathy + "_focal"
    outFocalStat = FocalStatistics(
        inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
    )
    outFocalStat.save(inFocal)
    # mosaic to new raster
    mosaicBathy = "mosaicBathy"
    inputRasters = [inBathy, inFocal]
    arcpy.MosaicToNewRaster_management(
        inputRasters,
        workspaceName,
        mosaicBathy,
        inBathy,
        "32_BIT_FLOAT",
        "#",
        "1",
        "FIRST",
        "FIRST",
    )
    arcpy.AddMessage("mosaic done")
    mosaicBathy = workspaceName + "/" + "mosaicBathy"

    mergeList = []

    areaThresholdValue = areaT.split(" ")[0]
    areaUnit = areaT.split(" ")[1]
    # convert the input area unit to "SQUARE_KILOMETERS"
    converter = HelperFunctions.areaUnitConverter(areaUnit)
    areaThresholdValue = converter * float(areaThresholdValue)
    # convert to "square meters"
    areaThresholdValue = areaThresholdValue * 1000000

    # generate bounding rectangle
    MbrFeatClass = "bounding_rectangle"
    arcpy.MinimumBoundingGeometry_management(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    arcpy.AddMessage("bounding rectangle generated")
    noFeat = int(arcpy.GetCount_management(inFeatClass).getOutput(0))
    noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
    arcpy.AddMessage("noFeat: " + str(noFeat))
    arcpy.AddMessage("noRectangle: " + str(noRectangle))
    # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
    # if not, regenerate the bounding rectangle up to three times
    if noRectangle < noFeat:
        arcpy.MinimumBoundingGeometry_management(
            inFeatClass,
            MbrFeatClass,
            "RECTANGLE_BY_WIDTH",
            "NONE",
            "",
            "MBG_FIELDS",
        )
        noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
        if noRectangle < noFeat:
            arcpy.MinimumBoundingGeometry_management(
                inFeatClass,
                MbrFeatClass,
                "RECTANGLE_BY_WIDTH",
                "NONE",
                "",
                "MBG_FIELDS",
            )
            noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
            if noRectangle < noFeat:
                arcpy.MinimumBoundingGeometry_management(
                    inFeatClass,
                    MbrFeatClass,
                    "RECTANGLE_BY_WIDTH",
                    "NONE",
                    "",
                    "MBG_FIELDS",
                )
                noRectangle = int(
                    arcpy.GetCount_management(MbrFeatClass).getOutput(0)
                )
                if noRectangle < noFeat:
                    arcpy.AddMessage(
                        "noRectangle: "
                        + str(noRectangle)
                        + " does not equal to noFeat: "
                        + str(noFeat)
                    )

    # loop through each input feature
    cursor = arcpy.SearchCursor(inFeatClass)
    k = 1
    for row in cursor:
        # only do this every 100 iterations
        if k % 100 == 1:
            arcpy.Compact_management(
                workspaceName
            )  # compact the geodatabase to reduce its size and potentially improve the performance
            arcpy.AddMessage("Compacted the geodatabase")
        try:
            itemList = []
            featID = row.getValue("featID")
            arcpy.AddMessage("working on feature: " + str(featID))

            LwR = row.getValue("LengthWidthRatio")
            area = row.getValue("Shape_Area")
            arcpy.AddMessage("area: " + str(area))
            whereClause = '"featID" = ' + str(featID)
            inFeat = workspaceName + "/" + "inFeat_" + str(featID)
            mergeList.append(inFeat)

            # select the feature
            arcpy.Select_analysis(inFeatClass, inFeat, whereClause)

            boundFeat = workspaceName + "/" + "boundFeat_" + str(featID)
            itemList.append(boundFeat)

            # select the feature
            arcpy.Select_analysis(MbrFeatClass, boundFeat, whereClause)

            profilePointFC = workspaceName + "/" + "profilePointFC"
            itemList.append(profilePointFC)

            # depending on the following criteria, creating different profiles
            if (
                    area < areaThresholdValue
            ):  # for a smaller polygon feature, create only one profile. This would save time
                time1 = datetime.now()
                create_profiles3(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profile3.")
            elif (
                    LwR <= 5.0
            ):  # for a polygon feature that is not elongated, create five profiles passing through the polygon centre
                time1 = datetime.now()
                create_profiles1(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profiles1.")
            else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                time1 = datetime.now()
                create_profiles2(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profiles2.")

            # extract depth values to profile points
            profilePointFC1 = workspaceName + "/" + "profilePointFC1"
            itemList.append(profilePointFC1)
            ExtractValuesToPoints(profilePointFC, mosaicBathy, profilePointFC1)
            arcpy.AddMessage("extract depth values done")
            # Add x and y
            arcpy.AddXY_management(profilePointFC1)
            arcpy.AddMessage("Add x and y done")
            # export the table to a csv file
            outCSV = tempFolder + "/" + "profilePointFC1.csv"
            itemList.append(outCSV)
            # delete schema.ini which may contains incorrect data types (2023-04-20)
            schemaFile = tempFolder + "/" + "schema.ini"
            if os.path.isfile(schemaFile):
                os.remove(schemaFile)

            arcpy.CopyRows_management(profilePointFC1, outCSV)
            arcpy.AddMessage(outCSV + " is generated")
            # read in the csv file as pandas dataframe
            points = pd.read_csv(outCSV, sep=",", header=0)
            points.set_index("OBJECTID", inplace=True)

            # calculate profile attributes
            profileIDList = np.unique(points.profileID)
            shapeList = []
            symmetryList = []
            concaveList = []
            topSlopeClassList = []
            sideSlopeClassList = []
            topDepthList = []
            heightList = []
            lengthList = []
            # loop through each profile for the polygon feature
            for profileID in profileIDList:
                pointsT = points.loc[points.profileID == profileID].copy()
                depthCol = "RASTERVALU"
                if pointsT.index.size > 10:
                    gap = 4
                else:
                    gap = 3
                # calling the 'calculate_profile_attributes_high' function
                (
                    shape,
                    symmetry,
                    concave,
                    topSlopeClass,
                    sideSlopeClass,
                    topDepth,
                    height,
                    length,
                ) = calculate_profile_attributes_high(
                    pointsT, depthCol, "POINT_X", "POINT_Y", gap
                )
                # append the profile attributes to the lists
                shapeList.append(shape)
                symmetryList.append(symmetry)
                concaveList.append(concave)
                topSlopeClassList.append(topSlopeClass)
                sideSlopeClassList.append(sideSlopeClass)
                topDepthList.append(topDepth)
                heightList.append(height)
                lengthList.append(length)

            valueList = []
            # for a polygon feature with five profiles, join all attribute values together as a string
            shape = ",".join(shapeList)
            symmetry = ",".join(symmetryList)
            concave = ",".join(concaveList)
            topSlopeClass = ",".join(topSlopeClassList)
            sideSlopeClass = ",".join(sideSlopeClassList)
            topDepth = ",".join(topDepthList)
            height = ",".join(heightList)
            length = ",".join(lengthList)

            valueList.append(shape)
            valueList.append(symmetry)
            valueList.append(concave)
            valueList.append(topSlopeClass)
            valueList.append(sideSlopeClass)
            valueList.append(topDepth)
            valueList.append(height)
            valueList.append(length)
            arcpy.AddMessage(valueList)
            arcpy.AddMessage("profile attributes calculated")

            for field in fieldList:
                fieldType = "TEXT"
                fieldLength = 200
                fields = arcpy.ListFields(inFeat)
                field_names = [f.name for f in fields]
                if field in field_names:
                    arcpy.AddMessage(field + " exists")
                else:
                    arcpy.AddField_management(
                        inFeat, field, fieldType, field_length=fieldLength
                    )

            arcpy.AddMessage("profile fields added")

            # calculate fields
            i = 0
            for field in fieldList:
                # calculate string to a text field, the string must be enclosed by double quote
                expression = '"' + valueList[i] + '"'
                arcpy.CalculateField_management(
                    inFeat, field, expression, "PYTHON3"
                )
                i += 1

            arcpy.AddMessage("profile fields calculated")

            # delete intermediate data
            HelperFunctions.deleteDataItems(itemList)
            arcpy.AddMessage("intermediate data deleted")
        except:
            arcpy.AddMessage("failed on " + str(featID))
            continue
        k += 1

    del cursor, row

    # merge all individual features together
    mergedFeat = "mergedFeat"
    arcpy.Merge_management(mergeList, mergedFeat)
    arcpy.AddMessage("merged all done")

    # transfer the field values to inFeatClass

    for field in fieldList:
        inID = "featID"
        joinID = "featID"
        expression = "!" + mergedFeat + "." + field + "!"
        HelperFunctions.addTextField(
            inFeatClass, mergedFeat, field, inID, joinID, expression
        )

    arcpy.AddMessage("Profile attributes added and calculated")

# This function calculates profile attributes for the bathymetric low features
def calculateProfileBL(workspaceName, tempFolder, inFeatClass, inBathy, areaT):
    # workspaceName: input workspace
    # tempFolder: input temporary folder
    # inFeatClass: input bathymetric high featureclass
    # inBathy: input bathymetry grid
    # areaT: area threshold parameter

    env.workspace = workspaceName
    env.overwriteOutput = True
    # eight profile attributes to be added to the input feature
    fieldList = [
        "profileShape",
        "profileSymmetry",
        "profileConcavity",
        "profile_bottom_SlopeClass",
        "profile_side_SlopeClass",
        "profile_bottom_Depth",
        "profileRelief",
        "profileLength",
    ]
    fields = arcpy.ListFields(inFeatClass)
    field_names = [f.name for f in fields]
    for field in fieldList:
        if field in field_names:
            arcpy.AddMessage(field + " already exists and will be deleted")
            arcpy.DeleteField_management(inFeatClass, field)

    # expand inBathy
    # This is to ensure that the profile point(s) at the edge of bathymetry grid have depth values
    inFocal = inBathy + "_focal"
    outFocalStat = FocalStatistics(
        inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
    )
    outFocalStat.save(inFocal)
    # mosaic to new raster
    mosaicBathy = "mosaicBathy"
    inputRasters = [inBathy, inFocal]
    arcpy.MosaicToNewRaster_management(
        inputRasters,
        workspaceName,
        mosaicBathy,
        inBathy,
        "32_BIT_FLOAT",
        "#",
        "1",
        "FIRST",
        "FIRST",
    )
    arcpy.AddMessage("mosaic done")
    mosaicBathy = workspaceName + "/" + "mosaicBathy"

    mergeList = []
    # convert the input area unit to "SQUARE_KILOMETERS"
    areaThresholdValue = areaT.split(" ")[0]
    areaUnit = areaT.split(" ")[1]
    # convert the input area unit to "SQUARE_KILOMETERS"
    converter = HelperFunctions.areaUnitConverter(areaUnit)
    areaThresholdValue = converter * float(areaThresholdValue)
    # convert to "square meters"
    areaThresholdValue = areaThresholdValue * 1000000

    # generate bounding rectangle
    MbrFeatClass = "bounding_rectangle"
    arcpy.MinimumBoundingGeometry_management(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    noFeat = int(arcpy.GetCount_management(inFeatClass).getOutput(0))
    noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
    arcpy.AddMessage("noFeat: " + str(noFeat))
    arcpy.AddMessage("noRectangle: " + str(noRectangle))
    # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
    # if not, regenerate the bounding rectangle up to three times
    if noRectangle < noFeat:
        arcpy.MinimumBoundingGeometry_management(
            inFeatClass,
            MbrFeatClass,
            "RECTANGLE_BY_WIDTH",
            "NONE",
            "",
            "MBG_FIELDS",
        )
        noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
        if noRectangle < noFeat:
            arcpy.MinimumBoundingGeometry_management(
                inFeatClass,
                MbrFeatClass,
                "RECTANGLE_BY_WIDTH",
                "NONE",
                "",
                "MBG_FIELDS",
            )
            noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
            if noRectangle < noFeat:
                arcpy.MinimumBoundingGeometry_management(
                    inFeatClass,
                    MbrFeatClass,
                    "RECTANGLE_BY_WIDTH",
                    "NONE",
                    "",
                    "MBG_FIELDS",
                )
                noRectangle = int(
                    arcpy.GetCount_management(MbrFeatClass).getOutput(0)
                )
                if noRectangle < noFeat:
                    arcpy.AddMessage(
                        "noRectangle: "
                        + str(noRectangle)
                        + " does not equal to noFeat: "
                        + str(noFeat)
                    )
    cursor = arcpy.SearchCursor(inFeatClass)
    # loop through each feature
    k = 1
    for row in cursor:
        # only do this every 100 iterations
        if k % 100 == 1:
            arcpy.Compact_management(
                workspaceName
            )  # compact the geodatabase to reduce its size and potentially improve the performance
            arcpy.AddMessage("Compacted the geodatabase")
        try:
            itemList = []
            featID = row.getValue("featID")
            arcpy.AddMessage("working on feature: " + str(featID))
            LwR = row.getValue("LengthWidthRatio")
            area = row.getValue("Shape_Area")
            arcpy.AddMessage("area: " + str(area))
            whereClause = '"featID" = ' + str(featID)
            inFeat = workspaceName + "/" + "inFeat_" + str(featID)
            mergeList.append(inFeat)

            # select the feature
            arcpy.Select_analysis(inFeatClass, inFeat, whereClause)

            boundFeat = workspaceName + "/" + "boundFeat_" + str(featID)
            itemList.append(boundFeat)

            # select the feature
            arcpy.Select_analysis(MbrFeatClass, boundFeat, whereClause)

            profilePointFC = workspaceName + "/" + "profilePointFC"
            itemList.append(profilePointFC)

            # depending on the following criteria, creating different profiles
            if (
                    area < areaThresholdValue
            ):  # for a smaller polygon feature, create only one profile. This would save time
                time1 = datetime.now()
                create_profiles3(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profile3.")
            elif (
                    LwR <= 5.0
            ):  # for a polygon feature that is not elongated, create five profiles passing through the polygon centre
                time1 = datetime.now()
                create_profiles1(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profile1.")
            else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                time1 = datetime.now()
                create_profiles2(
                    inFeat, boundFeat, profilePointFC, tempFolder
                )
                time2 = datetime.now()
                diff = time2 - time1
                arcpy.AddMessage("took " + str(diff) + " to create profile2.")

            # extract depth values to profile points
            profilePointFC1 = workspaceName + "/" + "profilePointFC1"
            itemList.append(profilePointFC1)
            ExtractValuesToPoints(profilePointFC, mosaicBathy, profilePointFC1)
            arcpy.AddMessage("extract depth values done")
            # Add x and y
            arcpy.AddXY_management(profilePointFC1)
            arcpy.AddMessage("Add x and y done")
            # export the table to a csv file
            outCSV = tempFolder + "/" + "profilePointFC1.csv"
            itemList.append(outCSV)
            # delete schema.ini which may contains incorrect data types (2023-04-20)
            schemaFile = tempFolder + "/" + "schema.ini"
            if os.path.isfile(schemaFile):
                os.remove(schemaFile)

            arcpy.CopyRows_management(profilePointFC1, outCSV)
            arcpy.AddMessage(outCSV + " is generated")
            # read in the csv file as pandas dataframe
            points = pd.read_csv(outCSV, sep=",", header=0)
            points.set_index("OBJECTID", inplace=True)
            # calculate profile attributes

            profileIDList = np.unique(points.profileID)
            shapeList = []
            symmetryList = []
            concaveList = []
            bottomSlopeClassList = []
            sideSlopeClassList = []
            bottomDepthList = []
            heightList = []
            lengthList = []
            # loop through each profile
            for profileID in profileIDList:

                pointsT = points.loc[points.profileID == profileID].copy()
                depthCol = "RASTERVALU"
                if pointsT.index.size > 10:
                    gap = 4
                else:
                    gap = 3
                # calling the 'calculate_profile_attributes_low' helper function
                (
                    shape,
                    symmetry,
                    concave,
                    bottomSlopeClass,
                    sideSlopeClass,
                    bottomDepth,
                    height,
                    length,
                ) = calculate_profile_attributes_low(
                    pointsT, depthCol, "POINT_X", "POINT_Y", gap
                )
                shapeList.append(shape)
                symmetryList.append(symmetry)
                concaveList.append(concave)
                bottomSlopeClassList.append(bottomSlopeClass)
                sideSlopeClassList.append(sideSlopeClass)
                bottomDepthList.append(bottomDepth)
                heightList.append(height)
                lengthList.append(length)

            valueList = []
            shape = ",".join(shapeList)
            symmetry = ",".join(symmetryList)
            concave = ",".join(concaveList)
            bottomSlopeClass = ",".join(bottomSlopeClassList)
            sideSlopeClass = ",".join(sideSlopeClassList)
            bottomDepth = ",".join(bottomDepthList)
            height = ",".join(heightList)
            length = ",".join(lengthList)
            valueList.append(shape)
            valueList.append(symmetry)
            valueList.append(concave)
            valueList.append(bottomSlopeClass)
            valueList.append(sideSlopeClass)
            valueList.append(bottomDepth)
            valueList.append(height)
            valueList.append(length)
            arcpy.AddMessage("profile attributes calculated")

            for field in fieldList:
                fieldType = "TEXT"
                fieldLength = 200
                fields = arcpy.ListFields(inFeat)
                field_names = [f.name for f in fields]
                if field in field_names:
                    arcpy.AddMessage(field + " exists")
                else:
                    arcpy.AddField_management(
                        inFeat, field, fieldType, field_length=fieldLength
                    )

            arcpy.AddMessage("profile fields added")

            # calculate fields
            i = 0
            for field in fieldList:
                # calculate string to a text field, the string must be enclosed by double quote
                expression = '"' + valueList[i] + '"'
                arcpy.CalculateField_management(
                    inFeat, field, expression, "PYTHON3"
                )
                i += 1

            arcpy.AddMessage("profile fields calculated")

            # delete intermediate data
            HelperFunctions.deleteDataItems(itemList)
            arcpy.AddMessage("intermediate data deleted")

        except:
            arcpy.AddMessage("failed on " + str(featID))
            continue
        k += 1

    del cursor, row
    # merge all individual features together
    mergedFeat = "mergedFeat"
    arcpy.Merge_management(mergeList, mergedFeat)
    arcpy.AddMessage("merged all done")

    # transfer the field values to inFeatClass

    for field in fieldList:
        inID = "featID"
        joinID = "featID"
        expression = "!" + mergedFeat + "." + field + "!"
        HelperFunctions.addTextField(
            inFeatClass, mergedFeat, field, inID, joinID, expression
        )

    arcpy.AddMessage("Profile attributes added and calculated")


if __name__ == '__main__':
    arcpy.AddMessage("dummy message")
