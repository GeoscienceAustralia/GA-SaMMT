#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: November 21, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import math
import warnings
from datetime import datetime

import arcpy
import numpy as np
from arcpy.sa import *


# This function converts comma decimal separator (e.g., European standard) to dot (e.g.,US, UK and Australian standard)
def convertDecimalSeparator(inText):
    # inText: input string representing a decimal number
    textList = inText.split(",")
    inText1 = textList[0] + "." + textList[1]
    return inText1

# This function converts backslash (accepted through the ArcGIS tool) to forwardslash (needed in python script) in a path
def convert_backslash_forwardslash(inText):
    # inText: input path

    inText = rf"{inText}"
    if inText.find("\t"):
        inText = inText.replace("\t", "\\t")
    elif inText.find("\n"):
        inText = inText.replace("\n", "\\n")
    elif inText.find("\r"):
        inText = inText.replace("\r", "\\r")

    inText = inText.replace("\\", "/")
    return inText

# This function calculate TPI values from a bathymetry grid
def calculateTPI(bathy, radius, tpiRas):
    # bathy: input bathymetry grid
    # radius: the input radius value of a circle window
    # tpiRas: output TPI grid

    time1 = datetime.now()
    neighborhood = NbrCircle(radius, "CELL")
    outFocal = FocalStatistics(bathy, neighborhood, "MEAN", "DATA")
    # TPI equals to the difference between the value of the centre cell and the mean value of its neighbourhood
    outMinus = Minus(bathy, outFocal)
    outMinus.save(tpiRas)
    arcpy.AddMessage("TPI is done")
    time2 = datetime.now()
    diff = time2 - time1
    arcpy.AddMessage("took " + str(diff) + " to generate TPI.")
    return

# This function selects part of the raster based on a threshold value
def selectRaster(inRas, outRas, threshold, sign, value=1):
    # inRas: input raster
    # outRas: output raster
    # threshold: input threshold value used to select the inRas
    # sign: sign as part of the selection condition
    # value: the new raster value assigned to the part of the raster that satisfies the condition

    if sign == ">=":
        conDo = Con((Raster(inRas) >= threshold), value)
    elif sign == "<=":
        conDo = Con((Raster(inRas) <= threshold), value)
    conDo.save(outRas)

# This function deletes all intermediate data items
def deleteDataItems(inDataList):
    # inDataList: a list of data items to be deleted

    if len(inDataList) == 0:
        arcpy.AddMessage("no data item in the list")

    else:
        for item in inDataList:
            arcpy.AddMessage("Deleting " + item)
            arcpy.Delete_management(item)
    return

# This function deletes all unnecessary fields from the input featureclass
def deleteAllFields(inFeat):
    # inFeat: input featureclass
    fields = arcpy.ListFields(inFeat)
    fieldList = []
    for field in fields:
        if not field.required:
            fieldList.append(field.name)
    arcpy.DeleteField_management(inFeat, fieldList)


# This function calculates a converter value for the input area unit. The base unit is "SquareKilometers".
def areaUnitConverter(inAreaUnit):
    # inAreaUnit: input Area Unit

    if inAreaUnit == "Acres":
        converter = 0.00404686
    elif inAreaUnit == "Ares":
        converter = 0.0001
    elif inAreaUnit == "Hectares":
        converter = 0.01
    elif inAreaUnit == "SquareCentimeters":
        converter = 0.0000000001
    elif inAreaUnit == "SquareDecimeters":
        converter = 0.00000001
    elif inAreaUnit == "SquareMeters":
        converter = 0.000001
    elif inAreaUnit == "SquareFeet":
        converter = 0.000000092903
    elif inAreaUnit == "SquareInches":
        converter = 0.00000000064516
    elif inAreaUnit == "SquareKilometers":
        converter = 1
    elif inAreaUnit == "SquareMiles":
        converter = 2.58999
    elif inAreaUnit == "SquareMillimeters":
        converter = 0.000000000001
    elif inAreaUnit == "SquareYards":
        converter = 0.00000083613

    return converter

