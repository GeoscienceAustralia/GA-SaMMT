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

##arcpy.CheckOutExtension("Spatial")

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


# This function executes the multiprocessing to calculate the topographic attributes for the bathymetric high features
def execute_topographic_BH(argList, n_cpu):
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
        results = pool.map(add_topographic_attributes_high_function, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function executes the multiprocessing to calculate the topographic attributes for the bathymetric low features
def execute_topographic_BL(argList, n_cpu):
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
        results = pool.map(add_topographic_attributes_low_function, argList)

    arcpy.AddMessage("multiprocessing done all")
    
# This function calculates the topographic attributes for the bathymetric high features
def add_topographic_attributes_high_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    slpGrid = arg[4]
    saGrid = arg[5]

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the topographic features
    calculateTopographicBH(workspaceName, tempFolder, inFeat, inBathy, slpGrid, saGrid)

    arcpy.CheckInExtension("Spatial")

    return

# This function calculates the topographic attributes for the bathymetric low features
def add_topographic_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    headFeat = arg[3]
    footFeat = arg[4]
    inBathy = arg[5]
    slpGrid = arg[6]
    saGrid = arg[7]

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the topographic features
    calculateTopographicBL(workspaceName, tempFolder, inFeat, headFeat, footFeat, inBathy, slpGrid, saGrid)

    arcpy.CheckInExtension("Spatial")

    return

# This function calculates the shape attributes for the bathymetric high features
def add_shape_attributes_high_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the shape features
    calculateCompactness(inFeat)
    calculateCircularity_Convexity_Solidity(workspaceName, inFeat)
    calculateSinuosity_LwR(workspaceName, tempFolder, inFeat, inBathy)

    arcpy.CheckInExtension("Spatial")

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

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the shape features
    calculateCompactness(inFeat)
    calculateCircularity_Convexity_Solidity(workspaceName, inFeat)
    calculateSinuosity_LwR_WdR_Slopes(workspaceName, tempFolder, inFeat, inBathy, headFeat, footFeat, additionalOption)

    arcpy.CheckInExtension("Spatial")

    return

# This function calculates the profile attributes for the bathymetric high features
def add_profile_attributes_high_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    areaT = arg[4]

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the shape features
    calculateProfileBH(workspaceName, tempFolder, inFeat, inBathy, areaT)

    arcpy.CheckInExtension("Spatial")

    return

# This function calculates the profile attributes for the bathymetric low features
def add_profile_attributes_low_function(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    tempFolder = arg[1]
    inFeat = arg[2]
    inBathy = arg[3]
    areaT = arg[4]

    if arcpy.CheckExtension("Spatial") == "Available":
        arcpy.CheckOutExtension("Spatial")
        print("Spatial Analyst license checked out successfully.")
    else:
        print("Spatial Analyst license is unavailable.")
        
    # calling individual functions to calculate the shape features
    calculateProfileBL(workspaceName, tempFolder, inFeat, inBathy, areaT)

    arcpy.CheckInExtension("Spatial")

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
            arcpy.management.Compact(workspace)
            arcpy.AddMessage("Compacted the geodatabase")
        time1 = datetime.now()
        featID = row1.getValue("featID")
        MbrL = row1.getValue("rectangle_Length")
        MbrW = row1.getValue("rectangle_Width")
        whereClause = '"featID" = ' + str(featID)
        arcpy.AddMessage("working on featID: " + str(featID))
        # select one polygon and its bounding polygon
        arcpy.analysis.Select(inFeatClass, inFeat, whereClause)
        arcpy.analysis.Select(workspace + "/" + MbrFeatClass, MbrFeat, whereClause)
        arcpy.AddMessage("selection done")

        # convert bounding rectangle to points
        arcpy.management.FeatureVerticesToPoints(MbrFeat, MbrPoints, "ALL")
        arcpy.AddMessage("bounding to points done")
        # add x and y
        arcpy.management.AddXY(MbrPoints)
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
        arcpy.management.CreateFishnet(
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
        arcpy.analysis.Intersect(inFeats, intersectOut1)
        arcpy.AddMessage("intersect done")
        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to split this polygon.")

        i += 1

    del cursor1, row1

    # merge all features together

    arcpy.management.Merge(mergeList, splitFeatClass)
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
        arcpy.management.AddField(
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
    arcpy.management.CalculateField(
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
    arcpy.management.MinimumBoundingGeometry(
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
            arcpy.management.AddField(
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

        arcpy.management.CalculateField(
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
    arcpy.management.MinimumBoundingGeometry(
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
            arcpy.management.AddField(
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
    arcpy.management.PolygonToLine(splitFeatClass, lineFeatClass1)
    arcpy.AddMessage("polygon to line done")
    # selection
    lineFeatClass2 = workspace + "/" + "lineFeatClass2"
    itemList.append(lineFeatClass2)
    whereClause = "LEFT_FID <> -1"
    arcpy.analysis.Select(lineFeatClass1, lineFeatClass2, whereClause)
    arcpy.AddMessage("selection done")
    # spatial join
    lineFeatClass3 = workspace + "/" + "lineFeatClass3"
    itemList.append(lineFeatClass3)
    arcpy.analysis.SpatialJoin(
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
    arcpy.analysis.Statistics(lineFeatClass3, outTab1, statsField, caseField)

    outTab2 = "outTab2"
    itemList.append(outTab2)
    statsField = [["SUM_Shape_Length", "MEAN"]]
    caseField = "featID"
    arcpy.analysis.Statistics(outTab1, outTab2, statsField, caseField)
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
    arcpy.management.FeatureVerticesToPoints(inFeatClass, inFeatVertices, "ALL")
    arcpy.AddMessage("feature vertices to points done")

    # add x and y
    arcpy.management.AddXY(inFeatVertices)
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

    arcpy.management.CopyRows(inFeatVertices, csvFile1)
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
    arcpy.analysis.Select(inFeatVertices, pointFeat1, whereClause)
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
    arcpy.management.Copy(pointFeat1, pointFeat2)
    arcpy.management.CopyRows(pointFeat2, csvFile2)
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
    arcpy.analysis.Select(pointFeat1, firstFeatClass, whereClause)
    # generate last points featureclass
    text = "("
    for i in lastList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    lastFeatClass = workspace + "/" + "lastPoints"
    itemList.append(lastFeatClass)
    arcpy.analysis.Select(pointFeat1, lastFeatClass, whereClause)
    arcpy.AddMessage("generate first and last points features done")

    # polygon to point
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    # Use FeatureToPoint function to find a point inside each part
    arcpy.management.FeatureToPoint(splitFeatClass, pointFeat2, "CENTROID")
    arcpy.AddMessage("feature to point done")

    # sort the points
    pointFeat2_1 = workspace + "/" + "pointFeat2_1"
    itemList.append(pointFeat2_1)
    pointFeat2_2 = workspace + "/" + "pointFeat2_2"
    itemList.append(pointFeat2_2)
    arcpy.management.Sort(pointFeat2, pointFeat2_1, [["ORIG_FID", "ASCENDING"]])
    arcpy.management.Sort(pointFeat2, pointFeat2_2, [["ORIG_FID", "DESCENDING"]])

    # add x and y
    arcpy.management.AddXY(pointFeat2_1)
    arcpy.management.AddXY(pointFeat2_2)
    arcpy.AddMessage("Add x and y done")

    # merge the first point, the centre points of each sub-polygon, then the last point
    mergedFeats = [firstFeatClass, pointFeat2_1, lastFeatClass]
    mergedFeat1_1 = workspace + "/" + "merged_points1_1"
    itemList.append(mergedFeat1_1)
    arcpy.management.Merge(mergedFeats, mergedFeat1_1)

    mergedFeats = [firstFeatClass, pointFeat2_2, lastFeatClass]
    mergedFeat1_2 = workspace + "/" + "merged_points1_2"
    itemList.append(mergedFeat1_2)
    arcpy.management.Merge(mergedFeats, mergedFeat1_2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat1_1 = "curveLine1"
    itemList.append(lineFeat1_1)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.management.PointsToLine(mergedFeat1_1, lineFeat1_1, lineField, sortField)
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
    arcpy.management.PointsToLine(mergedFeat1_2, lineFeat1_2, lineField, sortField)
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
    arcpy.management.Merge(mergedFeats, mergedCurveFeat)
    arcpy.AddMessage("merged curves done")

    # summary statistics
    # in order to select the shorter curveline
    outTab3 = "outTab3"
    itemList.append(outTab3)
    statsField = [["Shape_Length", "MIN"]]
    caseField = ["featID"]
    arcpy.analysis.Statistics(mergedCurveFeat, outTab3, statsField, caseField)

    # merge to create a straight line connecting the first
    # and last point in order to calculate the straight length (head to foot length)
    mergedFeats = [firstFeatClass, lastFeatClass]
    mergedFeat2 = workspace + "/" + "merged_points2"
    itemList.append(mergedFeat2)
    arcpy.management.Merge(mergedFeats, mergedFeat2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat2 = "straightLine"
    itemList.append(lineFeat2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.management.PointsToLine(mergedFeat2, lineFeat2, lineField, sortField)
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
    arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate Sinuosity field done")
    field = "LengthWidthRatio"
    expression = "!sinuous_length! / !mean_width!"
    arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")
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
    arcpy.analysis.Select(inFeat, outFeat2, whereClause)
    arcpy.management.Copy(outFeat2, outFeat)
    # count the number of profiles
    noLines = int(arcpy.management.GetCount(dissolveLineFeat).getOutput(0))

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
        arcpy.management.Sort(outFeat2, outFeat3, sortField)
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
            arcpy.analysis.Select(outFeat3, outFeat4, whereClause)
            arcpy.management.Copy(outFeat4, outFeat)
        else:
            arcpy.management.Copy(outFeat3, outFeat)
        # startX and startY represent the XY of the start point of the line segment
        # endX and endY represent the XY of the end point the line segment
        # note that the end point of the first segment is the start point of the second segment, and so on
        arcpy.management.AddXY(outFeat)
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
    arcpy.management.Dissolve(inLineFeat, dissolveLineFeat, dissolvedField)

    # convert line to vertices, effectively identify the start and end points of the profiles
    outVerticeFeat1 = "dissolveLineFeat_vertices1"
    itemList.append(outVerticeFeat1)
    arcpy.management.FeatureVerticesToPoints(
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
    arcpy.analysis.Statistics(depthFeat1, outTab1, statField, caseField)

    # densify line features so that we have more points along the profile
    distance = "10 Meters"
    arcpy.edit.Densify(dissolveLineFeat, "DISTANCE", distance)

    # convert line to vertices
    outVerticeFeat2 = "dissolveLineFeat_vertices2"
    itemList.append(outVerticeFeat2)
    arcpy.management.FeatureVerticesToPoints(
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
    arcpy.analysis.Statistics(depthFeat2, outTab2, statField, caseField)

    # call the helper function to calculate mean_segment_Slope
    outFeat1 = "outFeat_selected_final"
    itemList.append(outFeat1)
    meanSlope = calculate_segmentSlope(
        depthFeat2, outTab2, dissolveLineFeat, headFeat, footFeat, outFeat1
    )

    # calculate distance of the minimum depth point of each profile to the feature head
    arcpy.analysis.Near(outFeat1, headFeat)

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
            arcpy.management.AddField(
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
    arcpy.management.CalculateField(
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
    arcpy.management.CalculateField(
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
    nuLines = int(arcpy.management.GetCount(dissolveLineFeat).getOutput(0))
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
    arcpy.management.Dissolve(inLineFeat, dissolveLineFeat, dissolvedField)

    # convert line to vertices, effectively identify the start and end points of the profiles
    outVerticeFeat1 = "dissolveLineFeat_vertices1"
    itemList.append(outVerticeFeat1)
    arcpy.management.FeatureVerticesToPoints(
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
    arcpy.analysis.Statistics(depthFeat1, outTab1, statField, caseField)

    # densify line features so that we have more points along the profile
    distance = "10 Meters"
    arcpy.edit.Densify(dissolveLineFeat, "DISTANCE", distance)

    # convert line to vertices
    outVerticeFeat2 = "dissolveLineFeat_vertices2"
    itemList.append(outVerticeFeat2)
    arcpy.management.FeatureVerticesToPoints(
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
    arcpy.analysis.Statistics(depthFeat2, outTab2, statField, caseField)

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
    arcpy.management.MinimumBoundingGeometry(
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
            arcpy.management.AddField(
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
    arcpy.management.PolygonToLine(splitFeatClass, lineFeatClass1)
    arcpy.AddMessage("polygon to line done")
    # selection
    lineFeatClass2 = workspace + "/" + "lineFeatClass2"
    itemList.append(lineFeatClass2)
    whereClause = "LEFT_FID <> -1"
    arcpy.analysis.Select(lineFeatClass1, lineFeatClass2, whereClause)
    arcpy.AddMessage("selection done")
    # spatial join
    lineFeatClass3 = workspace + "/" + "lineFeatClass3"
    itemList.append(lineFeatClass3)
    arcpy.analysis.SpatialJoin(
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
    arcpy.analysis.Statistics(lineFeatClass3, outTab1, statsField, caseField)

    outTab2 = "outTab2"
    itemList.append(outTab2)
    statsField = [["SUM_Shape_Length", "MEAN"]]
    caseField = "featID"
    arcpy.analysis.Statistics(outTab1, outTab2, statsField, caseField)
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
    arcpy.management.FeatureVerticesToPoints(inFeatClass, inFeatVertices, "ALL")
    arcpy.AddMessage("feature vertices to points done")

    # add x and y
    arcpy.management.AddXY(inFeatVertices)
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

    arcpy.management.CopyRows(inFeatVertices, csvFile1)
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
    arcpy.analysis.Select(inFeatVertices, pointFeat1, whereClause)
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
    arcpy.management.MosaicToNewRaster(
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
    arcpy.management.Copy(pointFeat1, pointFeat2)
    arcpy.management.CopyRows(pointFeat2, csvFile2)
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
    arcpy.analysis.Select(pointFeat1, headFeatClass, whereClause)
    # generate foot featureclass
    text = "("
    for i in footList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    arcpy.analysis.Select(pointFeat1, footFeatClass, whereClause)
    arcpy.AddMessage("generate head and foot features done")

    # generate first points featureclass
    text = "("
    for i in firstList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    firstFeatClass = workspace + "/" + "firstPoints"
    itemList.append(firstFeatClass)
    arcpy.analysis.Select(pointFeat1, firstFeatClass, whereClause)
    # generate last points featureclass
    text = "("
    for i in lastList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    lastFeatClass = workspace + "/" + "lastPoints"
    itemList.append(lastFeatClass)
    arcpy.analysis.Select(pointFeat1, lastFeatClass, whereClause)
    arcpy.AddMessage("generate first and last points features done")

    # polygon to point
    pointFeat2 = workspace + "/" + "pointFeat2"
    itemList.append(pointFeat2)
    # Use FeatureToPoint function to find a point inside each part
    arcpy.management.FeatureToPoint(splitFeatClass, pointFeat2, "CENTROID")
    arcpy.AddMessage("feature to point done")

    # sort the points
    pointFeat2_1 = workspace + "/" + "pointFeat2_1"
    itemList.append(pointFeat2_1)
    pointFeat2_2 = workspace + "/" + "pointFeat2_2"
    itemList.append(pointFeat2_2)
    arcpy.management.Sort(pointFeat2, pointFeat2_1, [["ORIG_FID", "ASCENDING"]])
    arcpy.management.Sort(pointFeat2, pointFeat2_2, [["ORIG_FID", "DESCENDING"]])

    # add x and y
    arcpy.management.AddXY(pointFeat2_1)
    arcpy.management.AddXY(pointFeat2_2)
    print("Add x and y done")

    # merge the first point, the centre points of each sub-polygon, then the last point
    mergedFeats = [firstFeatClass, pointFeat2_1, lastFeatClass]
    mergedFeat1_1 = workspace + "/" + "merged_points1_1"
    itemList.append(mergedFeat1_1)
    arcpy.management.Merge(mergedFeats, mergedFeat1_1)

    mergedFeats = [firstFeatClass, pointFeat2_2, lastFeatClass]
    mergedFeat1_2 = workspace + "/" + "merged_points1_2"
    itemList.append(mergedFeat1_2)
    arcpy.management.Merge(mergedFeats, mergedFeat1_2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat1_1 = "curveLine1"
    itemList.append(lineFeat1_1)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.management.PointsToLine(mergedFeat1_1, lineFeat1_1, lineField, sortField)
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
    arcpy.management.PointsToLine(mergedFeat1_2, lineFeat1_2, lineField, sortField)
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
    arcpy.management.Merge(mergedFeats, mergedCurveFeat)
    arcpy.AddMessage("merged curves done")

    # summary statistics
    # in order to select the shorter curveline
    outTab3 = "outTab3"
    itemList.append(outTab3)
    statsField = [["Shape_Length", "MIN"]]
    caseField = ["featID"]
    arcpy.analysis.Statistics(mergedCurveFeat, outTab3, statsField, caseField)

    # merge to create a straight line connecting the first
    # and last point in order to calculate the straight length (head to foot length)
    mergedFeats = [firstFeatClass, lastFeatClass]
    mergedFeat2 = workspace + "/" + "merged_points2"
    itemList.append(mergedFeat2)
    arcpy.management.Merge(mergedFeats, mergedFeat2)
    arcpy.AddMessage("merged done")

    # point to line
    lineFeat2 = "straightLine"
    itemList.append(lineFeat2)
    lineField = "featID"
    sortField = "OBJECTID"
    # Execute PointsToLine
    arcpy.management.PointsToLine(mergedFeat2, lineFeat2, lineField, sortField)
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
    arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")
    arcpy.AddMessage("calculate Sinuosity field done")
    field = "LengthWidthRatio"
    expression = "!sinuous_length! / !mean_width!"
    arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")
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
            arcpy.management.Compact(
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
                arcpy.analysis.Select(lineFeatClass3, lineFeatClass4, whereClause)
                dissolveLineFeat = workspace + "/" + "lineFeatClass4_dissolved"

                headFeat1 = workspace + "/" + "headFeat1"
                footFeat1 = workspace + "/" + "footFeat1"
                arcpy.analysis.Select(headFeatClass, headFeat1, whereClause)
                arcpy.analysis.Select(footFeatClass, footFeat1, whereClause)
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
                arcpy.analysis.Select(lineFeatClass3, lineFeatClass4, whereClause)
                dissolveLineFeat = workspace + "/" + "lineFeatClass4_dissolved"

                headFeat1 = workspace + "/" + "headFeat1"
                footFeat1 = workspace + "/" + "footFeat1"
                arcpy.analysis.Select(headFeatClass, headFeat1, whereClause)
                arcpy.analysis.Select(footFeatClass, footFeat1, whereClause)
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
    arcpy.management.FeatureToPoint(inFeat, centreFeat, "CENTROID")
    tempLayer = "tempLayer"
    itemList.append(tempLayer)
    arcpy.management.MakeFeatureLayer(centreFeat, tempLayer)
    # if the centre point is not inside the polygon
    # (e.g., in case of a multipart feature after using the connection tools)
    # we need to force it
    arcpy.management.SelectLayerByLocation(tempLayer, "WITHIN", inFeat)

    matchcount = int(arcpy.management.GetCount(tempLayer)[0])
    if matchcount == 0:
        arcpy.management.FeatureToPoint(inFeat, centreFeat, "INSIDE")
    arcpy.AddMessage("centre point generated")
    # add x and y
    arcpy.management.AddXY(centreFeat)
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

    arcpy.management.XYToLine(
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
        arcpy.analysis.Select(lineFC, sFeat, whereClause)
        # intersect each profile with the feature polygon
        fcList = [sFeat, inFeat]
        lineFC1 = "lineFC1"
        arcpy.analysis.Intersect(fcList, lineFC1, "ALL", "", "LINE")

        # convert profile line to profile points along the line
        # normally, the lineFC1 should only have one feature, but occasionally
        # it has 2 or more features due to the default cluster tolerance setting in the above intersect analysis
        # the following codes obtain the length of the main line
        nuLines = int(arcpy.management.GetCount(lineFC1).getOutput(0))
        if nuLines < 1:  # if lineFC1 has no feature, skip this profile
            arcpy.management.Delete(sFeat)
            arcpy.management.Delete(lineFC1)
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
            arcpy.edit.Densify(lineFC1, "DISTANCE", str(dist) + " Meters")
            # add an ID field
            fieldType = "LONG"
            fieldPrecision = 10
            fieldName = "profileID"
            arcpy.management.AddField(lineFC1, fieldName, fieldType, fieldPrecision)
            expression = oID
            arcpy.management.CalculateField(
                lineFC1, fieldName, expression, "PYTHON3"
            )

            arcpy.management.FeatureVerticesToPoints(lineFC1, pointFC, "ALL")
            # spatial sort
            sort_fields = [["Shape", "ASCENDING"]]
            # Use UR algorithm
            sort_method = "UR"
            arcpy.management.Sort(pointFC, pointFC1, sort_fields, sort_method)

            arcpy.management.Delete(sFeat)
            arcpy.management.Delete(lineFC1)
            arcpy.management.Delete(pointFC)

    del cursor, row

    arcpy.management.Merge(mergeFCList, outPointFeat)
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
    arcpy.management.FeatureVerticesToPoints(rectangleFeat, MbrPoints, "ALL")
    arcpy.AddMessage("bounding to points done")
    # add x and y
    arcpy.management.AddXY(MbrPoints)
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

    arcpy.management.CreateFishnet(
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
            arcpy.analysis.Select(fishnetFeat, sFeat, whereClause)
            fcList = [sFeat, inFeat]
            lineFC1 = "lineFC1"

            arcpy.analysis.Intersect(fcList, lineFC1, "ALL", "", "LINE")

            # normally, the lineFC1 should only have one feature, but occasionally
            # it has 0 feature due to intersecting with a point or not intersecting the feature at all
            # (e.g., in case of the feature is linearly connected multipart feature)
            # or >=2 features due to the default cluster tolerance setting in the above intersect analysis
            # the following codes obtain the length of the main line
            nuLines = int(arcpy.management.GetCount(lineFC1).getOutput(0))
            noFeat1 += nuLines

            if nuLines < 1:  # if lineFC1 has no feature, skip this profile
                arcpy.management.Delete(sFeat)
                arcpy.management.Delete(lineFC1)
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
                arcpy.edit.Densify(lineFC1, "DISTANCE", str(dist) + " Meters")

                # add an ID field
                fieldType = "LONG"
                fieldPrecision = 10
                fieldName = "profileID"
                arcpy.management.AddField(
                    lineFC1, fieldName, fieldType, fieldPrecision
                )
                expression = oID
                arcpy.management.CalculateField(
                    lineFC1, fieldName, expression, "PYTHON3"
                )

                arcpy.management.FeatureVerticesToPoints(lineFC1, pointFC, "ALL")
                # spatial sort
                sort_fields = [["Shape", "ASCENDING"]]
                # Use UR algorithm
                sort_method = "UR"
                arcpy.management.Sort(pointFC, pointFC1, sort_fields, sort_method)

                arcpy.management.Delete(sFeat)
                arcpy.management.Delete(lineFC1)
                arcpy.management.Delete(pointFC)

    del cursor, row

    if noFeat1 > 0:
        arcpy.AddMessage(
            str(noFeat1) + " cross-section profiles have actually been created."
        )
        arcpy.management.Merge(mergeFCList, outPointFeat)
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
    arcpy.management.FeatureToPoint(inFeat, centreFeat, "CENTROID")

    tempLayer = "tempLayer"
    itemList.append(tempLayer)
    arcpy.management.MakeFeatureLayer(centreFeat, tempLayer)
    # if the centre point is not inside the polygon
    # (e.g., in case of a multipart feature after using the connection tools)
    # we need to force it
    arcpy.management.SelectLayerByLocation(tempLayer, "WITHIN", inFeat)

    matchcount = int(arcpy.management.GetCount(tempLayer)[0])
    if matchcount == 0:
        arcpy.management.FeatureToPoint(inFeat, centreFeat, "INSIDE")
    arcpy.AddMessage("centre point generated")
    # add x and y
    arcpy.management.AddXY(centreFeat)
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

    arcpy.management.XYToLine(
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
        arcpy.analysis.Select(lineFC, sFeat, whereClause)
        # intersect each profile with the feature polygon
        fcList = [sFeat, inFeat]
        lineFC1 = "lineFC1"

        arcpy.analysis.Intersect(fcList, lineFC1, "ALL", "", "LINE")

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
        arcpy.edit.Densify(lineFC1, "DISTANCE", str(dist) + " Meters")
        # add an ID field
        fieldType = "LONG"
        fieldPrecision = 10
        fieldName = "profileID"
        arcpy.management.AddField(lineFC1, fieldName, fieldType, fieldPrecision)
        expression = oID
        arcpy.management.CalculateField(
            lineFC1, fieldName, expression, "PYTHON3"
        )

        arcpy.management.FeatureVerticesToPoints(lineFC1, pointFC, "ALL")
        # spatial sort
        sort_fields = [["Shape", "ASCENDING"]]
        # Use UR algorithm
        sort_method = "UR"
        arcpy.management.Sort(pointFC, pointFC1, sort_fields, sort_method)

        arcpy.management.Delete(sFeat)
        arcpy.management.Delete(lineFC1)
        arcpy.management.Delete(pointFC)

    del cursor, row

    arcpy.management.Merge(mergeFCList, outPointFeat)
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
    arcpy.management.Sort(inPoints, sortFeat, sortField)
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
    arcpy.management.XYToLine(
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

    arcpy.management.Dissolve(lineFeat, outLines, lineField)
    arcpy.management.Delete(sortFeat)
    arcpy.management.Delete(csvFile)
    arcpy.management.Delete(lineFeat)

    return

# This function creates temporary workspaces and folders, splits the input featureclass into subsets,
# and copies a subset and input bathymetry grid into each workspace
def splitFeat(workspace, inFeat, inBathy, noSplit):
    # workspace: the input workspace which contains the inFeat and inBathy
    # inFeat: input featureclass of bathymetric high or low features
    # inBathy: input bathymetry grid
    # noSplit: number of subsets to split

    noFeat = int(arcpy.management.GetCount(inFeat).getOutput(0))
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
        arcpy.management.CreateFileGDB(path, gdbName)
        arcpy.AddMessage(gdbName + ' created')

        # copy inBathy
        data1 = path + '/' + gdbName + '/' + inBathy
        bathyList.append(data1)
        arcpy.management.Copy(inBathy, data1)
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
        arcpy.management.CreateFolder(path, folderName)
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
            arcpy.management.DeleteField(inFeatClass, field)

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
    arcpy.management.MosaicToNewRaster(
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
    arcpy.management.MinimumBoundingGeometry(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    arcpy.AddMessage("bounding rectangle generated")
    noFeat = int(arcpy.management.GetCount(inFeatClass).getOutput(0))
    noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
    arcpy.AddMessage("noFeat: " + str(noFeat))
    arcpy.AddMessage("noRectangle: " + str(noRectangle))
    # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
    # if not, regenerate the bounding rectangle up to three times
    if noRectangle < noFeat:
        arcpy.management.MinimumBoundingGeometry(
            inFeatClass,
            MbrFeatClass,
            "RECTANGLE_BY_WIDTH",
            "NONE",
            "",
            "MBG_FIELDS",
        )
        noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
        if noRectangle < noFeat:
            arcpy.management.MinimumBoundingGeometry(
                inFeatClass,
                MbrFeatClass,
                "RECTANGLE_BY_WIDTH",
                "NONE",
                "",
                "MBG_FIELDS",
            )
            noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
            if noRectangle < noFeat:
                arcpy.management.MinimumBoundingGeometry(
                    inFeatClass,
                    MbrFeatClass,
                    "RECTANGLE_BY_WIDTH",
                    "NONE",
                    "",
                    "MBG_FIELDS",
                )
                noRectangle = int(
                    arcpy.management.GetCount(MbrFeatClass).getOutput(0)
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
            arcpy.management.Compact(
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
            arcpy.analysis.Select(inFeatClass, inFeat, whereClause)

            boundFeat = workspaceName + "/" + "boundFeat_" + str(featID)
            itemList.append(boundFeat)

            # select the feature
            arcpy.analysis.Select(MbrFeatClass, boundFeat, whereClause)

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
            arcpy.management.AddXY(profilePointFC1)
            arcpy.AddMessage("Add x and y done")
            # export the table to a csv file
            outCSV = tempFolder + "/" + "profilePointFC1.csv"
            itemList.append(outCSV)
            # delete schema.ini which may contains incorrect data types (2023-04-20)
            schemaFile = tempFolder + "/" + "schema.ini"
            if os.path.isfile(schemaFile):
                os.remove(schemaFile)

            arcpy.management.CopyRows(profilePointFC1, outCSV)
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
                    arcpy.management.AddField(
                        inFeat, field, fieldType, field_length=fieldLength
                    )

            arcpy.AddMessage("profile fields added")

            # calculate fields
            i = 0
            for field in fieldList:
                # calculate string to a text field, the string must be enclosed by double quote
                expression = '"' + valueList[i] + '"'
                arcpy.management.CalculateField(
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
    arcpy.management.Merge(mergeList, mergedFeat)
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
            arcpy.management.DeleteField(inFeatClass, field)

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
    arcpy.management.MosaicToNewRaster(
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
    arcpy.management.MinimumBoundingGeometry(
        inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
    )
    noFeat = int(arcpy.management.GetCount(inFeatClass).getOutput(0))
    noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
    arcpy.AddMessage("noFeat: " + str(noFeat))
    arcpy.AddMessage("noRectangle: " + str(noRectangle))
    # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
    # if not, regenerate the bounding rectangle up to three times
    if noRectangle < noFeat:
        arcpy.management.MinimumBoundingGeometry(
            inFeatClass,
            MbrFeatClass,
            "RECTANGLE_BY_WIDTH",
            "NONE",
            "",
            "MBG_FIELDS",
        )
        noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
        if noRectangle < noFeat:
            arcpy.management.MinimumBoundingGeometry(
                inFeatClass,
                MbrFeatClass,
                "RECTANGLE_BY_WIDTH",
                "NONE",
                "",
                "MBG_FIELDS",
            )
            noRectangle = int(arcpy.management.GetCount(MbrFeatClass).getOutput(0))
            if noRectangle < noFeat:
                arcpy.management.MinimumBoundingGeometry(
                    inFeatClass,
                    MbrFeatClass,
                    "RECTANGLE_BY_WIDTH",
                    "NONE",
                    "",
                    "MBG_FIELDS",
                )
                noRectangle = int(
                    arcpy.management.GetCount(MbrFeatClass).getOutput(0)
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
            arcpy.management.Compact(
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
            arcpy.analysis.Select(inFeatClass, inFeat, whereClause)

            boundFeat = workspaceName + "/" + "boundFeat_" + str(featID)
            itemList.append(boundFeat)

            # select the feature
            arcpy.analysis.Select(MbrFeatClass, boundFeat, whereClause)

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
            arcpy.management.AddXY(profilePointFC1)
            arcpy.AddMessage("Add x and y done")
            # export the table to a csv file
            outCSV = tempFolder + "/" + "profilePointFC1.csv"
            itemList.append(outCSV)
            # delete schema.ini which may contains incorrect data types (2023-04-20)
            schemaFile = tempFolder + "/" + "schema.ini"
            if os.path.isfile(schemaFile):
                os.remove(schemaFile)

            arcpy.management.CopyRows(profilePointFC1, outCSV)
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
                    arcpy.management.AddField(
                        inFeat, field, fieldType, field_length=fieldLength
                    )

            arcpy.AddMessage("profile fields added")

            # calculate fields
            i = 0
            for field in fieldList:
                # calculate string to a text field, the string must be enclosed by double quote
                expression = '"' + valueList[i] + '"'
                arcpy.management.CalculateField(
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
    arcpy.management.Merge(mergeList, mergedFeat)
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

# This function calculates topographic attributes for bathymetric high features
def calculateTopographicBH(workspaceName, tempFolder, inFeat, inBathy, slpGrid, saGrid):
    
    env.workspace = workspaceName
    env.overwriteOutput = True
    itemList = []
    
    
    fieldList = [
        "minDepth",
        "maxDepth",
        "depthRange",
        "meanDepth",
        "stdDepth",
        "medianDepth",
        "relativeHeight",
        "minGradient",
        "maxGradient",
        "gradientRange",
        "meanGradient",
        "stdGradient",
        "medianGradient",
        "surfaceArea",
        "volume",
        "sArea",
    ]

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    # add new topographic fields
    for field in fieldList:
        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        if field in field_names:
            arcpy.AddMessage(field + " exists")
        else:
            arcpy.management.AddField(
                inFeat, field, fieldType, fieldPrecision, fieldScale
            )

    # zonal statistics
    zoneField = "featID"
    outTab1 = "outTab1"
    outTab2 = "outTab2"
    outTab3 = "outTab3"
    itemList.append(outTab1)
    itemList.append(outTab2)        
    itemList.append(outTab3)
    # The two percentile values are needed to calculate the relativeHeight attribute.
    # The relativeHeight attribute is the depth difference between the 97.5th and the 2.5th percentiles.
    # The relativeHeight attribute is more appropriate than the depthRange attribute in classifying Seamount, Pinnacle, Knoll and Hills (Dolan and Bjarnadottir, 2025).
    # This is because the depthRange attribute is more likely affected by bathymetry data uncertainty.
    # Dolan MFJ and Bjarnadóttir LR (2025) Seamounts and related topographic highs – automated mapping in support of sustainable ocean management, Norway. Front. Earth Sci. 13:1690996. doi: 10.3389/feart.2025.1690996
    percentile_values=[2.5,97.5]
    outZ1 = ZonalStatisticsAsTable(
        inFeat, zoneField, inBathy, outTab1, "DATA", "ALL", percentile_values=percentile_values
    )
    outZ2 = ZonalStatisticsAsTable(
        inFeat, zoneField, slpGrid, outTab2, "DATA", "ALL"
    )
    outZ3 = ZonalStatisticsAsTable(
        inFeat, zoneField, saGrid, outTab3, "DATA", "ALL"
    )

    # calculate these topographic fields
    field = "minDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MIN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "maxDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MAX" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "depthRange"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "RANGE" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "meanDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MEAN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "stdDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "STD" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "medianDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MEDIAN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "relativeHeight"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "PCT97_5" + "!" + " - " + "!" + outTab1 + "." + "PCT2_5" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)
            

    field = "minGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MIN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "maxGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MAX" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "gradientRange"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "RANGE" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "meanGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MEAN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "stdGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "STD" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "medianGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MEDIAN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "surfaceArea"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab3 + "." + "SUM" + "!"
    HelperFunctions.addField(inFeat, outTab3, field, inID, joinID, expression)
    # calculate volume and surface area using 3D extension
    # The function is unable to calculate volume and surface area for very small (narrow) features
    # The estimated volume and surface area values are more accurate for large features
    
    csvFile = tempFolder + "/" + "volume.csv"
    itemList.append(csvFile)
    calculateVolume(inBathy, inFeat, 1, csvFile, workspaceName)

    outTab4 = "outTab4"
    itemList.append(outTab4)
    arcpy.conversion.ExportTable(csvFile, outTab4)

    field = "volume"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab4 + "." + "Volume" + "!"
    HelperFunctions.addField(inFeat, outTab4, field, inID, joinID, expression)

    field = "sArea"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab4 + "." + "SArea" + "!"
    HelperFunctions.addField(inFeat, outTab4, field, inID, joinID, expression)

    arcpy.AddMessage("All attributes added")
    # delete intermediate files
    HelperFunctions.deleteDataItems(itemList)

   
    
# This function calculates topographic attributes for bathymetric low features
def calculateTopographicBL(workspaceName, tempFolder, inFeat, headFeat, footFeat, inBathy, slpGrid, saGrid):
    
    env.workspace = workspaceName
    env.overwriteOutput = True
    itemList = []
    
    
    fieldList = [
        "headDepth",
        "footDepth",
        "head_foot_depthRange",
        "head_foot_gradient",
        "minDepth",
        "maxDepth",
        "depthRange",
        "meanDepth",
        "stdDepth",
        "medianDepth",
        "relativeDepth",
        "minGradient",
        "maxGradient",
        "gradientRange",
        "meanGradient",
        "stdGradient",
        "medianGradient",
        "surfaceArea",
        "volume",
        "sArea",
    ]
    
    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    # add new topographic fields
    for field in fieldList:
        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        if field in field_names:
            arcpy.AddMessage(field + " exists")
        else:
            arcpy.management.AddField(
                inFeat, field, fieldType, fieldPrecision, fieldScale
            )

    # zonal statistics
    zoneField = "featID"
    outTab1 = "outTab1"
    outTab2 = "outTab2"
    outTab3 = "outTab3"
    itemList.append(outTab1)
    itemList.append(outTab2)        
    itemList.append(outTab3)
    # The two percentile values are needed to calculate the relativeDepth attribute.
    # The relativeDepth attribute is the depth difference between the 97.5th and the 2.5th percentiles.
    # The relativeDepth attribute may be more appropriate than the depthRange attribute because the depthRange attribute is more likely affected by bathymetry data uncertainty.
    percentile_values=[2.5,97.5]
    outZ1 = ZonalStatisticsAsTable(
        inFeat, zoneField, inBathy, outTab1, "DATA", "ALL", percentile_values=percentile_values
    )
    outZ2 = ZonalStatisticsAsTable(
        inFeat, zoneField, slpGrid, outTab2, "DATA", "ALL"
    )
    outZ3 = ZonalStatisticsAsTable(
        inFeat, zoneField, saGrid, outTab3, "DATA", "ALL"
    )

    # calculate these fields
    field = "minDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MIN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "maxDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MAX" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "depthRange"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "RANGE" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "meanDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MEAN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "stdDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "STD" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "medianDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "MEDIAN" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "relativeDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab1 + "." + "PCT97_5" + "!" + " - " + "!" + outTab1 + "." + "PCT2_5" + "!"
    HelperFunctions.addField(inFeat, outTab1, field, inID, joinID, expression)

    field = "minGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MIN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "maxGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MAX" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "gradientRange"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "RANGE" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "meanGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MEAN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "stdGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "STD" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "medianGradient"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab2 + "." + "MEDIAN" + "!"
    HelperFunctions.addField(inFeat, outTab2, field, inID, joinID, expression)

    field = "surfaceArea"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab3 + "." + "SUM" + "!"
    HelperFunctions.addField(inFeat, outTab3, field, inID, joinID, expression)

    # spatial join
    joinFeat1 = "joinFeat1"
    itemList.append(joinFeat1)
    arcpy.analysis.SpatialJoin(inFeat, headFeat, joinFeat1)

    joinFeat2 = "joinFeat2"
    itemList.append(joinFeat2)
    arcpy.analysis.SpatialJoin(inFeat, footFeat, joinFeat2)

    # selection analysis
    selectFeat1 = "selectFeat1"
    itemList.append(selectFeat1)
    whereClause = '"depth" IS NULL'
    arcpy.analysis.Select(joinFeat1, selectFeat1, whereClause)

    selectFeat2 = "selectFeat2"
    itemList.append(selectFeat2)
    whereClause = '"depth" IS NOT NULL'
    arcpy.analysis.Select(joinFeat1, selectFeat2, whereClause)
    # if the depth is null, replace it with the depth1 field
    arcpy.management.CalculateField(selectFeat1, "depth", "!depth1!", "PYTHON3")
    mergedFeat1 = "mergedFeat1"
    itemList.append(mergedFeat1)
    mergedFeats = [selectFeat1, selectFeat2]
    arcpy.management.Merge(mergedFeats, mergedFeat1)

    # selection analysis
    selectFeat3 = "selectFeat3"
    itemList.append(selectFeat3)
    whereClause = '"depth" IS NULL'
    arcpy.analysis.Select(joinFeat2, selectFeat3, whereClause)

    selectFeat4 = "selectFeat4"
    itemList.append(selectFeat4)
    whereClause = '"depth" IS NOT NULL'
    arcpy.analysis.Select(joinFeat2, selectFeat4, whereClause)

    arcpy.management.CalculateField(selectFeat3, "depth", "!depth1!", "PYTHON3")
    mergedFeat2 = "mergedFeat2"
    itemList.append(mergedFeat2)
    mergedFeats = [selectFeat3, selectFeat4]
    arcpy.management.Merge(mergedFeats, mergedFeat2)

    field = "headDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + mergedFeat1 + "." + "depth" + "!"
    HelperFunctions.addField(inFeat, mergedFeat1, field, inID, joinID, expression)

    field = "footDepth"
    inID = "featID"
    joinID = "featID"
    expression = "!" + mergedFeat2 + "." + "depth" + "!"
    HelperFunctions.addField(inFeat, mergedFeat2, field, inID, joinID, expression)

    field = "head_foot_depthRange"
    expression = "!headDepth! - !footDepth!"
    arcpy.management.CalculateField(inFeat, field, expression, "PYTHON3")

    field = "head_foot_gradient"
    expression = (
        "math.degrees(math.atan(!head_foot_depthRange! / !head_foot_length!))"
    )
    arcpy.management.CalculateField(inFeat, field, expression, "PYTHON3")
    
    # calculate volume and surface area using 3D extension
    # The function is unable to calculate volume and surface area for very small (narrow) features
    # The estimated volume and surface area values are more accurate for large features
    
    csvFile = tempFolder + "/" + "volume.csv"
    itemList.append(csvFile)
    calculateVolume(inBathy, inFeat, -1, csvFile, workspaceName)

    outTab4 = "outTab4"
    itemList.append(outTab4)
    arcpy.conversion.ExportTable(csvFile, outTab4)

    field = "volume"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab4 + "." + "Volume" + "!"
    HelperFunctions.addField(inFeat, outTab4, field, inID, joinID, expression)

    field = "sArea"
    inID = "featID"
    joinID = "featID"
    expression = "!" + outTab4 + "." + "SArea" + "!"
    HelperFunctions.addField(inFeat, outTab4, field, inID, joinID, expression)

    arcpy.AddMessage("All attributes added")
    # delete intermediate files
    HelperFunctions.deleteDataItems(itemList)

   
    

# This function generate surface area grid
# The surface area grid is calculated from the bathymetry grid using Jenness (2004) algorithm
# Jenness, J.S., 2004. Calculating landscape surface area from digital elevation model. Wildlife Society Bulletin, 32, 829-839.
def calculateSurfaceArea(bathyRas, outRas, wSize, tempFolder):
    # bathyRas: input bathymetry grid
    # outRas: output surface area grid
    # wSize: kernel size for the weight files
    # tempFolder: temporary folder that stores the weight files
    
    # check the window size is an odd number
    if wSize % 2 == 0:
        messages.addErrorMessage(
            "Window size must be an odd number!"
        )
        raise arcpy.ExecuteError
    # check the window size must be greater or equal to 3
    if wSize < 3:
        messages.addErrorMessage(
            "Window size must be greater or equal to 3!"
        )
        raise arcpy.ExecuteError

    # call the helper function to generate morphological surface classes
    HelperFunctions.generateWeightFiles(tempFolder, wSize)

    rasResult = arcpy.management.GetRasterProperties(bathyRas, "CELLSIZEX")
    size = int(rasResult.getOutput(0))
    # window is the window size

    a = wSize - 1
    b = a / 2

    nu1 = int((wSize - 1) / 2)
    nu2 = -nu1
    # tempList = [[nu1, 0], [nu2, 0], [0, nu1], [0, nu2], [nu1, nu2], [nu2, nu1], [nu1, nu1], [nu2, nu2]]

    inWeight1 = tempFolder + "/weight_" + str(nu2) + str(nu2) + ".txt"
    inWeight2 = tempFolder + "/weight_0" + str(nu2) + ".txt" 
    inWeight3 = tempFolder + "/weight_" + str(nu1) + str(nu2) + ".txt"
    inWeight4 = tempFolder + "/weight_" + str(nu2) + "0.txt" 
    inWeight5 = tempFolder + "/weight_" + str(nu1) + "0.txt" 
    inWeight6 = tempFolder + "/weight_" + str(nu2) + str(nu1) + ".txt"
    inWeight7 = tempFolder + "/weight_0" + str(nu1) + ".txt" 
    inWeight8 = tempFolder + "/weight_" + str(nu1) + str(nu1) + ".txt"
    fileList = []
    fileList.append(inWeight1)
    fileList.append(inWeight2)
    fileList.append(inWeight3)
    fileList.append(inWeight4)
    fileList.append(inWeight5)
    fileList.append(inWeight6)
    fileList.append(inWeight7)
    fileList.append(inWeight8)

    NbrWeight1 = NbrWeight(inWeight1)
    NbrWeight2 = NbrWeight(inWeight2)
    NbrWeight3 = NbrWeight(inWeight3)
    NbrWeight4 = NbrWeight(inWeight4)
    NbrWeight5 = NbrWeight(inWeight5)
    NbrWeight6 = NbrWeight(inWeight6)
    NbrWeight7 = NbrWeight(inWeight7)
    NbrWeight8 = NbrWeight(inWeight8)

    focal1 = FocalStatistics(bathyRas, NbrWeight1, "SUM", "DATA")
    focal2 = FocalStatistics(bathyRas, NbrWeight2, "SUM", "DATA")
    focal3 = FocalStatistics(bathyRas, NbrWeight3, "SUM", "DATA")
    focal4 = FocalStatistics(bathyRas, NbrWeight4, "SUM", "DATA")
    focal5 = FocalStatistics(bathyRas, NbrWeight5, "SUM", "DATA")
    focal6 = FocalStatistics(bathyRas, NbrWeight6, "SUM", "DATA")
    focal7 = FocalStatistics(bathyRas, NbrWeight7, "SUM", "DATA")
    focal8 = FocalStatistics(bathyRas, NbrWeight8, "SUM", "DATA")
    
    deletedList = []
    deletedList.append("focal1")
    deletedList.append("focal2")
    deletedList.append("focal3")
    deletedList.append("focal4")
    deletedList.append("focal5")
    deletedList.append("focal6")
    deletedList.append("focal7")
    deletedList.append("focal8")

    # AB length
    outRas1 = Divide(SquareRoot(Plus(Power(Minus(focal1, focal2), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("AB done")
    # BC length
    outRas2 = Divide(SquareRoot(Plus(Power(Minus(focal2, focal3), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("BC done")
    # DE length
    outRas3 = Divide(SquareRoot(Plus(Power(Minus(focal4, bathyRas), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("DE done")
    # EF length
    outRas4 = Divide(SquareRoot(Plus(Power(Minus(bathyRas, focal5), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("EF done")
    # GH length
    outRas5 = Divide(SquareRoot(Plus(Power(Minus(focal6, focal7), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("GH done")
    # HI length
    outRas6 = Divide(SquareRoot(Plus(Power(Minus(focal7, focal8), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("HI done")
    # AD length
    outRas7 = Divide(SquareRoot(Plus(Power(Minus(focal1, focal4), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("AD done")
    # BE length
    outRas8 = Divide(SquareRoot(Plus(Power(Minus(focal2, bathyRas), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("BE done")
    # CF length
    outRas9 = Divide(SquareRoot(Plus(Power(Minus(focal3, focal5), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("CF done")
    # DG length
    outRas10 = Divide(SquareRoot(Plus(Power(Minus(focal4, focal6), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("DG done")
    # EH length
    outRas11 = Divide(SquareRoot(Plus(Power(Minus(bathyRas, focal7), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("EH done")
    # FI length
    outRas12 = Divide(SquareRoot(Plus(Power(Minus(focal5, focal8), 2), Power(Times(size, b), 2))), a)
    arcpy.AddMessage("EI done")
    # EA length
    outRas13 = Divide(
        SquareRoot(Plus(Power(Minus(bathyRas, focal1), 2), Power(Times(Times(size, b), SquareRoot(2)), 2))), a)
    arcpy.AddMessage("EA done")
    # EC length
    outRas14 = Divide(
        SquareRoot(Plus(Power(Minus(bathyRas, focal3), 2), Power(Times(Times(size, b), SquareRoot(2)), 2))), a)
    arcpy.AddMessage("EC done")
    # EG length
    outRas15 = Divide(
        SquareRoot(Plus(Power(Minus(bathyRas, focal6), 2), Power(Times(Times(size, b), SquareRoot(2)), 2))), a)
    arcpy.AddMessage("EG done")
    # EI length
    outRas16 = Divide(
        SquareRoot(Plus(Power(Minus(bathyRas, focal8), 2), Power(Times(Times(size, b), SquareRoot(2)), 2))), a)
    arcpy.AddMessage("EI done")

    # area of i triangle: EA, AB, BE
    outRas17 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas13, outRas1), outRas8), Minus(Plus(outRas13, outRas1), outRas8)),
              Minus(Plus(outRas13, outRas8), outRas1)), Minus(Plus(outRas8, outRas1), outRas13)), 16))
    arcpy.AddMessage("i done")
    # area of ii triangle: BE, BC, EC
    outRas18 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas2, outRas14), outRas8), Minus(Plus(outRas2, outRas14), outRas8)),
              Minus(Plus(outRas14, outRas8), outRas2)), Minus(Plus(outRas8, outRas2), outRas14)), 16))
    arcpy.AddMessage("ii done")
    # area of iii triangle: EA, AD, DE
    outRas19 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas13, outRas7), outRas3), Minus(Plus(outRas13, outRas7), outRas3)),
              Minus(Plus(outRas13, outRas3), outRas7)), Minus(Plus(outRas7, outRas3), outRas13)), 16))
    arcpy.AddMessage("iii done")
    # area of iv triangle: EC, CF, EF
    outRas20 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas14, outRas9), outRas4), Minus(Plus(outRas14, outRas9), outRas4)),
              Minus(Plus(outRas14, outRas4), outRas9)), Minus(Plus(outRas4, outRas9), outRas14)), 16))
    arcpy.AddMessage("iv done")
    # area of v triangle: DE, DG, EG
    outRas21 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas3, outRas10), outRas15), Minus(Plus(outRas3, outRas10), outRas15)),
              Minus(Plus(outRas3, outRas15), outRas10)), Minus(Plus(outRas10, outRas15), outRas3)), 16))
    arcpy.AddMessage("v done")
    # area of vi triangle: EF, FI, EI
    outRas22 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas4, outRas12), outRas16), Minus(Plus(outRas4, outRas12), outRas16)),
              Minus(Plus(outRas4, outRas16), outRas12)), Minus(Plus(outRas16, outRas12), outRas4)), 16))
    arcpy.AddMessage("vi done")
    # area of vii triangle: EG, EH, GH
    outRas23 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas15, outRas11), outRas5), Minus(Plus(outRas15, outRas11), outRas5)),
              Minus(Plus(outRas15, outRas5), outRas11)), Minus(Plus(outRas11, outRas5), outRas15)), 16))
    arcpy.AddMessage("vii done")
    # area of viii triangle: EH, EI, HI
    outRas24 = SquareRoot(Divide(Times(
        Times(Times(Plus(Plus(outRas11, outRas16), outRas6), Minus(Plus(outRas11, outRas16), outRas6)),
              Minus(Plus(outRas11, outRas6), outRas16)), Minus(Plus(outRas16, outRas6), outRas11)), 16))
    arcpy.AddMessage("viii done")
    # surface area
    outRas25 = Plus(
        Plus(Plus(Plus(Plus(Plus(Plus(outRas17, outRas18), outRas19), outRas20), outRas21), outRas22), outRas23),
        outRas24)
    outRas25.save(outRas)
    arcpy.AddMessage("Surface Area grid generated")

    HelperFunctions.deleteFiles(fileList)

    deletedList.append("outRas1")
    deletedList.append("outRas2")
    deletedList.append("outRas3")
    deletedList.append("outRas4")
    deletedList.append("outRas5")
    deletedList.append("outRas6")
    deletedList.append("outRas7")
    deletedList.append("outRas8")
    deletedList.append("outRas9")
    deletedList.append("outRas10")
    deletedList.append("outRas11")
    deletedList.append("outRas12")
    deletedList.append("outRas13")
    deletedList.append("outRas14")
    deletedList.append("outRas15")
    deletedList.append("outRas16")
    deletedList.append("outRas17")
    deletedList.append("outRas18")
    deletedList.append("outRas19")
    deletedList.append("outRas20")
    deletedList.append("outRas21")
    deletedList.append("outRas22")
    deletedList.append("outRas23")
    deletedList.append("outRas24")
    deletedList.append("outRas25")
    HelperFunctions.deleteDataItems(deletedList)
    arcpy.AddMessage("intermediate datasets deleted")

# This function calculate volume and surface area using 3D analyst
# This function could not calculate volume and surface area for small (narrow) features
def calculateVolume(inBathy, inFeats, direction, csvFile, workspaceName):
    # inBathy: input bathymetry grid
    # inFeats: input bathymetric high/low features
    # direction: direction for calculating volume (a value of 1 (-1) indicates volume for bathymerric high (low) features))
    # csvFile: the text file stores the volume and sArea values
    # workspaceName: workspace name

    if arcpy.CheckExtension("3D") == "Available":
        arcpy.CheckOutExtension("3D")
        print("3D Analyst license checked out successfully.")
    else:
        print("3D Analyst license is unavailable.")   
    
    time1 = datetime.now()
    # get cell size of the input bathymetry grid. make sure the grid has a quare cell
    rasResult = arcpy.management.GetRasterProperties(inBathy, "CELLSIZEX")
    cSize = int(rasResult.getOutput(0))
    # expand inBathy for 2 cells
    # so that the feaures along the edge of the bathymetry grid will have depth values 
    inBathy1 = "inBathy_1"
    HelperFunctions.expandBathy(inBathy, inBathy1, 2, workspaceName)

    # buffer the inFeats one cell outward
    bufferFeats = inFeats + "_" + str(cSize) + "m"
    arcpy.analysis.GraphicBuffer(inFeats, bufferFeats, str(cSize) + " Meters", "SQUARE", "MITER")


    path1 = workspaceName.split(".gdb")[0]
    tempFolder = path1[0: path1.rfind("/")]
    
    fil = open(csvFile, "w")
    text = "featID,Volume,SArea"
    fil.write(text + "\n")
    # loop through each feature
    cursor = arcpy.SearchCursor(inFeats)
    for row in cursor:
        featID = row.getValue("featID")
        arcpy.AddMessage("working on " + str(featID))
        outTin1 = tempFolder + "/" + "outTin1_" + str(featID)
        outTin2 = tempFolder + "/" + "outTin2_" + str(featID)
        outFeat = workspaceName + "/" + "outFeat" + str(featID)
        inFeat = workspaceName + "/" + "inFeat" + str(featID)
        inPoints = workspaceName + "/" + "inPoints" + str(featID)
        outPoints = workspaceName + "/" + "outPoints" + str(featID)
        try:
            where_clause = "featID" + " = " + str(featID)
            arcpy.analysis.Select(bufferFeats, inFeat, where_clause)
           
            # convert polygon to points
            arcpy.management.FeatureVerticesToPoints(inFeat,inPoints,"ALL")
            
            # extract depth values
            ExtractValuesToPoints(inPoints, inBathy1, outPoints)            
            
            # generate the reference surface first
            # by interpolating points along the polygon boundaries
            # the TopoToRster function would throw errors when dealing with small (narrow) features
            # this needs to be caught and skipped to next feature
            input1 = outPoints + " RASTERVALU" + " PointElevation"
            outRaster = "outTopo1"
            arcpy.ddd.TopoToRaster(input1, outRaster, cell_size=cSize, data_type="SPOT")
            outTopo = ExtractByMask(outRaster, inFeat)
            
            arcpy.AddMessage("reference surface generated")
            # convert raster to tin surface
            arcpy.ddd.RasterTin(outTopo, outTin1)
            arcpy.AddMessage("reference tin generated")
            # generate the real surface
            outExtract = ExtractByMask(inBathy1, inFeat, "INSIDE", inFeat)
            arcpy.AddMessage("real surface generated")
            arcpy.ddd.RasterTin(outExtract, outTin2)
            arcpy.AddMessage("real tin generated")
            # Volume = real surface - reference surface
            arcpy.ddd.SurfaceDifference(outTin2, outTin1, outFeat)
            arcpy.AddMessage("surface difference done")
            # get the total volume (surface area)
            # direction = 1 indicates above; direction = -1 indicates below
            cursor1 = arcpy.SearchCursor(outFeat)
            volume1 = 0
            sArea1 = 0
            for row1 in cursor1:
                code = int(row1.getValue("Code"))
                volume = float(row1.getValue("Volume"))
                sArea = float(row1.getValue("SArea"))
                if code == direction:
                    volume1 += volume
                    sArea1 += sArea
            del cursor1, row1
            text = str(featID) + "," + str(volume1) + "," + str(sArea1)
            arcpy.AddMessage(text)
            fil.write(text + "\n")
            
            arcpy.management.Delete(outTin1)
            arcpy.management.Delete(outTin2)
            arcpy.management.Delete(outFeat)
            arcpy.management.Delete(inFeat)
            arcpy.management.Delete(inPoints)
            arcpy.management.Delete(outTopo)
            arcpy.management.Delete(outExtract)
            arcpy.management.Delete(outRaster)
            arcpy.management.Delete(outPoints)
        # the TopoToRster function would throw errors when dealing with small (narrow) features
        # this needs to be caught and skipped to next feature
        except:
            print("skipping", str(featID))

            if arcpy.Exists(inFeat):
                arcpy.management.Delete(inFeat)
            if arcpy.Exists(inPoints):
                arcpy.management.Delete(inPoints)
            if arcpy.Exists(outPoints):
                arcpy.management.Delete(outPoints)
  
            continue
        
    fil.close()
    del cursor, row
    time2 = datetime.now()
    diff = time2 - time1
    arcpy.AddMessage("took " + str(diff) + " to calculate volume attributes.")

    arcpy.management.Delete(inBathy1)
    arcpy.management.Delete(bufferFeats)
    arcpy.AddMessage("Volume and sArea attributes calculated")

    arcpy.CheckInExtension("3D")
    
                
        
    
    


if __name__ == '__main__':
    arcpy.AddMessage("dummy message")
