#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: September 1, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from arcpy.sa import *
import pandas as pd
import multiprocessing
from multiprocessing import Pool
import os
import sys
import math

arcpy.CheckOutExtension("Spatial")


def execute_contour_BH(argList, method, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # method: the mapping method that is selected by the user
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    # use python window instead of ArcGIS Pro application for the multiprocessing
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        if method == 'First Derivative':
            results = pool.map(doFirstDerivativeBH, argList)
        else:
            results = pool.map(doSecondDerivativeBH, argList)

    arcpy.AddMessage("multiprocessing done all")

def execute_contour_BL(argList, method, n_cpu):
    # argList: a list of a list of arguments to be passed for multiprocessing
    # method: the mapping method that is selected by the user
    # n_cpu: number of cpu logical processors used for multiprocessing (each processor runs one independent process)

    arcpy.AddMessage(
        "Will open multiple python windows for processing. Please do not close them! They will close when finish."
    )
    # use python window instead of ArcGIS Pro application for the multiprocessing
    multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
    arcpy.AddMessage("nCPU:" + str(n_cpu))
    # doing multiprocessing here
    with Pool(n_cpu) as pool:
        if method == 'First Derivative':
            results = pool.map(doFirstDerivativeBL, argList)
        else:
            results = pool.map(doSecondDerivativeBL, argList)

    arcpy.AddMessage("multiprocessing done all")

# not used
def doSelection(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat1 = arg[1]  # merged features
    inFeat2 = arg[2]  # dissolved features
    inFeat3 = arg[3]  # joined features
    tempFolder = arg[4]  # temporary folder holding the CSV file
    outFeat = arg[5]  # output features selected from the merged features
    fieldName = "idV"
    env.workspace = workspaceName

    # looping through each selected dissolved feature
    idList = []
    cursor = arcpy.SearchCursor(inFeat2)
    i = 1
    for row in cursor:
        print("working on", str(i))
        # for each dissolved feature, select its associated joined features
        # Note that the joined features have a one-to-one relationship with the merged features,
        # They are identical spatially, only with more attributes for the joined features.
        targetID = row.getValue(fieldName)
        tempFeat = "tempFeatClass"
        whereClause = "TARGET_FID = " + str(targetID)
        arcpy.analysis.Select(inFeat3, tempFeat, whereClause)
        # get the count of selected joined features
        featCount = int(arcpy.management.GetCount(tempFeat).getOutput(0))
        print("featCount", featCount)

        if featCount < 3:  # this condition should never be satisfied
            print("skip", str(targetID))
        else:
            # For the selected merged features, each is associated with a contour value
            # get a statistics of the total area of the joined (and thus merged) features for each contour value
            tempTab = "tempTable"
            caseField = "contour"
            statField = [["Shape_Area_1", "SUM"]]
            arcpy.analysis.Statistics(tempFeat, tempTab, statField, caseField)
            # export the table as a CSV file
            csvFile = tempFolder + "/tempTab.csv"
            arcpy.conversion.ExportTable(tempTab, csvFile)
            # read the CSV file as a Pandas DataFrame
            tempPD = pd.read_csv(csvFile, sep=',', header=0)
            # get the two lists
            y = tempPD.SUM_Shape_Area_1.to_list()
            x = tempPD.contour.to_list()
            # The idea is to identify an index location within the contour list (x) and split the list into two subsets.
            # The location is identified to have the maximum area difference between two neighbouring contour values.
            # The ultimate objective is to select those merged feature(s) that have the identified contour value.
            # The boundaries of these features represent the new boundaries for the bathymetric high features.

            # calculate the area difference between two neighbouring contour values
            diff = [y[i] - y[i - 1] for i in range(1, len(y))]
            # As the diff is always a negative value, the maximum area difference is the minimum value of the diff
            # list.
            x1 = x[0:diff.index(min(diff)) + 1]
            print("x1", x1)
            x2 = x[diff.index(min(diff)) + 1:]
            print("x2", x2)
            if len(x1) > len(x2):
                contour = x1[0]
            else:
                contour = x2[0]
            # select the joined features that have the boundary contour value
            tempFeat1 = "tempFeatClass1"
            whereClause = "contour = " + str(contour)
            arcpy.analysis.Select(tempFeat, tempFeat1, whereClause)
            # The selected joined features have the required ID for the merged features
            # Select those IDs and append them to the list
            cursor1 = arcpy.SearchCursor(tempFeat1)
            for row1 in cursor1:
                outID = row1.getValue("JOIN_FID")
                print("outID", outID)
                idList.append(outID)
            del cursor1, row1
            arcpy.management.Delete(tempFeat1)
            arcpy.management.Delete(tempTab)
            arcpy.management.Delete(csvFile)

        arcpy.management.Delete(tempFeat)
        i += 1

    del cursor, row
    # Now, we can actually select the merged features using those identified IDs
    text = "("
    for i in idList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    print(whereClause)

    arcpy.analysis.Select(inFeat1, outFeat, whereClause)
    print("second selection done")

# the first derivative mapping method for mapping Bathymetric High features
def doFirstDerivativeBH(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat1 = arg[1]  # merged features
    inFeat2 = arg[2]  # dissolved features
    inFeat3 = arg[3]  # joined features
    tempFolder = arg[4]  # temporary folder holding the CSV file
    outFeat = arg[5]  # output features selected from the merged features
    fieldName = "idV"
    env.workspace = workspaceName

    # looping through each selected dissolved feature
    idList = []
    cursor = arcpy.SearchCursor(inFeat2)
    i = 1
    for row in cursor:
        print("working on", str(i))
        # for each dissolved feature, select its associated joined features
        # Note that the joined features have a one-to-one relationship with the merged features,
        # They are identical spatially, only with more attributes for the joined features.
        targetID = row.getValue(fieldName)
        tempFeat = "tempFeatClass"
        whereClause = "TARGET_FID = " + str(targetID)
        arcpy.analysis.Select(inFeat3, tempFeat, whereClause)
        # get the count of selected joined features
        featCount = int(arcpy.management.GetCount(tempFeat).getOutput(0))
        print("featCount", featCount)

        if featCount < 3:  # this condition should never be satisfied
            print("skip", str(targetID))
        else:
            # For the selected merged features, each is associated with a contour value
            # get a statistics of the total area of the joined (and thus merged) features for each contour value
            tempTab = "tempTable"
            caseField = "contour"
            statField = [["Shape_Area_1", "SUM"]]
            arcpy.analysis.Statistics(tempFeat, tempTab, statField, caseField)
            # export the table as a CSV file
            csvFile = tempFolder + "/tempTab.csv"
            arcpy.conversion.ExportTable(tempTab, csvFile)
            # read the CSV file as a Pandas DataFrame
            tempPD = pd.read_csv(csvFile, sep=',', header=0)
            # sort the data, from the shallowest to deepest
            tempPD1 = tempPD.sort_values('contour', ascending=False)
            # get the two lists
            y = tempPD1.SUM_Shape_Area_1.to_list()
            x = tempPD1.contour.to_list()
            # The idea is to identify an index location within the contour list (x) and split the list into two subsets.
            # The location is identified to have the maximum first derivative between two neighbouring contour values.
            # The ultimate objective is to select those merged feature(s) that have the identified contour value.
            # The boundaries of these features represent the new boundaries for the bathymetric high features.

            # calculate the 'slope' gradients between two neighbouring contours
            # slope is the first derivative
            diff = [math.degrees(math.atan((y[i] - y[i - 1]) / abs(x[i] - x[i-1]) / 10000)) for i in range(1, len(y))]

            x1 = x[0:diff.index(max(diff)) + 1]
            print("x1", x1)
            x2 = x[diff.index(max(diff)) + 1:]
            print("x2", x2)
            if len(x1) > len(x2):
                contour = x1[-1]
            else:
                contour = x2[-1]
            # select the joined features that have the boundary contour value
            tempFeat1 = "tempFeatClass1"
            whereClause = "contour = " + str(contour)
            arcpy.analysis.Select(tempFeat, tempFeat1, whereClause)
            # The selected joined features have the required ID for the merged features
            # Select those IDs and append them to the list
            cursor1 = arcpy.SearchCursor(tempFeat1)
            for row1 in cursor1:
                outID = row1.getValue("JOIN_FID")
                print("outID", outID)
                idList.append(outID)
            del cursor1, row1
            arcpy.management.Delete(tempFeat1)
            arcpy.management.Delete(tempTab)
            arcpy.management.Delete(csvFile)

        arcpy.management.Delete(tempFeat)
        i += 1

    del cursor, row
    # Now, we can actually select the merged features using those identified IDs
    text = "("
    for i in idList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    print(whereClause)

    arcpy.analysis.Select(inFeat1, outFeat, whereClause)
    print("second selection done")


# the first derivative mapping method for mapping Bathymetric Low features
def doFirstDerivativeBL(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat1 = arg[1]  # merged features
    inFeat2 = arg[2]  # dissolved features
    inFeat3 = arg[3]  # joined features
    tempFolder = arg[4]  # temporary folder holding the CSV file
    outFeat = arg[5]  # output features selected from the merged features
    fieldName = "idV"
    env.workspace = workspaceName

    # looping through each selected dissolved feature
    idList = []
    cursor = arcpy.SearchCursor(inFeat2)
    i = 1
    for row in cursor:
        print("working on", str(i))
        # for each dissolved feature, select its associated joined features
        # Note that the joined features have a one-to-one relationship with the merged features,
        # They are identical spatially, only with more attributes for the joined features.
        targetID = row.getValue(fieldName)
        tempFeat = "tempFeatClass"
        whereClause = "TARGET_FID = " + str(targetID)
        arcpy.analysis.Select(inFeat3, tempFeat, whereClause)
        # get the count of selected joined features
        featCount = int(arcpy.management.GetCount(tempFeat).getOutput(0))
        print("featCount", featCount)

        if featCount < 3:  # this condition should never be satisfied
            print("skip", str(targetID))
        else:
            # For the selected merged features, each is associated with a contour value
            # get a statistics of the total area of the joined (and thus merged) features for each contour value
            tempTab = "tempTable"
            caseField = "contour"
            statField = [["Shape_Area_1", "SUM"]]
            arcpy.analysis.Statistics(tempFeat, tempTab, statField, caseField)
            # export the table as a CSV file
            csvFile = tempFolder + "/tempTab.csv"
            arcpy.conversion.ExportTable(tempTab, csvFile)
            # read the CSV file as a Pandas DataFrame
            tempPD = pd.read_csv(csvFile, sep=',', header=0)
            # sort the data, from the deepest to shallowest
            tempPD1 = tempPD.sort_values('contour', ascending=True)
            # get the two lists
            y = tempPD1.SUM_Shape_Area_1.to_list()
            x = tempPD1.contour.to_list()
            # The idea is to identify an index location within the contour list (x) and split the list into two subsets.
            # The location is identified to have the maximum first derivative between two neighbouring contour values.
            # The ultimate objective is to select those merged feature(s) that have the identified contour value.
            # The boundaries of these features represent the new boundaries for the bathymetric low features.

            # calculate the 'slope' gradients between two neighbouring contours
            # slope is the first derivative
            diff = [math.degrees(math.atan((y[i] - y[i - 1]) / abs(x[i] - x[i-1]) / 10000)) for i in range(1, len(y))]

            x1 = x[0:diff.index(max(diff)) + 1]
            print("x1", x1)
            x2 = x[diff.index(max(diff)) + 1:]
            print("x2", x2)
            if len(x1) > len(x2):
                contour = x1[-1]
            else:
                contour = x2[-1]
            # select the joined features that have the boundary contour value
            tempFeat1 = "tempFeatClass1"
            whereClause = "contour = " + str(contour)
            arcpy.analysis.Select(tempFeat, tempFeat1, whereClause)
            # The selected joined features have the required ID for the merged features
            # Select those IDs and append them to the list
            cursor1 = arcpy.SearchCursor(tempFeat1)
            for row1 in cursor1:
                outID = row1.getValue("JOIN_FID")
                print("outID", outID)
                idList.append(outID)
            del cursor1, row1
            arcpy.management.Delete(tempFeat1)
            arcpy.management.Delete(tempTab)
            arcpy.management.Delete(csvFile)

        arcpy.management.Delete(tempFeat)
        i += 1

    del cursor, row
    # Now, we can actually select the merged features using those identified IDs
    text = "("
    for i in idList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    print(whereClause)

    arcpy.analysis.Select(inFeat1, outFeat, whereClause)
    print("second selection done")


# the second derivative mapping method for mapping Bathymetric High features
def doSecondDerivativeBH(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat1 = arg[1]  # merged features
    inFeat2 = arg[2]  # dissolved features
    inFeat3 = arg[3]  # joined features
    tempFolder = arg[4]  # temporary folder holding the CSV file
    outFeat = arg[5]  # output features selected from the merged features
    fieldName = "idV"
    env.workspace = workspaceName

    # looping through each selected dissolved feature
    idList = []
    cursor = arcpy.SearchCursor(inFeat2)
    i = 1
    for row in cursor:
        print("working on", str(i))
        # for each dissolved feature, select its associated joined features
        # Note that the joined features have a one-to-one relationship with the merged features,
        # They are identical spatially, only with more attributes for the joined features.
        targetID = row.getValue(fieldName)
        tempFeat = "tempFeatClass"
        whereClause = "TARGET_FID = " + str(targetID)
        arcpy.analysis.Select(inFeat3, tempFeat, whereClause)
        # get the count of selected joined features
        featCount = int(arcpy.management.GetCount(tempFeat).getOutput(0))
        print("featCount", featCount)

        if featCount < 3:  # this condition should never be satisfied
            print("skip", str(targetID))
        else:
            # For the selected merged features, each is associated with a contour value
            # get a statistics of the total area of the joined (and thus merged) features for each contour value
            tempTab = "tempTable"
            caseField = "contour"
            statField = [["Shape_Area_1", "SUM"]]
            arcpy.analysis.Statistics(tempFeat, tempTab, statField, caseField)
            # export the table as a CSV file
            csvFile = tempFolder + "/tempTab.csv"
            arcpy.conversion.ExportTable(tempTab, csvFile)
            # read the CSV file as a Pandas DataFrame
            tempPD = pd.read_csv(csvFile, sep=',', header=0)
            # sort the data from shallowest to deepest
            tempPD1 = tempPD.sort_values('contour', ascending=False)
            # get the two lists
            y = tempPD1.SUM_Shape_Area_1.to_list()
            x = tempPD1.contour.to_list()
            # The idea is to identify an index location within the contour list (x).
            # The location is identified to have the maximum second derivative between two neighbouring contour values.
            # The ultimate objective is to select those merged feature(s) that have the identified contour value.
            # The boundaries of these features represent the new boundaries for the bathymetric high features.

            # calculate the 'slope' gradients between two neighbouring contours
            # slope is the first derivative
            diff = [math.degrees(math.atan((y[i] - y[i - 1]) / abs(x[i] - x[i-1]) / 10000)) for i in range(1, len(y))]
            # calculate the slope of the slope (the second derivative)
            diff1 = [math.degrees(math.atan(diff[i] - diff[i - 1])) for i in range(1, len(diff))]
            # When there are only two contours, we will select the second contour (deeper one).
            # When there are only three contours, we will only have one second derivative value.
            # In this case, select the second contour as the feature boundary
            if len(diff) == 0:  # should not come here
                contour = x[0]
            elif len(diff) == 1:  # two contours
                contour = x[1]
            elif len(diff) == 2:  # three contours
                contour = x[1]
                # if diff1[0] > 0:
                #     contour = x[2]
                # else:
                #     contour = x[1]
            else:
                # only need the first contour group
                x1 = x[0:diff1.index(max(diff1)) + 2]
                print("x1", x1)
                contour = x1[-1]

            # select the joined features that have the boundary contour value
            tempFeat1 = "tempFeatClass1"
            whereClause = "contour = " + str(contour)
            arcpy.analysis.Select(tempFeat, tempFeat1, whereClause)
            # The selected joined features have the required ID for the merged features
            # Select those IDs and append them to the list
            cursor1 = arcpy.SearchCursor(tempFeat1)
            for row1 in cursor1:
                outID = row1.getValue("JOIN_FID")
                print("outID", outID)
                idList.append(outID)
            del cursor1, row1
            arcpy.management.Delete(tempFeat1)
            arcpy.management.Delete(tempTab)
            arcpy.management.Delete(csvFile)

        arcpy.management.Delete(tempFeat)
        i += 1

    del cursor, row
    # Now, we can actually select the merged features using those identified IDs
    text = "("
    for i in idList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    print(whereClause)

    arcpy.analysis.Select(inFeat1, outFeat, whereClause)
    print("second selection done")

# the second derivative mapping method for mapping the Bathymetric Low features-967
def doSecondDerivativeBL(arg):
    """ pass a list of arguments"""
    workspaceName = arg[0]
    inFeat1 = arg[1]  # merged features
    inFeat2 = arg[2]  # dissolved features
    inFeat3 = arg[3]  # joined features
    tempFolder = arg[4]  # temporary folder holding the CSV file
    outFeat = arg[5]  # output features selected from the merged features
    fieldName = "idV"
    env.workspace = workspaceName

    # looping through each selected dissolved feature
    idList = []
    cursor = arcpy.SearchCursor(inFeat2)
    i = 1
    for row in cursor:
        print("working on", str(i))
        # for each dissolved feature, select its associated joined features
        # Note that the joined features have a one-to-one relationship with the merged features,
        # They are identical spatially, only with more attributes for the joined features.
        targetID = row.getValue(fieldName)
        tempFeat = "tempFeatClass"
        whereClause = "TARGET_FID = " + str(targetID)
        arcpy.analysis.Select(inFeat3, tempFeat, whereClause)
        # get the count of selected joined features
        featCount = int(arcpy.management.GetCount(tempFeat).getOutput(0))
        print("featCount", featCount)

        if featCount < 3:  # this condition should never be satisfied
            print("skip", str(targetID))
        else:
            # For the selected merged features, each is associated with a contour value
            # get a statistics of the total area of the joined (and thus merged) features for each contour value
            tempTab = "tempTable"
            caseField = "contour"
            statField = [["Shape_Area_1", "SUM"]]
            arcpy.analysis.Statistics(tempFeat, tempTab, statField, caseField)
            # export the table as a CSV file
            csvFile = tempFolder + "/tempTab.csv"
            arcpy.conversion.ExportTable(tempTab, csvFile)
            # read the CSV file as a Pandas DataFrame
            tempPD = pd.read_csv(csvFile, sep=',', header=0)
            # sort the data from deepest to shallowest
            tempPD1 = tempPD.sort_values('contour', ascending=True)
            # get the two lists
            y = tempPD1.SUM_Shape_Area_1.to_list()
            x = tempPD1.contour.to_list()
            # The idea is to identify an index location within the contour list (x).
            # The location is identified to have the maximum second derivative between two neighbouring contour values.
            # The ultimate objective is to select those merged feature(s) that have the identified contour value.
            # The boundaries of these features represent the new boundaries for the bathymetric low features.

            # calculate the 'slope' gradients between two neighbouring contours
            # slope is the first derivative
            diff = [math.degrees(math.atan((y[i] - y[i - 1]) / abs(x[i] - x[i-1]) / 10000)) for i in range(1, len(y))]
            # calculate the slope of the slope (the second derivative)
            diff1 = [math.degrees(math.atan(diff[i] - diff[i - 1])) for i in range(1, len(diff))]
            # When there are only two contours, we will select the second contour (shallower one).
            # When there are only three contours, we will only have one second derivative value.
            # In this case, select the second contour as the feature boundary
            if len(diff) == 0:  # should not come here
                contour = x[0]
            elif len(diff) == 1:  # two contours
                contour = x[1]
            elif len(diff) == 2:  # three contours
                contour = x[1]
                # if diff1[0] > 0:
                #     contour = x[2]
                # else:
                #     contour = x[1]
            else:
                # only need the first contour group
                x1 = x[0:diff1.index(max(diff1)) + 2]
                print("x1", x1)
                contour = x1[-1]

            # select the joined features that have the boundary contour value
            tempFeat1 = "tempFeatClass1"
            whereClause = "contour = " + str(contour)
            arcpy.analysis.Select(tempFeat, tempFeat1, whereClause)
            # The selected joined features have the required ID for the merged features
            # Select those IDs and append them to the list
            cursor1 = arcpy.SearchCursor(tempFeat1)
            for row1 in cursor1:
                outID = row1.getValue("JOIN_FID")
                print("outID", outID)
                idList.append(outID)
            del cursor1, row1
            arcpy.management.Delete(tempFeat1)
            arcpy.management.Delete(tempTab)
            arcpy.management.Delete(csvFile)

        arcpy.management.Delete(tempFeat)
        i += 1

    del cursor, row
    # Now, we can actually select the merged features using those identified IDs
    text = "("
    for i in idList:
        text = text + str(i) + ","
    text = text[0:-1] + ")"
    whereClause = "OBJECTID IN " + text
    print(whereClause)

    arcpy.analysis.Select(inFeat1, outFeat, whereClause)
    print("second selection done")