# This function calculates positive or negative openness value from the batymetry grid
def calculateOpenness(
    bathyRas, radius, opennessParameter, outRas, tempWS, messages
):
    # bathyRas: input bathymetry grid
    # radius: radius value of the analysis window
    # opennessParameter: determine whether to calculate positive or negative openness
    # outRas: output openness grid
    # tempWS: temporary workspace
    # messages: to handle error messages

    ## most of the codes are taken from the "Openness" tool in the "ArcGeomorphometry Tools" python toolbox
    ## with the following modifications: 1) the analysis radius (window size) now accepts all positive integer values not limited to odd numbers only
    ## 2) the border areas are now processed properly instead of being left blank
    ## 3) modify some codes to work in later versions of python and numpy module

    time1 = datetime.now()
    radius = int(radius)
    # the radius in the diagonal directions
    radius1 = int(np.round(radius / np.sqrt(2)))

    # Describe input raster
    descData = arcpy.Describe(bathyRas)
    dataPath = descData.path
    cellSize = descData.meanCellHeight
    extent = descData.Extent
    height = descData.height
    width = descData.width
    xmin = extent.XMin
    ymin = extent.YMin

    spatialReference = descData.spatialReference
    if spatialReference.type == "Geographic":
        messages.addErrorMessage(
            "    *** Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required. ***"
        )
        raise arcpy.ExecuteError
    pnt = arcpy.Point(xmin, ymin)

    # Load DEM into numpy float32 array
    rasterDEMArray = arcpy.RasterToNumPyArray(bathyRas)

    # Check window size
    if radius > rasterDEMArray.shape[-1]:
        messages.addErrorMessage("    *** Analysis window is too long. ***")
        raise arcpy.ExecuteError

    #   calculate elevation angles within roughly circular search window (clockwise from N=0º)
    outShape = rasterDEMArray.shape

    outArray = np.zeros(outShape, dtype=np.float32)
    # the new array extends the loaded DEM array with a width of the radius from all four borders, so that the border areas of the loaded DEM can be processed properly
    rasterDEMArray1 = np.arange(
        (rasterDEMArray.shape[0] + 2 * radius)
        * (rasterDEMArray.shape[1] + 2 * radius)
    ).reshape(
        rasterDEMArray.shape[0] + 2 * radius, rasterDEMArray.shape[1] + 2 * radius
    )
    rasterDEMArray1 = np.zeros_like(rasterDEMArray1, dtype=float)
    rasterDEMArray1[:] = np.nan
    rasterDEMArray1[
        radius : rasterDEMArray.shape[0] + radius,
        radius : rasterDEMArray.shape[1] + radius,
    ] = rasterDEMArray
    del rasterDEMArray  # to release memory
    #   set temporal arrays
    tempArray = np.zeros_like(outArray)
    # arrayList holds the temporal arrays, so that we can calculate np.nanmean()
    arrayList = []
    shiftsList = [
        (x, y)
        for x in range(-radius, radius + 1)
        for y in range(-radius, radius + 1)
    ]
    #   calculate elevation angles within roughly circular search window (clockwise from N=0º)
    for direction in range(0, 360, 45):
        if direction == 0:
            shiftsListD = filter(lambda arr: arr[0] < 0 and arr[1] == 0, shiftsList)
        elif direction == 45:
            shiftsListD = filter(
                lambda arr: arr[1] < radius1 + 1
                and arr[0] == -arr[1]
                and arr[1] > 0,
                shiftsList,
            )
        elif direction == 90:
            shiftsListD = filter(lambda arr: arr[0] == 0 and arr[1] > 0, shiftsList)
        elif direction == 135:
            shiftsListD = filter(
                lambda arr: arr[1] < radius1 + 1
                and arr[0] == arr[1]
                and arr[0] > 0,
                shiftsList,
            )
        elif direction == 180:
            shiftsListD = filter(lambda arr: arr[0] > 0 and arr[1] == 0, shiftsList)
        elif direction == 225:
            shiftsListD = filter(
                lambda arr: arr[0] < radius1 + 1
                and arr[0] == -arr[1]
                and arr[0] > 0,
                shiftsList,
            )
        elif direction == 270:
            shiftsListD = filter(lambda arr: arr[0] == 0 and arr[1] < 0, shiftsList)
        elif direction == 315:
            shiftsListD = filter(
                lambda arr: -arr[1] < radius1 + 1
                and arr[0] == arr[1]
                and arr[0] < 0,
                shiftsList,
            )

        if opennessParameter == "positiveOpenness":  # calculate positive openness
            tempArray.fill(-9999.9)
            for dx, dy in shiftsListD:
                xstop = -radius + dx or None
                ystop = -radius + dy or None
                angleArray = (
                    rasterDEMArray1[radius + dx : xstop, radius + dy : ystop]
                    - rasterDEMArray1[radius:-radius, radius:-radius]
                ) / (math.hypot(dx, dy) * cellSize)
                angleArray[np.isnan(angleArray)] = -999999.9
                tempArray = np.maximum(tempArray, angleArray)
            tempArray = np.where(tempArray < -9999, np.nan, tempArray)
            arrayList.append(90 - np.degrees(np.arctan(tempArray)))
        elif opennessParameter == "negativeOpenness":  # calculate negative openness
            tempArray.fill(9999.9)
            for dx, dy in shiftsListD:
                xstop = -radius + dx or None
                ystop = -radius + dy or None
                angleArray = (
                    rasterDEMArray1[radius + dx : xstop, radius + dy : ystop]
                    - rasterDEMArray1[radius:-radius, radius:-radius]
                ) / (math.hypot(dx, dy) * cellSize)
                angleArray[np.isnan(angleArray)] = -999999.9
                tempArray = np.minimum(tempArray, angleArray)
            tempArray = np.where(tempArray < -9999, np.nan, tempArray)
            arrayList.append(90 + np.degrees(np.arctan(tempArray)))
    del rasterDEMArray1  # to release memory
    del tempArray  # to release memory

    # np.stack() requires numpy version 1.10.0 or higher
    stacked_array = np.stack(arrayList)
    with warnings.catch_warnings():
        # ignore runtime warning
        warnings.simplefilter("ignore", category=RuntimeWarning)
        outArray = np.nanmean(stacked_array, axis=0)

    # Create new output calculated raster, set spatial coordinates and save
    # if the raster is more than 5000 cells in either X or Y directions, split the raster into blocks
    blocksize = 5000
    if (width <= blocksize) and (height <= blocksize):
        newRaster = arcpy.NumPyArrayToRaster(
            outArray, pnt, cellSize, cellSize, -9999
        )
        if spatialReference.name != "Unknown":
            arcpy.DefineProjection_management(newRaster, spatialReference)
        # Set nodata where nodata in the input DEM
        newRaster = SetNull(IsNull(bathyRas), newRaster)
        newRaster.save(outRas)
        del outArray
    else:
        itemList = []
        xList = []
        yList = []
        for x in range(0, width, blocksize):
            xList.append(x)
        for y in range(0, height, blocksize):
            yList.append(y)
        xList.append(width)
        yList.append(height)

        i = 0
        j = len(yList) - 1
        k = 0
        while i < len(xList) - 1:
            while j > 0:
                arr = outArray[yList[j - 1] : yList[j], xList[i] : xList[i + 1]]
                hh = arr.shape[0]
                ww = arr.shape[1]
                pnt = arcpy.Point(xmin, ymin)
                newRaster = arcpy.NumPyArrayToRaster(
                    arr, pnt, cellSize, cellSize, -9999
                )
                ras = tempWS + "/" + "tempRas" + str(k)
                itemList.append(ras)
                newRaster.save(ras)
                if spatialReference.name != "Unknown":
                    arcpy.DefineProjection_management(ras, spatialReference)
                ymin = ymin + hh * cellSize

                j -= 1
                k += 1
            xmin = xmin + ww * cellSize
            i += 1
            j = len(yList) - 1
            ymin = extent.YMin

        del outArray  # release memory
        tempRaster = "tempRaster"

        arcpy.MosaicToNewRaster_management(
            itemList,
            tempWS,
            tempRaster,
            bathyRas,
            "32_BIT_FLOAT",
            "#",
            "1",
            "FIRST",
            "FIRST",
        )
        itemList.append(tempWS + "/" + tempRaster)

        # Set nodata where nodata in the input DEM
        newRaster = SetNull(IsNull(bathyRas), tempWS + "/" + tempRaster)
        newRaster.save(outRas)
        deleteDataItems(itemList)

    time2 = datetime.now()
    diff = time2 - time1
    arcpy.AddMessage("took " + str(diff) + " to generate openness.")
    return

