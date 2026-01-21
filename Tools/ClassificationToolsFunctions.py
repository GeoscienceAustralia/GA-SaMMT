#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: December 15, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
import multiprocessing
from multiprocessing import Pool
import os
import sys

arcpy.CheckOutExtension("Spatial")

# This function calls the multiprocessing module to verify Depression Feature
def execute_verify_depression(argList, n_cpu):
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
        results = pool.map(verifyDepression, argList)

    arcpy.AddMessage("multiprocessing done all")

# This function verify that a Depression Feature classified by the Classify Bathymetric Low Features Tool is
# indeed a proper Depression. In particularly, if the feature contains an enclosed contour larger than a certain size
# (determined by the areaRatioT parameter), then it is a proper Depression. Otherwise, it is an unclassified feature.
def verifyDepression(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    depressionFeat = arg[1] # features that were classified as depressions by the Classify Bathymetric Low Features Tool
    inBathy = arg[2] # the bathymetric grid of the area
    areaRatioT = arg[3] # The threshold value calculated as the ratio of the contour polygon area to the input feature area
                        # The default value is 0.1.
    maxContour = arg[4] # The maximum number of unique contours the verification process is allowed to generate
    cellSize = arg[5] # the cell size of the bathymetric grid
    outFeat = arg[6] # the output features resulted from the verification process
    env.workspace = workspaceName
    env.overwriteOutput = True
    # step through each original Depression Feature, run the verification process, and update the classification
    # either as Depression or as unclassified
    cursor = arcpy.UpdateCursor(depressionFeat)
    for row in cursor:
        # select an original Depression Feature
        oID = row.getValue("OBJECTID")
        arcpy.AddMessage('working on ' + str(oID))
        whereClause = "OBJECTID = " + str(oID)
        selectedFeat = "selectedFeat"
        arcpy.Select_analysis(depressionFeat, selectedFeat, whereClause)
        # buffer the feature, with a distance equals the cell size of the bathymetric grid
        # This is mainly used for a very small feature. If using the small feature directly, it often fails to generate
        # closed-contours; while, using the buffered feature would usually allow the generation of close-contours.
        bufferFeat = "bufferFeat"
        distance = cellSize + " Meter"
        arcpy.AddMessage(distance)
        arcpy.Buffer_analysis(selectedFeat, bufferFeat, distance)
        # extract the bathymetric grid to the extent of the buffered feature
        featBathy = ExtractByMask(inBathy, bufferFeat, "INSIDE")
        # get the minimum and maximum depth values within the extracted bathymetric grid
        result1 = arcpy.GetRasterProperties_management(featBathy, "MINIMUM")
        minDepth = round(float(result1.getOutput(0)), 2)
        result1 = arcpy.GetRasterProperties_management(featBathy, "MAXIMUM")
        maxDepth = round(float(result1.getOutput(0)), 2)
        # The verification process is an iterative process. The maximum number of the iteration is determined by the
        # maxContour parameter. The process starts with generating contours with 2 or 3 distinct contour values (j = 1).
        # The process then evaluates whether the area ratio between the largest contour polygon generated
        # above and the feature polygon is greater than the areaRationT parameter. If yes, this feature is confirmed as
        # a Depression and the process is terminated. If not, the process goes into the next iteration. If after all
        # iterations (generating maxContour + 1 unique contours), the above criterion is still not satisfied,
        # the feature is classified as unclassified and the process is terminated.

        # It should be noted that a larger maxContour parameter generally requires more time to complete. But it would
        # usually result in more reliable results.
        featContour = "featContour"
        j = 1
        classV = "unclassified"
        # starts the iterative verification process
        while j < (maxContour + 1):
            # calculate the contourInt parameter for the Contour tool
            contourInt = round((maxDepth - minDepth) / (j + 1), 2)
            # call the contour tool to generate contours within the extracted bathymetric grid
            Contour(featBathy, featContour, contourInt, maxDepth)
            # adding a "contour1" field to get around the rounding issue
            fieldType = "DOUBLE"
            fieldPrecision = 15
            fieldScale = 6
            fieldName = "contour1"
            arcpy.AddField_management(featContour, fieldName, fieldType, fieldPrecision, fieldScale)
            # rounding float number to two decimal place
            codeblock = """
def roundNumber(a):
    b = round(a,2)
    return b
                        """
            expression = "roundNumber(!contour!)"
            arcpy.CalculateField_management(
                featContour, fieldName, expression, "PYTHON3", codeblock
            )
            # get the polygon area of the feature
            cursor2 = arcpy.SearchCursor(selectedFeat)
            row2 = cursor2.next()
            featArea = float(row2.getValue("SHAPE_AREA"))
            # select the contour polygon with the largest area and get its area value
            i = 1
            # create an empty 1-d array to store the values of the contour polygon areas
            arr = np.empty(0)
            while i < (j + 1):
                # select a set of contours with a distinct contour value
                selectedContour = round(maxDepth - i * contourInt, 2)
                whereClause = "contour1 = " + str(selectedContour)
                contourFeat = "contourFeat"
                arcpy.Select_analysis(featContour, contourFeat, whereClause)
                # convert these contours to polygons
                contourPoly = contourFeat + "_poly"
                arcpy.FeatureToPolygon_management(contourFeat, contourPoly)
                # clip the contour polygon with the feature polygon, to make sure the contour polygon either intersects
                # or within the feature polygon
                clipPoly = "clipPoly"
                arcpy.Clip_analysis(contourPoly, selectedFeat, clipPoly)

                nuFeat = int(arcpy.GetCount_management(clipPoly).getOutput(0))
                if nuFeat > 0: # at least one contour polygon either intersects or is within the feature polygon
                    # do a dissolve so that we deal with only one polygon
                    dissolveFeat = "dissolveFeat"
                    arcpy.Dissolve_management(clipPoly, dissolveFeat)
                    # get the area of the contour polygon
                    cursor1 = arcpy.SearchCursor(dissolveFeat)
                    row1 = cursor1.next()
                    area1 = float(row1.getValue("SHAPE_AREA"))
                    # add the area value to the array
                    arr = np.append(arr, area1)
                    del cursor1, row1
                else:
                    # else, add NaN to the array
                    arr = np.append(arr, np.NaN)

                i += 1
            del cursor2, row2
            # get the maximum polygon area of the contour polygons
            contourArea = np.nanmax(arr)
            # evaluate whether the maximum contour polygon area satisfies the ratio criterion
            # if yes, terminate the process; if not, continue to the next iteration
            if contourArea >= featArea * areaRatioT:
                classV = "Depression"
                arcpy.AddMessage("This is a depression")
                break
            else:
                j += 1
        # if all iterations fail the criterion, the feature is deemed unclassified
        # we then update the classification
        if classV == "unclassified":
            arcpy.AddMessage("This is unclassified")
            row.setValue("Morphology_feature", "unclassified")
            cursor.updateRow(row)
        arcpy.AddMessage("The verification process conducts in total " + str(j) + " evaluation iterations")

    del cursor, row
    # copy the updated depression features to the output features
    arcpy.Copy_management(depressionFeat, outFeat)

    return