def addField(inFeat, joinFeat, fieldName, inID, joinID, expression):
    # inFeat: input featureclass (or table)
    # joinFeat: feature (or table) to be joined with the inFeat
    # fieldName: the field in the inFeat to be calculated from the joinFeat
    # inID: unique id field in the inFeat
    # joinID: unique id field in the joinFeat that matches the inID
    # expression: expression text used to calculate the field

    fieldType = "DOUBLE"
    fieldPrecision = 15
    fieldScale = 6

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(
            inFeat, fieldName, fieldType, fieldPrecision, fieldScale
        )

    layerName = "tempLyr"
    arcpy.MakeFeatureLayer_management(inFeat, layerName)
    arcpy.AddJoin_management(layerName, inID, joinFeat, joinID, "KEEP_ALL")

    arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON3")

    arcpy.RemoveJoin_management(layerName, joinFeat)

    arcpy.Delete_management(layerName)
    arcpy.AddMessage(fieldName + " added and calculated")
    return

def splitFeat(workspace, inFeat, mergeFeat, joinFeat, selectFeat, noSplit):
    # workspace: the workspace which contains inFeat, mergeFeat and joinFeat
    # inFeat: the featureclass to be split
    # mergeFeat: a featureclass to be copied to the new workspace
    # joinFeat: another featureclass to be copied to the new workspace
    # selectFeat: the basename for a featureclass
    # noSplit: the number of subsets to split the inFeat into

    noFeat = int(arcpy.GetCount_management(inFeat).getOutput(0))
    featCount = int(noFeat / noSplit)

    featList = []
    tempfolderList = []
    workspaceList = []
    mergeFeatList = []
    joinFeatList = []
    selectFeatList = []

    path = workspace.rstrip(workspace.split('/')[-1])
    path = path.rstrip('/')
    baseName = workspace.split('/')[-1]
    baseName = baseName.split('.')[0]

    # loop through subsets
    i = 1
    while i <= noSplit:
        # create a File Geodatabase
        gdbName = baseName + str(i) + '.gdb'
        arcpy.CreateFileGDB_management(path, gdbName)
        arcpy.AddMessage(gdbName + ' created')
        workspace = path + '/' + gdbName
        workspaceList.append(workspace)
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
        # copy mergeFeat
        data1 = path + '/' + gdbName + '/' + mergeFeat
        mergeFeatList.append(data1)
        arcpy.Copy_management(mergeFeat, data1)
        arcpy.AddMessage(mergeFeat + ' copied')
        # copy joinFeat
        data2 = path + '/' + gdbName + '/' + joinFeat
        joinFeatList.append(data2)
        arcpy.Copy_management(joinFeat, data2)
        arcpy.AddMessage(joinFeat + ' copied')
        # create temp folder
        folderName = 'temp' + str(i)
        arcpy.CreateFolder_management(path, folderName)
        arcpy.AddMessage(folderName + ' created')
        tempFolder = path + '/' + folderName
        tempfolderList.append(tempFolder)
        # create a new name based on the basename of a featureclass
        data3 = path + '/' + gdbName + '/' + selectFeat + '_' + str(i)
        selectFeatList.append(data3)

        i += 1
    return workspaceList, tempfolderList, featList, mergeFeatList, joinFeatList, selectFeatList

# This function adds a featID field with unique ID values
def addIDField(inFeat, fieldName):
    # inFeat: input featureclass (or table)
    # fieldName: the name of the unique ID field

    fieldType = "LONG"
    fieldPrecision = 15

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(inFeat, fieldName, fieldType, fieldPrecision)

    expression = "!OBJECTID!"

    arcpy.CalculateField_management(inFeat, fieldName, expression, "PYTHON3")

    arcpy.AddMessage(fieldName + " added and calculated")
    return

# This function delete fields not to be kept
def keepSelectedFields(inFeat, fieldsTokeep):
    # inFeat: input featureclass (or table)
    # fieldsToKeep: a list of field names in inFeat to be kept

    fieldList = arcpy.ListFields(inFeat)
    fieldsToDrop = []
    for field in fieldList:
        if not field.required:
            if field.name not in fieldsTokeep:
                fieldsToDrop.append(field.name)
    if len(fieldsToDrop) > 0:
        arcpy.DeleteField_management(inFeat, fieldsToDrop)
    return

# This function adds and calculates fields with Text type
def addTextField(inFeat, joinFeat, fieldName, inID, joinID, expression):
    # inFeat: input featureclass (or table)
    # joinFeat: feature (or table) to be joined with the inFeat
    # fieldName: the field in the inFeat to be calculated from the joinFeat
    # inID: unique id field in the inFeat
    # joinID: unique id field in the joinFeat that matches the inID
    # expression: expression text used to calculate the field

    fieldType = "TEXT"
    fieldLength = 200

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(
            inFeat, fieldName, fieldType, field_length=fieldLength
        )

    layerName = "tempLyr"
    arcpy.MakeFeatureLayer_management(inFeat, layerName)
    arcpy.AddJoin_management(layerName, inID, joinFeat, joinID, "KEEP_ALL")

    arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON3")

    arcpy.RemoveJoin_management(layerName, joinFeat)

    arcpy.Delete_management(layerName)
    arcpy.AddMessage(fieldName + " added and calculated")
    return

# This function adds and calculates a long field from a joined featureclass
def addLongField(inFeat, joinFeat, fieldName, inID, joinID, expression):
    # inFeat: input featureclass (or table)
    # joinFeat: feature (or table) to be joined with the inFeat
    # fieldName: the field in the inFeat to be calculated from the joinFeat
    # inID: unique id field in the inFeat
    # joinID: unique id field in the joinFeat that matches the inID
    # expression: expression text used to calculate the field

    fieldType = "LONG"
    fieldPrecision = 15

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]

    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be recalculated")
    else:
        arcpy.AddField_management(inFeat, fieldName, fieldType, fieldPrecision)

    layerName = "tempLyr"
    arcpy.MakeFeatureLayer_management(inFeat, layerName)
    arcpy.AddJoin_management(layerName, inID, joinFeat, joinID, "KEEP_ALL")

    arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON3")

    arcpy.RemoveJoin_management(layerName, joinFeat)

    arcpy.Delete_management(layerName)
    arcpy.AddMessage(fieldName + " added and calculated")
    return

# This function deletes a field from input featureclass
def deleteSelectedField(inFeat, fieldName):
    # inFeat: input featureclass
    # fieldName: field to be deleted

    fields = arcpy.ListFields(inFeat)
    field_names = [f.name for f in fields]
    if fieldName in field_names:
        arcpy.AddMessage(fieldName + " exists and will be deleted")
        arcpy.DeleteField_management(inFeat, [fieldName])
    else:
        arcpy.AddMessage(fieldName + " does not exist")

    return



