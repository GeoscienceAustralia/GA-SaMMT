#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: July 1, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

from datetime import datetime

import arcpy
import numpy as np
import pandas as pd
from arcpy import env
from arcpy.sa import *
from pandas.core.common import flatten
import HelperFunctions


arcpy.CheckOutExtension("Spatial")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "AccessoryTools"

        # List of tool classes associated with this toolbox
        # There are two tools. Merge Connected Features Tool merges polygon features that are connected through shared points or borders.
        # Connect Nearby Linear Features Tool connects nearby linear bathymetric low features.
        self.tools = [
            Update_Features_Tool,
            Merge_Connected_Features_Tool,
            Connect_Nearby_Linear_Features_Tool,
            Connect_Nearby_Linear_HF_Features_Tool,
        ]


# This tool merges overlapped features and update the feature boundary
class Update_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update Feature Boundary Tool"
        self.description = "Merge overlapped features and update the feature boundary"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Datasets",
            name="in_feature_set",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
            multiValue=True,
        )
        # fourth parameter
        param1 = arcpy.Parameter(
            displayName="Output Features After Updating the Feature Boundaries",
            name="dissolvedFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        parameters = [param0, param1]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        in_feature_set = parameters[0].valueAsText
        dissolvedFeat = parameters[1].valueAsText
        inFeats = in_feature_set.split(";")
        # enable the helper functions
        helper = helpers()

        dissolvedFeat = HelperFunctions.convert_backslash_forwardslash(dissolvedFeat)
        inputs = []
        # loop through the input datasets and get their full path
        for inFeat in inFeats:
            # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
            # In this case, the full path needs to be obtained from the map layer
            if inFeat.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isFeatureLayer:
                        if inFeat == lyr.name:
                            inFeat = HelperFunctions.convert_backslash_forwardslash(
                                lyr.dataSource
                            )

                            # check that the input feature class is in a correct format
                            vecDesc = arcpy.Describe(inFeat)
                            vecType = vecDesc.dataType
                            if (vecType != "FeatureClass") or (
                                inFeat.rfind(".gdb") == -1
                            ):
                                messages.addErrorMessage(
                                    "The input featureclass must be a feature class in a File GeoDatabase!"
                                )
                                raise arcpy.ExecuteError
                            else:
                                inputs.append(inFeat)

        # check that the output featureclass is in a correct format
        if dissolvedFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # merge the input datasets
        mergedFeat = "mergedFeat"
        arcpy.management.Merge(inputs, mergedFeat)
        arcpy.AddMessage("merge done")
        # add a temporary field
        fieldName = "temp"
        fieldType = "LONG"
        fields = arcpy.ListFields(mergedFeat)
        field_names = [f.name for f in fields]
        # check the 'temp' field exists
        # if not, add it
        if fieldName not in field_names:
            arcpy.management.AddField(mergedFeat, fieldName, fieldType)

        expression = "1"
        arcpy.management.CalculateField(mergedFeat, fieldName, expression)
        # dissolve to obtain updated boundaries
        arcpy.management.Dissolve(
            mergedFeat, dissolvedFeat, fieldName, "", "SINGLE_PART"
        )
        arcpy.AddMessage("dissolve done")
        # delete temporary field and dataset
        arcpy.management.DeleteField(dissolvedFeat, fieldName)

        arcpy.management.Delete(mergedFeat)

        return


# This tool merges polygon features that are connected through shared points or borders.
class Merge_Connected_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Merge Connected Features Tool"
        self.description = (
            "Merge/dissolve polygon features that are connected by shared points"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Polygon Features",
            name="inFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )
        # fourth parameter
        param1 = arcpy.Parameter(
            displayName="Output Features After Merging Features Connected by Shared Points",
            name="dissolveFeat2",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        parameters = [param0, param1]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        inFeat = parameters[0].valueAsText
        dissolveFeat2 = parameters[1].valueAsText

        # enable the helper functions
        helper = helpers()
        inFeat = HelperFunctions.convert_backslash_forwardslash(inFeat)
        dissolveFeat2 = HelperFunctions.convert_backslash_forwardslash(dissolveFeat2)

        # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeat == lyr.name:
                        inFeat = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeat)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeat.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat2.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass after merging only features connected by shared point must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeat[0 : inFeat.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        HelperFunctions.addIDField(inFeat, "featID")

        # Generate near table between individual input poygon features
        itemList = []
        outTable = "nearTable"
        itemList.append(outTable)
        location = "NO_LOCATION"
        angle = "NO_ANGLE"
        closest = "ALL"
        searchRadius = "100 Meters"
        arcpy.GenerateNearTable_analysis(
            inFeat,
            inFeat,
            outTable,
            search_radius=searchRadius,
            location=location,
            angle=angle,
            closest=closest,
        )

        cursor = arcpy.SearchCursor(outTable)
        inIDList = []
        nearIDList = []

        # obtain idLists for connected features which have nearest distance = 0
        # for each input feature, identify its nearest feature with near_dist = 0 (e.g., connected features),
        # inIDList: list of ids of individual input features that have connected features
        # nearIDList:  this list contains the ids of their nearest features
        for row in cursor:
            inID = row.getValue("IN_FID")
            nearID = row.getValue("NEAR_FID")
            nearDist = row.getValue("NEAR_DIST")
            if nearDist == 0:
                inIDList.append(inID)
                nearIDList.append(nearID)

        del cursor, row
        # obtain the number of features that are connected
        size = np.unique(np.asarray(inIDList)).size

        if (
            size == 0
        ):  # if no features are connected, simply copy the input featureclass to the outputs
            arcpy.AddMessage("There are not connected features")
            arcpy.Copy_management(inFeat, dissolveFeat2)
        else:  # if there are connected features, do the followings
            arcpy.AddMessage(str(size) + " total features are connected")

            # call the helper function to generate a new list of featID
            # the connected features will be assigned the same featID
            featIDNewList = helper.findNewFeatIDs(inFeat, inIDList, nearIDList)
            # update the featID field with the new ids
            cursor = arcpy.UpdateCursor(inFeat)
            i = 0
            for row in cursor:
                featIDNew = featIDNewList[i]
                row.setValue("featID", featIDNew)
                cursor.updateRow(row)
                i += 1
            del cursor, row
            dissolveFeat = "dissolveFeat"
            itemList.append(dissolveFeat)
            # dissolve all connected features that have same featIDs
            arcpy.Dissolve_management(inFeat, dissolveFeat, "featID")
            helper.calculateFeatID(dissolveFeat)

            # after converting dissolved features (multipart) to single-part features, the features connected
            # by shared point(s) will be un-dissolved

            # multipart to single-part
            singlepartFeat = "dissolve_singlepart"
            itemList.append(singlepartFeat)
            arcpy.MultipartToSinglepart_management(dissolveFeat, singlepartFeat)

            # get the feature counts of the input features, the multipart dissolved features, and the single-part dissolved features
            inFeatCount = int(arcpy.GetCount_management(inFeat).getOutput(0))
            dissolveFeatCount = int(
                arcpy.GetCount_management(dissolveFeat).getOutput(0)
            )
            singlepartFeatCount = int(
                arcpy.GetCount_management(singlepartFeat).getOutput(0)
            )

            if (
                inFeatCount == singlepartFeatCount
            ):  # if all connected features are connected by shared points, copy the multipart dissolved features to outputs
                arcpy.AddMessage(
                    "They are "
                    + str(size)
                    + " features having shared point(s). They have thus been connected."
                )
                arcpy.Copy_management(dissolveFeat, dissolveFeat2)
            elif (
                dissolveFeatCount == singlepartFeatCount
            ):  # if all connected features are connected by shared borders, copy the input features to outputs
                arcpy.AddMessage(
                    "They are "
                    + str(size)
                    + " features having shared border(s); They have thus not been connected."
                )
                arcpy.Copy_management(inFeat, dissolveFeat2)
            else:  # if some features are connected by shared points and others are connected by shared borders,
                # 1. copy the single-part dissolved features as the output featureclass after merging features shared by borders
                # 2. call the helper function get a count of features sharing borders and generate output featureclass after merging sharing points
                dissolveFeat1 = "dissolveFeat1"
                itemList.append(dissolveFeat1)
                arcpy.Copy_management(singlepartFeat, dissolveFeat1)
                count = helper.mergeFeatures(
                    inFeat, dissolveFeat, dissolveFeat1, dissolveFeat2
                )
                count1 = size - count
                arcpy.AddMessage(
                    "They are "
                    + str(count)
                    + " features having shared border(s). They have thus not been connected."
                )
                arcpy.AddMessage(
                    "They are "
                    + str(count1)
                    + " features having shared point(s). They have thus been connected."
                )

            helper.calculateFeatID(dissolveFeat2)
            HelperFunctions.deleteDataItems(itemList)

        return


# This tool connects nearby linear bathymetric high features, based on one of the three algorithms.
# The features to be connected satitify need to satisfy a number of conditions based on distance and orientation.
class Connect_Nearby_Linear_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Connect Nearby Linear Features Tool"
        self.description = "Connect nearby linear bathymetric high or low features that are certain distance apart and align at a similar orientation"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric High/Low Features",
            name="inFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Distance Threshold",
            name="distThreshold",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Angle Threshold",
            name="angleThreshold",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Distance Weight",
            name="distWeight",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )
        param3.value = 1

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Angle Weight",
            name="angleWeight",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 1

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Connection Algorithm",
            name="conOption",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param5.filter.type = "ValueList"
        param5.filter.list = [
            "Mid points on Minimum Bounding Rectangle",
            "Most distant points on feature",
            "Mid points and Most distant points",
        ]
        param5.value = "Mid points on Minimum Bounding Rectangle"

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = "0 SquareMeters"

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Length_to_Width Ratio Threshold",
            name="lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param7.value = 0.9

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Output Connected Features",
            name="dissolveFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 10th parameter, used to hold temporaray files
        param9 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        parameters = [
            param0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7,
            param8,
            param9,
        ]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        inFeat = parameters[0].valueAsText
        distThreshold = parameters[1].valueAsText
        angleThreshold = parameters[2].valueAsText
        distWeight = parameters[3].valueAsText
        angleWeight = parameters[4].valueAsText
        conOption = parameters[5].valueAsText
        areaThreshold = parameters[6].valueAsText
        lwRatioT = parameters[7].valueAsText
        dissolveFeat = parameters[8].valueAsText
        tempFolder = parameters[9].valueAsText

        # enable helper function
        helper = helpers()
        inFeat = HelperFunctions.convert_backslash_forwardslash(inFeat)
        dissolveFeat = HelperFunctions.convert_backslash_forwardslash(dissolveFeat)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)

        # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeat == lyr.name:
                        inFeat = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeat)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeat.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output connected featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        distanceT = distThreshold.split(" ")[0]  # distance value
        linearUnit = distThreshold.split(" ")[1]  # distance unit
        if linearUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown distance unit.")
            raise arcpy.ExecuteError

        # check that the valid weights have been entered
        distWeight = float(distWeight)
        angleWeight = float(angleWeight)
        if (distWeight + angleWeight) == 0:
            messages.addErrorMessage(
                "You cann't assign a weight of zero to both distance and anlge!"
            )
            raise arcpy.ExecuteError

        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        workspaceName = inFeat[0 : inFeat.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeat, "featID")

        itemList = []
        # generate bounding rectangle
        MbrFeat = "bounding_rectangle"
        itemList.append(MbrFeat)
        arcpy.MinimumBoundingGeometry_management(
            inFeat, MbrFeat, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )
        # add/calculate anlge field to inFeat
        field = "rectangle_Orientation"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Orientation" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "rectangle_Length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Length" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "rectangle_Width"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Width" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "Length_Width_Ratio"
        inID = "featID"
        joinID = "featID"
        expression = (
            "!"
            + MbrFeat
            + "."
            + "MBG_Length"
            + "! / !"
            + MbrFeat
            + "."
            + "MBG_Width"
            + "!"
        )
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        # select a subset of input features to connect, based on the area threshold and length to width ratio threshold
        # this is to speed up the process when there are a large number of input features
        inFeat_selected1 = inFeat + "_selected1"
        itemList.append(inFeat_selected1)
		
		# convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
		# convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        whereClause = (
            "(Length_Width_Ratio >= "
            + str(lwRatioT)
            + ") And (Shape_Area >= "
            + str(areaThreshold)
            + ")"
        )
        arcpy.AddMessage(whereClause)
        arcpy.Select_analysis(inFeat, inFeat_selected1, whereClause)

        # generate the bounding rectangles for those selected features
        MbrFeat1 = "bounding_rectangle1"
        itemList.append(MbrFeat1)
        arcpy.MinimumBoundingGeometry_management(
            inFeat_selected1, MbrFeat1, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )

        inFeatCount = int(arcpy.GetCount_management(inFeat_selected1).getOutput(0))
        arcpy.AddMessage(str(inFeatCount) + " features selected for connection")

        # generate direction points depending on the selected algorithm
        # Three algorithms
        # The 'Mid points on Minimum Bounding Rectangle' algorithm identifies the direction points (e.g., N and S)
        # as the middle points on the corresponding sides of the minimum bounding rectangle (e.g., N side and S side).
        # The 'Most distance points on feature" algorithm identifies the direction points (e.g., N and S)
        # as the intercepted locations between the feature and the corresponding sides of the minimum bounding rectangle (e.g., N side and S side).
        # The 'Mid points and Most distant points' algorithm generate two set of direction points, one set using Mid points option, the other set using Most distant option

        # convert rectangle sides to lines
        MbrLines1 = "MbrLines1"
        itemList.append(MbrLines1)
        arcpy.SplitLine_management(MbrFeat1, MbrLines1)
        arcpy.AddMessage("MbrLines1 done")
        # add these attributes to the MbrLines1
        geometryFields = [
            ["bearing", "LINE_BEARING"],
            ["MidX", "CENTROID_X"],
            ["MidY", "CENTROID_Y"],
        ]
        arcpy.CalculateGeometryAttributes_management(MbrLines1, geometryFields)
        # add a field for the purpose of subsequent selection
        fieldName = "angle_temp"
        fieldType = "LONG"
        fieldPrecision = 15
        arcpy.AddField_management(MbrLines1, fieldName, fieldType, fieldPrecision)
        expression = "!bearing! - !rectangle_Orientation!"
        arcpy.CalculateField_management(MbrLines1, fieldName, expression)
        # select a subset of the lines: two lines from each bounding rectanlge (either N and S or E and W)
        MbrLines1_selected = "MbrLines1_selected"
        itemList.append(MbrLines1_selected)
        whereClause = "((angle_temp <> 0) And (angle_temp <> 180))"
        arcpy.Select_analysis(MbrLines1, MbrLines1_selected, whereClause)
        arcpy.AddMessage("MbrLines1 selection done")
        # identify and assign these lines with directional flags
        fieldName = "direction"
        fieldType = "text"
        fieldLength = 10
        arcpy.AddField_management(
            MbrLines1_selected, fieldName, fieldType, field_length=fieldLength
        )

        expression = "getDirection(round(!rectangle_Orientation!,2),!angle_temp!)"

        codeblock = """
def getDirection(angle1,angle2):
    if(angle1 >= 0) & (angle1 <= 45) & (angle2 == 90):
        return 'N'
    if(angle1 >= 0) & (angle1 <= 45) & (angle2 == 270):
        return 'S'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == 90):
        return 'E'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == 270):
        return 'W'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == -90):
        return 'W'
    if(angle1 > 90) & (angle1 <= 135) & (angle2 == 90):
        return 'E'
    if(angle1 > 90) & (angle1 <= 135) & (angle2 == -90):
        return 'W'
    if(angle1 > 135) & (angle1 <= 180) & (angle2 == 90):
        return 'S'
    if(angle1 > 135) & (angle1 <= 180) & (angle2 == -90):
        return 'N'"""

        arcpy.CalculateField_management(
            MbrLines1_selected, fieldName, expression, "PYTHON3", codeblock
        )
        # add and calculate an "angle" field
        fieldName = "angle"
        fieldType = "DOUBLE"
        filedPrecision = 15
        fieldScale = 6
        arcpy.AddField_management(
            MbrLines1_selected, fieldName, fieldType, fieldPrecision, fieldScale
        )
        expression = "!rectangle_Orientation!"
        arcpy.CalculateField_management(
            MbrLines1_selected, fieldName, expression, "PYTHON3"
        )

        pointFeat = "pointFeat"
        itemList.append(pointFeat)
        # generate directional points featureclass(es) according to the selected algorithm
        if conOption == "Mid points on Minimum Bounding Rectangle":
            # MidX and MidY fields already given the coordinate of the middle point
            arcpy.XYTableToPoint_management(
                MbrLines1_selected, pointFeat, "MidX", "MidY", "#", MbrLines1_selected
            )
            fieldsToKept = ["featID", "angle", "direction"]
            fieldsToDelete = []
            fields = arcpy.ListFields(pointFeat)
            for field in fields:
                if not field.required:
                    if not field.name in fieldsToKept:
                        fieldsToDelete.append(field.name)

            arcpy.DeleteField_management(pointFeat, fieldsToDelete)
        elif conOption == "Most distant points on feature":
            helper.getDirectionPoints(
                inFeat_selected1, MbrLines1_selected, tempFolder, pointFeat
            )
        elif (
            conOption == "Mid points and Most distant points"
        ):  # generate two set of direction points, one set using Mid points option, the other set using Most distant option
            pointFeat1 = "pointFeat1"
            itemList.append(pointFeat1)

            arcpy.XYTableToPoint_management(
                MbrLines1_selected, pointFeat, "MidX", "MidY", "#", MbrLines1_selected
            )
            fieldsToKept = ["featID", "angle", "direction"]
            fieldsToDelete = []
            fields = arcpy.ListFields(pointFeat)
            for field in fields:
                if not field.required:
                    if not field.name in fieldsToKept:
                        fieldsToDelete.append(field.name)

            arcpy.DeleteField_management(pointFeat, fieldsToDelete)

            helper.getDirectionPoints(
                inFeat_selected1, MbrLines1_selected, tempFolder, pointFeat1
            )

        arcpy.AddMessage("direction points done at " + str(datetime.now()))

        # separate points based on directions
        pointFeatN = pointFeat + "_N"
        pointFeatS = pointFeat + "_S"
        pointFeatE = pointFeat + "_E"
        pointFeatW = pointFeat + "_W"
        itemList.append(pointFeatN)
        itemList.append(pointFeatS)
        itemList.append(pointFeatE)
        itemList.append(pointFeatW)

        whereClause = "direction = 'N'"
        arcpy.Select_analysis(pointFeat, pointFeatN, whereClause)
        whereClause = "direction = 'S'"
        arcpy.Select_analysis(pointFeat, pointFeatS, whereClause)
        whereClause = "direction = 'E'"
        arcpy.Select_analysis(pointFeat, pointFeatE, whereClause)
        whereClause = "direction = 'W'"
        arcpy.Select_analysis(pointFeat, pointFeatW, whereClause)
        # For this combined option, generate another set of direction point features
        if conOption == "Mid points and Most distant points":
            pointFeatN1 = pointFeat1 + "_N"
            pointFeatS1 = pointFeat1 + "_S"
            pointFeatE1 = pointFeat1 + "_E"
            pointFeatW1 = pointFeat1 + "_W"
            itemList.append(pointFeatN1)
            itemList.append(pointFeatS1)
            itemList.append(pointFeatE1)
            itemList.append(pointFeatW1)

            whereClause = "direction = 'N'"
            arcpy.Select_analysis(pointFeat1, pointFeatN1, whereClause)
            whereClause = "direction = 'S'"
            arcpy.Select_analysis(pointFeat1, pointFeatS1, whereClause)
            whereClause = "direction = 'E'"
            arcpy.Select_analysis(pointFeat1, pointFeatE1, whereClause)
            whereClause = "direction = 'W'"
            arcpy.Select_analysis(pointFeat1, pointFeatW1, whereClause)

        # generate links based on the direction points
        # For the combined option, create four sets of links
        # For the other two options, just need to create one set of links
        if conOption == "Mid points and Most distant points":
            linksFeatWE = "linkWE"
            linksFeatSN = "linkSN"
            linksFeatWN = "linkWN"
            linksFeatSE = "linkSE"
            linksFeatSW = "linkSW"
            linksFeatEN = "linkEN"
            itemList.append(linksFeatWE)
            itemList.append(linksFeatSN)
            itemList.append(linksFeatWN)
            itemList.append(linksFeatSE)
            itemList.append(linksFeatSW)
            itemList.append(linksFeatEN)
            # This ArcGIS function create links from each origin to each destination
            # Note that the tool parameter 'distance threshold' is used in the search_distance parameter to limit the number of destination points from each origin point
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatE,
                linksFeatWE,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatN,
                linksFeatSN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatN,
                linksFeatWN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatE,
                linksFeatSE,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatW,
                linksFeatSW,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatE,
                pointFeatN,
                linksFeatEN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            helper.calculateFeatIDAngle(linksFeatWE, pointFeatW, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatSN, pointFeatS, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatWN, pointFeatW, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatSE, pointFeatS, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatSW, pointFeatS, pointFeatW)
            helper.calculateFeatIDAngle(linksFeatEN, pointFeatE, pointFeatN)

            linksFeatW1E1 = "linkW1E1"
            linksFeatS1N1 = "linkS1N1"
            linksFeatW1N1 = "linkW1N1"
            linksFeatS1E1 = "linkS1E1"
            linksFeatS1W1 = "linkS1W1"
            linksFeatE1N1 = "linkE1N1"
            itemList.append(linksFeatW1E1)
            itemList.append(linksFeatS1N1)
            itemList.append(linksFeatW1N1)
            itemList.append(linksFeatS1E1)
            itemList.append(linksFeatS1W1)
            itemList.append(linksFeatE1N1)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW1,
                pointFeatE1,
                linksFeatW1E1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatN1,
                linksFeatS1N1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW1,
                pointFeatN1,
                linksFeatW1N1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatE1,
                linksFeatS1E1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatW1,
                linksFeatS1W1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatE1,
                pointFeatN1,
                linksFeatE1N1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            helper.calculateFeatIDAngle(linksFeatW1E1, pointFeatW1, pointFeatE1)
            helper.calculateFeatIDAngle(linksFeatS1N1, pointFeatS1, pointFeatN1)
            helper.calculateFeatIDAngle(linksFeatW1N1, pointFeatW1, pointFeatN1)
            helper.calculateFeatIDAngle(linksFeatS1E1, pointFeatS1, pointFeatE1)
            helper.calculateFeatIDAngle(linksFeatS1W1, pointFeatS1, pointFeatW1)
            helper.calculateFeatIDAngle(linksFeatE1N1, pointFeatE1, pointFeatN1)

            linksFeatWE1 = "linkWE1"
            linksFeatSN1 = "linkSN1"
            linksFeatWN1 = "linkWN1"
            linksFeatSE1 = "linkSE1"
            linksFeatSW1 = "linkSW1"
            linksFeatEN1 = "linkEN1"
            itemList.append(linksFeatWE1)
            itemList.append(linksFeatSN1)
            itemList.append(linksFeatWN1)
            itemList.append(linksFeatSE1)
            itemList.append(linksFeatSW1)
            itemList.append(linksFeatEN1)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatE1,
                linksFeatWE1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatN1,
                linksFeatSN1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatN1,
                linksFeatWN1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatE1,
                linksFeatSE1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatW1,
                linksFeatSW1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatE,
                pointFeatN1,
                linksFeatEN1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            helper.calculateFeatIDAngle(linksFeatWE1, pointFeatW, pointFeatE1)
            helper.calculateFeatIDAngle(linksFeatSN1, pointFeatS, pointFeatN1)
            helper.calculateFeatIDAngle(linksFeatWN1, pointFeatW, pointFeatN1)
            helper.calculateFeatIDAngle(linksFeatSE1, pointFeatS, pointFeatE1)
            helper.calculateFeatIDAngle(linksFeatSW1, pointFeatS, pointFeatW1)
            helper.calculateFeatIDAngle(linksFeatEN1, pointFeatE, pointFeatN1)

            linksFeatW1E = "linkW1E"
            linksFeatS1N = "linkS1N"
            linksFeatW1N = "linkW1N"
            linksFeatS1E = "linkS1E"
            linksFeatS1W = "linkS1W"
            linksFeatE1N = "linkE1N"
            itemList.append(linksFeatW1E)
            itemList.append(linksFeatS1N)
            itemList.append(linksFeatW1N)
            itemList.append(linksFeatS1E)
            itemList.append(linksFeatS1W)
            itemList.append(linksFeatE1N)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW1,
                pointFeatE,
                linksFeatW1E,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatN,
                linksFeatS1N,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW1,
                pointFeatN,
                linksFeatW1N,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatE,
                linksFeatS1E,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS1,
                pointFeatW,
                linksFeatS1W,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatE1,
                pointFeatN,
                linksFeatE1N,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            helper.calculateFeatIDAngle(linksFeatW1E, pointFeatW1, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatS1N, pointFeatS1, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatW1N, pointFeatW1, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatS1E, pointFeatS1, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatS1W, pointFeatS1, pointFeatW)
            helper.calculateFeatIDAngle(linksFeatE1N, pointFeatE1, pointFeatN)

            # merge four sets together
            fList = [linksFeatW1E1, linksFeatWE1, linksFeatW1E]
            arcpy.Append_management(fList, linksFeatWE)
            fList = [linksFeatS1N1, linksFeatSN1, linksFeatS1N]
            arcpy.Append_management(fList, linksFeatSN)
            fList = [linksFeatW1N1, linksFeatWN1, linksFeatW1N]
            arcpy.Append_management(fList, linksFeatWN)
            fList = [linksFeatS1E1, linksFeatSE1, linksFeatS1E]
            arcpy.Append_management(fList, linksFeatSE)
            fList = [linksFeatS1W1, linksFeatSW1, linksFeatS1W]
            arcpy.Append_management(fList, linksFeatSW)
            fList = [linksFeatE1N1, linksFeatEN1, linksFeatE1N]
            arcpy.Append_management(fList, linksFeatEN)
        else:
            # create only one set of links
            linksFeatWE = "linkWE"
            linksFeatSN = "linkSN"
            linksFeatWN = "linkWN"
            linksFeatSE = "linkSE"
            linksFeatSW = "linkSW"
            linksFeatEN = "linkEN"
            itemList.append(linksFeatWE)
            itemList.append(linksFeatSN)
            itemList.append(linksFeatWN)
            itemList.append(linksFeatSE)
            itemList.append(linksFeatSW)
            itemList.append(linksFeatEN)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatE,
                linksFeatWE,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatN,
                linksFeatSN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatW,
                pointFeatN,
                linksFeatWN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatE,
                linksFeatSE,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatS,
                pointFeatW,
                linksFeatSW,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeatE,
                pointFeatN,
                linksFeatEN,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            helper.calculateFeatIDAngle(linksFeatWE, pointFeatW, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatSN, pointFeatS, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatWN, pointFeatW, pointFeatN)
            helper.calculateFeatIDAngle(linksFeatSE, pointFeatS, pointFeatE)
            helper.calculateFeatIDAngle(linksFeatSW, pointFeatS, pointFeatW)
            helper.calculateFeatIDAngle(linksFeatEN, pointFeatE, pointFeatN)

        arcpy.AddMessage("initial links generated at " + str(datetime.now()))

        # For each link direction (e.g., SN indicates from South to North), select two subsets of links based on certain criteria.
        # The criteria are determined by the distance threshold, angle threshold, distance weight and angle weight.
        # There are six link directions (SN, WN, SE, WE, SW and EN) to consider, when connecting neary features.
        outLinkFeatSN1 = "linkSN_1"
        outLinkFeatSN2 = "linkSN_2"
        itemList.append(outLinkFeatSN1)
        itemList.append(outLinkFeatSN2)
        helper.doLinks1(
            linksFeatSN,
            outLinkFeatSN1,
            outLinkFeatSN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SN",
        )

        outLinkFeatWN1 = "linkWN_1"
        outLinkFeatWN2 = "linkWN_2"
        itemList.append(outLinkFeatWN1)
        itemList.append(outLinkFeatWN2)
        helper.doLinks1(
            linksFeatWN,
            outLinkFeatWN1,
            outLinkFeatWN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "WN",
        )

        outLinkFeatSE1 = "linkSE_1"
        outLinkFeatSE2 = "linkSE_2"
        itemList.append(outLinkFeatSE1)
        itemList.append(outLinkFeatSE2)
        helper.doLinks1(
            linksFeatSE,
            outLinkFeatSE1,
            outLinkFeatSE2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SE",
        )

        outLinkFeatWE1 = "linkWE_1"
        outLinkFeatWE2 = "linkWE_2"
        itemList.append(outLinkFeatWE1)
        itemList.append(outLinkFeatWE2)
        helper.doLinks1(
            linksFeatWE,
            outLinkFeatWE1,
            outLinkFeatWE2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "WE",
        )

        outLinkFeatSW1 = "linkSW_1"
        outLinkFeatSW2 = "linkSW_2"
        itemList.append(outLinkFeatSW1)
        itemList.append(outLinkFeatSW2)
        helper.doLinks1(
            linksFeatSW,
            outLinkFeatSW1,
            outLinkFeatSW2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SW",
        )

        outLinkFeatEN1 = "linkEN_1"
        outLinkFeatEN2 = "linkEN_2"
        itemList.append(outLinkFeatEN1)
        itemList.append(outLinkFeatEN2)
        helper.doLinks1(
            linksFeatEN,
            outLinkFeatEN1,
            outLinkFeatEN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "EN",
        )

        arcpy.AddMessage("do links done at " + str(datetime.now()))

        ##        # note that the input link features could also be those resulted from the first set of links
        ##        # e.g. outLinkFeatSN1, outLinkFeatWN1, outLinkFeatSE1, outLinkFeatWE1, outLinkFeatSW1, outLinkFeatEN1
        ##        # the result would be slightly different

        # create initial lists
        linksFeatList = []
        linksFeatList.append(outLinkFeatSN2)
        linksFeatList.append(outLinkFeatWN2)
        linksFeatList.append(outLinkFeatSE2)
        linksFeatList.append(outLinkFeatWE2)
        linksFeatList.append(outLinkFeatSW2)
        linksFeatList.append(outLinkFeatEN2)

        featID1List, featID2List, featIDListList, distList, angleList = (
            helper.createLists(linksFeatList)
        )
        arcpy.AddMessage("create lists done")
        # updates ids list and other lists when multiple elements share either "from" or "to" points
        # each outList1 element contains a list of featIDs
        list1, list2, outList1, list3, list4 = helper.doLists(
            featID1List,
            featID2List,
            featIDListList,
            distList,
            angleList,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
        )
        arcpy.AddMessage("do lists done at " + str(datetime.now()))
        # further updates ids list when multiple elements connected through sharing "from" and "to" points
        # each outList2 element contains a list of featIDs
        outList2 = helper.doLists1(
            list1,
            list2,
            outList1,
            list3,
            list4,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
        )
        arcpy.AddMessage("do lists1 done at " + str(datetime.now()))

        # merge elements of outList2 where appropriate (e.g., share at least one common id)
        leng1 = len(helper.getUnique(list(flatten(outList2))))
        arcpy.AddMessage("leng1:" + str(leng1))
        outList = helper.mergeList(outList2)
        leng2 = len(list(flatten(outList)))
        arcpy.AddMessage("leng2:" + str(leng2))
        # continue to merge until no more merge is possible
        while leng2 > leng1:
            arcpy.AddMessage("leng2:" + str(leng2))
            outList = helper.mergeList(outList)
            leng2 = len(list(flatten(outList)))
        arcpy.AddMessage("merge elements done at " + str(datetime.now()))

        # get the original featID list
        cursor = arcpy.SearchCursor(inFeat)
        featIDList = []
        for row in cursor:
            featID = row.getValue("featID")
            featIDList.append(featID)
        del cursor, row

        ### assign a same featID to features that have been identified as to be connected
        featIDNewList = featIDList.copy()
        for tempList in outList:
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = featIDList.index(idv)
                featureID = featIDList[index]
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]

        inFeat1 = "inFeat1"
        itemList.append(inFeat1)
        arcpy.Copy_management(inFeat, inFeat1)
        # update the featID
        cursor = arcpy.UpdateCursor(inFeat1)
        i = 0
        for row in cursor:
            featIDNew = featIDNewList[i]
            row.setValue("featID", featIDNew)
            cursor.updateRow(row)
            i += 1
        del cursor, row
        # merge connected features to generate output featureclass
        arcpy.Dissolve_management(inFeat1, dissolveFeat, "featID")
        arcpy.AddMessage("merge done")
        # call the helper function to re-calculate featID the output featureclass
        helper.calculateFeatID(dissolveFeat)
        # delete temporary data
        HelperFunctions.deleteDataItems(itemList)

        return


# This tool connects nearby linear bathymetric high features, based on one of the three algorithms.
# The features to be connected satitify need to satisfy a number of conditions based on distance and orientation.
class Connect_Nearby_Linear_HF_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Connect Nearby Linear HF Features Tool"
        self.description = "Connect nearby linear bathymetric low features through their feet and heads that are certain distance apart and align at a similar orientation"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric Low Features",
            name="inFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Distance Threshold",
            name="distThreshold",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input",
        )

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Angle Threshold",
            name="angleThreshold",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Distance Weight",
            name="distWeight",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 1

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Angle Weight",
            name="angleWeight",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )
        param5.value = 1

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Connection Algorithm",
            name="conOption",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param6.filter.type = "ValueList"
        param6.filter.list = [
            "Mid points on Minimum Bounding Rectangle",
            "Most distant points on feature",
            "Mid points and Most distant points",
        ]
        param6.value = "Mid points on Minimum Bounding Rectangle"

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Optional",
            direction="Input",
        )
        param7.value = "0 SquareMeters"

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Length_to_Width Ratio Threshold",
            name="lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param8.value = 0.9

        # 10th parameter
        param9 = arcpy.Parameter(
            displayName="Output Connected Features",
            name="dissolveFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 11th parameter, used to hold temporaray files
        param10 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="Required",
            direction="Input",
        )

        parameters = [
            param0,
            param1,
            param2,
            param3,
            param4,
            param5,
            param6,
            param7,
            param8,
            param9,
            param10,
        ]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        inFeat = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        distThreshold = parameters[2].valueAsText
        angleThreshold = parameters[3].valueAsText
        distWeight = parameters[4].valueAsText
        angleWeight = parameters[5].valueAsText
        conOption = parameters[6].valueAsText
        areaThreshold = parameters[7].valueAsText
        lwRatioT = parameters[8].valueAsText
        dissolveFeat = parameters[9].valueAsText
        tempFolder = parameters[10].valueAsText

        # enable helper function
        helper = helpers()
        inFeat = HelperFunctions.convert_backslash_forwardslash(inFeat)
        dissolveFeat = HelperFunctions.convert_backslash_forwardslash(dissolveFeat)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)

        # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeat == lyr.name:
                        inFeat = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeat)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeat.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(inBathy)
        rasFormat = rasDesc.format
        if rasFormat != "FGDBR":
            messages.addErrorMessage(
                "The input bathymetry raster must be a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output connected featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input featureclass is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        # check that the input bathymetry grid is in a projected coordinate system
        spatialReference = rasDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        distanceT = distThreshold.split(" ")[0]  # distance value
        linearUnit = distThreshold.split(" ")[1]  # distance unit
        if linearUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown distance unit.")
            raise arcpy.ExecuteError

        # check that the valid weights have been entered
        distWeight = float(distWeight)
        angleWeight = float(angleWeight)
        if (distWeight + angleWeight) == 0:
            messages.addErrorMessage(
                "You cann't assign a weight of zero to both distance and anlge!"
            )
            raise arcpy.ExecuteError

        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        workspaceName = inFeat[0 : inFeat.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeat, "featID")

        itemList = []
        # generate bounding rectangle
        MbrFeat = "bounding_rectangle"
        itemList.append(MbrFeat)
        arcpy.MinimumBoundingGeometry_management(
            inFeat, MbrFeat, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )
        # add/calculate anlge field to inFeat
        field = "rectangle_Orientation"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Orientation" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "rectangle_Length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Length" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "rectangle_Width"
        inID = "featID"
        joinID = "featID"
        expression = "!" + MbrFeat + "." + "MBG_Width" + "!"
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        field = "Length_Width_Ratio"
        inID = "featID"
        joinID = "featID"
        expression = (
            "!"
            + MbrFeat
            + "."
            + "MBG_Length"
            + "! / !"
            + MbrFeat
            + "."
            + "MBG_Width"
            + "!"
        )
        HelperFunctions.addField(inFeat, MbrFeat, field, inID, joinID, expression)

        # select a subset of input features to connect, based on the area threshold and length to width ratio threshold
        # this is to speed up the process when there are a large number of input features
        inFeat_selected1 = inFeat + "_selected1"
        itemList.append(inFeat_selected1)
		# convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
		# convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        whereClause = (
            "(Length_Width_Ratio >= "
            + str(lwRatioT)
            + ") And (Shape_Area >= "
            + str(areaThreshold)
            + ")"
        )
        arcpy.AddMessage(whereClause)
        arcpy.Select_analysis(inFeat, inFeat_selected1, whereClause)

        # generate the bounding rectangles for those selected features
        MbrFeat1 = "bounding_rectangle1"
        itemList.append(MbrFeat1)
        arcpy.MinimumBoundingGeometry_management(
            inFeat_selected1, MbrFeat1, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )

        inFeatCount = int(arcpy.GetCount_management(inFeat_selected1).getOutput(0))
        arcpy.AddMessage(str(inFeatCount) + " features selected for connection")

        # generate direction points depending on the selected algorithm
        # Three algorithms
        # The 'Mid points on Minimum Bounding Rectangle' algorithm identifies the direction points (e.g., N and S)
        # as the middle points on the corresponding sides of the minimum bounding rectangle (e.g., N side and S side).
        # The 'Most distance points on feature" algorithm identifies the direction points (e.g., N and S)
        # as the intercepted locations between the feature and the corresponding sides of the minimum bounding rectangle (e.g., N side and S side).
        # The 'Mid points and Most distant points' algorithm generate two set of direction points, one set using Mid points option, the other set using Most distant option

        # convert rectangle sides to lines
        MbrLines1 = "MbrLines1"
        itemList.append(MbrLines1)
        arcpy.SplitLine_management(MbrFeat1, MbrLines1)
        arcpy.AddMessage("MbrLines1 done")
        # add these attributes to the MbrLines1
        geometryFields = [
            ["bearing", "LINE_BEARING"],
            ["MidX", "CENTROID_X"],
            ["MidY", "CENTROID_Y"],
        ]
        arcpy.CalculateGeometryAttributes_management(MbrLines1, geometryFields)
        # add a field for the purpose of subsequent selection
        fieldName = "angle_temp"
        fieldType = "LONG"
        fieldPrecision = 15
        arcpy.AddField_management(MbrLines1, fieldName, fieldType, fieldPrecision)
        expression = "!bearing! - !rectangle_Orientation!"
        arcpy.CalculateField_management(MbrLines1, fieldName, expression)
        # select a subset of the lines: two lines from each bounding rectanlge (either N and S or E and W)
        MbrLines1_selected = "MbrLines1_selected"
        itemList.append(MbrLines1_selected)
        whereClause = "((angle_temp <> 0) And (angle_temp <> 180))"
        arcpy.Select_analysis(MbrLines1, MbrLines1_selected, whereClause)
        arcpy.AddMessage("MbrLines1 selection done")
        # identify and assign these lines with directional flags
        fieldName = "direction"
        fieldType = "text"
        fieldLength = 10
        arcpy.AddField_management(
            MbrLines1_selected, fieldName, fieldType, field_length=fieldLength
        )

        expression = "getDirection(round(!rectangle_Orientation!,2),!angle_temp!)"

        codeblock = """
def getDirection(angle1,angle2):
    if(angle1 >= 0) & (angle1 <= 45) & (angle2 == 90):
        return 'N'
    if(angle1 >= 0) & (angle1 <= 45) & (angle2 == 270):
        return 'S'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == 90):
        return 'E'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == 270):
        return 'W'
    if(angle1 > 45) & (angle1 <= 90) & (angle2 == -90):
        return 'W'
    if(angle1 > 90) & (angle1 <= 135) & (angle2 == 90):
        return 'E'
    if(angle1 > 90) & (angle1 <= 135) & (angle2 == -90):
        return 'W'
    if(angle1 > 135) & (angle1 <= 180) & (angle2 == 90):
        return 'S'
    if(angle1 > 135) & (angle1 <= 180) & (angle2 == -90):
        return 'N'"""

        arcpy.CalculateField_management(
            MbrLines1_selected, fieldName, expression, "PYTHON3", codeblock
        )
        # add and calculate an "angle" field
        fieldName = "angle"
        fieldType = "DOUBLE"
        filedPrecision = 15
        fieldScale = 6
        arcpy.AddField_management(
            MbrLines1_selected, fieldName, fieldType, fieldPrecision, fieldScale
        )
        expression = "!rectangle_Orientation!"
        arcpy.CalculateField_management(
            MbrLines1_selected, fieldName, expression, "PYTHON3"
        )

        # expand inBathy
        # This is to ensure that the point(s) at the edge of bathymetry grid have depth values
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

        mosaicBathy = "mosaicBathy"
        pointFeat = "pointFeat"
        itemList.append(pointFeat)
        # generate directional points featureclass
        if conOption == "Mid points on Minimum Bounding Rectangle":
            # MidX and MidY fields already given the coordinate of the middle point
            arcpy.XYTableToPoint_management(
                MbrLines1_selected, pointFeat, "MidX", "MidY", "#", MbrLines1_selected
            )
            fieldsToKept = ["featID", "angle", "direction"]
            fieldsToDelete = []
            fields = arcpy.ListFields(pointFeat)
            for field in fields:
                if not field.required:
                    if not field.name in fieldsToKept:
                        fieldsToDelete.append(field.name)

            arcpy.DeleteField_management(pointFeat, fieldsToDelete)
            arcpy.AddXY_management(pointFeat)

            pointFeat2 = "pointFeat2"
            itemList.append(pointFeat2)
            # add two fields to incidate head and foot locations
            helper.toFHpoints(pointFeat, mosaicBathy, tempFolder, pointFeat2)

            pointFeat2F = "pointFeat2F"
            pointFeat2H = "pointFeat2H"
            itemList.append(pointFeat2F)
            itemList.append(pointFeat2H)
            whereClause = "location = 'F'"
            arcpy.Select_analysis(pointFeat2, pointFeat2F, whereClause)
            whereClause = "location = 'H'"
            arcpy.Select_analysis(pointFeat2, pointFeat2H, whereClause)
        elif conOption == "Most distant points on feature":
            helper.getDirectionPoints(
                inFeat_selected1, MbrLines1_selected, tempFolder, pointFeat
            )
            pointFeat2 = "pointFeat2"
            itemList.append(pointFeat2)
            helper.toFHpoints(pointFeat, mosaicBathy, tempFolder, pointFeat2)

            pointFeat2F = "pointFeat2F"
            pointFeat2H = "pointFeat2H"
            itemList.append(pointFeat2F)
            itemList.append(pointFeat2H)
            whereClause = "location = 'F'"
            arcpy.Select_analysis(pointFeat2, pointFeat2F, whereClause)
            whereClause = "location = 'H'"
            arcpy.Select_analysis(pointFeat2, pointFeat2H, whereClause)
        elif (
            conOption == "Mid points and Most distant points"
        ):  # generate two set of direction points, one set using Mid points option, the other set using Most distant option
            arcpy.XYTableToPoint_management(
                MbrLines1_selected, pointFeat, "MidX", "MidY", "#", MbrLines1_selected
            )
            fieldsToKept = ["featID", "angle", "direction"]
            fieldsToDelete = []
            fields = arcpy.ListFields(pointFeat)
            for field in fields:
                if not field.required:
                    if not field.name in fieldsToKept:
                        fieldsToDelete.append(field.name)

            arcpy.DeleteField_management(pointFeat, fieldsToDelete)
            arcpy.AddXY_management(pointFeat)

            pointFeat2 = "pointFeat2"
            itemList.append(pointFeat2)
            helper.toFHpoints(pointFeat, mosaicBathy, tempFolder, pointFeat2)
            pointFeat2F = "pointFeat2F"
            pointFeat2H = "pointFeat2H"
            itemList.append(pointFeat2F)
            itemList.append(pointFeat2H)
            whereClause = "location = 'F'"
            arcpy.Select_analysis(pointFeat2, pointFeat2F, whereClause)
            whereClause = "location = 'H'"
            arcpy.Select_analysis(pointFeat2, pointFeat2H, whereClause)

            pointFeat1 = "pointFeat1"
            itemList.append(pointFeat1)
            helper.getDirectionPoints(
                inFeat_selected1, MbrLines1_selected, tempFolder, pointFeat1
            )
            pointFeat3 = "pointFeat3"
            itemList.append(pointFeat3)
            helper.toFHpoints(pointFeat1, mosaicBathy, tempFolder, pointFeat3)

            pointFeat3F = "pointFeat3F"
            pointFeat3H = "pointFeat3H"
            itemList.append(pointFeat3F)
            itemList.append(pointFeat3H)
            whereClause = "location = 'F'"
            arcpy.Select_analysis(pointFeat3, pointFeat3F, whereClause)
            whereClause = "location = 'H'"
            arcpy.Select_analysis(pointFeat3, pointFeat3H, whereClause)

        arcpy.AddMessage("direction points done at " + str(datetime.now()))

        # create and process links
        if conOption == "Mid points and Most distant points":
            # create four sets of links
            linksFeat1 = "links1"
            linksFeat2 = "links2"
            linksFeat3 = "links3"
            linksFeat4 = "links4"
            itemList.append(linksFeat1)
            itemList.append(linksFeat2)
            itemList.append(linksFeat3)
            itemList.append(linksFeat4)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeat2F,
                pointFeat2H,
                linksFeat1,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeat2F,
                pointFeat3H,
                linksFeat2,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeat3F,
                pointFeat3H,
                linksFeat3,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeat3F,
                pointFeat2H,
                linksFeat4,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )

            outLinksFeat1 = "links1_selected"
            outLinksFeat2 = "links2_selected"
            outLinksFeat3 = "links3_selected"
            outLinksFeat4 = "links4_selected"
            itemList.append(outLinksFeat1)
            itemList.append(outLinksFeat2)
            itemList.append(outLinksFeat3)
            itemList.append(outLinksFeat4)
            # select a subset of links
            helper.selectLinks(linksFeat1, pointFeat2F, pointFeat2H, outLinksFeat1)
            helper.selectLinks(linksFeat2, pointFeat2F, pointFeat3H, outLinksFeat2)
            helper.selectLinks(linksFeat3, pointFeat3F, pointFeat3H, outLinksFeat3)
            helper.selectLinks(linksFeat4, pointFeat3F, pointFeat2H, outLinksFeat4)

            helper.calculateFeatIDAngle(outLinksFeat1, pointFeat2F, pointFeat2H)
            helper.calculateFeatIDAngle(outLinksFeat2, pointFeat2F, pointFeat3H)
            helper.calculateFeatIDAngle(outLinksFeat3, pointFeat3F, pointFeat3H)
            helper.calculateFeatIDAngle(outLinksFeat4, pointFeat3F, pointFeat2H)

            arcpy.AddMessage("initial links generated at " + str(datetime.now()))
            # merge links
            outLinksFeat = "links_selected"
            itemList.append(outLinksFeat)
            fcList = [outLinksFeat1, outLinksFeat2, outLinksFeat3, outLinksFeat4]
            arcpy.Merge_management(fcList, outLinksFeat)
        else:
            # create only one set of links
            linksFeat = "links_all"
            itemList.append(linksFeat)

            arcpy.analysis.GenerateOriginDestinationLinks(
                pointFeat2F,
                pointFeat2H,
                linksFeat,
                search_distance=distanceT,
                distance_unit=linearUnit,
            )
            outLinksFeat = "links_selected"
            itemList.append(outLinksFeat)
            # select a subset of links
            helper.selectLinks(linksFeat, pointFeat2F, pointFeat2H, outLinksFeat)
            helper.calculateFeatIDAngle(outLinksFeat, pointFeat2F, pointFeat2H)

            arcpy.AddMessage("initial links generated at " + str(datetime.now()))

        # split the links into 12 subsets based on the from and to directions
        linksSN = "linksSN"
        itemList.append(linksSN)
        whereClause = "fromDirection = 'S' And toDirection = 'N'"
        arcpy.Select_analysis(outLinksFeat, linksSN, whereClause)

        linksNS = "linksNS"
        itemList.append(linksNS)
        whereClause = "fromDirection = 'N' And toDirection = 'S'"
        arcpy.Select_analysis(outLinksFeat, linksNS, whereClause)

        linksEW = "linksEW"
        itemList.append(linksEW)
        whereClause = "fromDirection = 'E' And toDirection = 'W'"
        arcpy.Select_analysis(outLinksFeat, linksEW, whereClause)

        linksWE = "linksWE"
        itemList.append(linksWE)
        whereClause = "fromDirection = 'W' And toDirection = 'E'"
        arcpy.Select_analysis(outLinksFeat, linksWE, whereClause)

        linksEN = "linksEN"
        itemList.append(linksEN)
        whereClause = "fromDirection = 'E' And toDirection = 'N'"
        arcpy.Select_analysis(outLinksFeat, linksEN, whereClause)

        linksNE = "linksNE"
        itemList.append(linksNE)
        whereClause = "fromDirection = 'N' And toDirection = 'E'"
        arcpy.Select_analysis(outLinksFeat, linksNE, whereClause)

        linksSW = "linksSW"
        itemList.append(linksSW)
        whereClause = "fromDirection = 'S' And toDirection = 'W'"
        arcpy.Select_analysis(outLinksFeat, linksSW, whereClause)

        linksWS = "linksWS"
        itemList.append(linksWS)
        whereClause = "fromDirection = 'W' And toDirection = 'S'"
        arcpy.Select_analysis(outLinksFeat, linksWS, whereClause)

        linksSE = "linksSE"
        itemList.append(linksSE)
        whereClause = "fromDirection = 'S' And toDirection = 'E'"
        arcpy.Select_analysis(outLinksFeat, linksSE, whereClause)

        linksES = "linksES"
        itemList.append(linksES)
        whereClause = "fromDirection = 'E' And toDirection = 'S'"
        arcpy.Select_analysis(outLinksFeat, linksES, whereClause)

        linksWN = "linksWN"
        itemList.append(linksWN)
        whereClause = "fromDirection = 'W' And toDirection = 'N'"
        arcpy.Select_analysis(outLinksFeat, linksWN, whereClause)

        linksNW = "linksNW"
        itemList.append(linksNW)
        whereClause = "fromDirection = 'N' And toDirection = 'W'"
        arcpy.Select_analysis(outLinksFeat, linksNW, whereClause)

        # further process the links
        outLinkFeatSN1 = "linksSN_1"
        outLinkFeatSN2 = "linksSN_2"
        itemList.append(outLinkFeatSN1)
        itemList.append(outLinkFeatSN2)
        helper.doLinks1(
            linksSN,
            outLinkFeatSN1,
            outLinkFeatSN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SN",
        )

        outLinkFeatNS1 = "linksNS_1"
        outLinkFeatNS2 = "linksNS_2"
        itemList.append(outLinkFeatNS1)
        itemList.append(outLinkFeatNS2)
        helper.doLinks1(
            linksNS,
            outLinkFeatNS1,
            outLinkFeatNS2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "NS",
        )

        outLinkFeatWE1 = "linksWE_1"
        outLinkFeatWE2 = "linksWE_2"
        itemList.append(outLinkFeatWE1)
        itemList.append(outLinkFeatWE2)
        helper.doLinks1(
            linksWE,
            outLinkFeatWE1,
            outLinkFeatWE2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "WE",
        )

        outLinkFeatEW1 = "linksEW_1"
        outLinkFeatEW2 = "linksEW_2"
        itemList.append(outLinkFeatEW1)
        itemList.append(outLinkFeatEW2)
        helper.doLinks1(
            linksEW,
            outLinkFeatEW1,
            outLinkFeatEW2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "EW",
        )

        outLinkFeatEN1 = "linksEN_1"
        outLinkFeatEN2 = "linksEN_2"
        itemList.append(outLinkFeatEN1)
        itemList.append(outLinkFeatEN2)
        helper.doLinks1(
            linksEN,
            outLinkFeatEN1,
            outLinkFeatEN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "EN",
        )

        outLinkFeatNE1 = "linksNE_1"
        outLinkFeatNE2 = "linksNE_2"
        itemList.append(outLinkFeatNE1)
        itemList.append(outLinkFeatNE2)
        helper.doLinks1(
            linksNE,
            outLinkFeatNE1,
            outLinkFeatNE2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "NE",
        )

        outLinkFeatSW1 = "linksSW_1"
        outLinkFeatSW2 = "linksSW_2"
        itemList.append(outLinkFeatSW1)
        itemList.append(outLinkFeatSW2)
        helper.doLinks1(
            linksSW,
            outLinkFeatSW1,
            outLinkFeatSW2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SW",
        )

        outLinkFeatWS1 = "linksWS_1"
        outLinkFeatWS2 = "linksWS_2"
        itemList.append(outLinkFeatWS1)
        itemList.append(outLinkFeatWS2)
        helper.doLinks1(
            linksWS,
            outLinkFeatWS1,
            outLinkFeatWS2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "WS",
        )

        outLinkFeatSE1 = "linksSE_1"
        outLinkFeatSE2 = "linksSE_2"
        itemList.append(outLinkFeatSE1)
        itemList.append(outLinkFeatSE2)
        helper.doLinks1(
            linksSE,
            outLinkFeatSE1,
            outLinkFeatSE2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "SE",
        )

        outLinkFeatES1 = "linksES_1"
        outLinkFeatES2 = "linksES_2"
        itemList.append(outLinkFeatES1)
        itemList.append(outLinkFeatES2)
        helper.doLinks1(
            linksES,
            outLinkFeatES1,
            outLinkFeatES2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "ES",
        )

        outLinkFeatWN1 = "linksWN_1"
        outLinkFeatWN2 = "linksWN_2"
        itemList.append(outLinkFeatWN1)
        itemList.append(outLinkFeatWN2)
        helper.doLinks1(
            linksWN,
            outLinkFeatWN1,
            outLinkFeatWN2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "WN",
        )

        outLinkFeatNW1 = "linksNW_1"
        outLinkFeatNW2 = "linksNW_2"
        itemList.append(outLinkFeatNW1)
        itemList.append(outLinkFeatNW2)
        helper.doLinks1(
            linksNW,
            outLinkFeatNW1,
            outLinkFeatNW2,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
            "NW",
        )

        # create initial lists
        linkFeatList = []
        linkFeatList.append(outLinkFeatSN2)
        linkFeatList.append(outLinkFeatNS2)
        linkFeatList.append(outLinkFeatWE2)
        linkFeatList.append(outLinkFeatEW2)
        linkFeatList.append(outLinkFeatEN2)
        linkFeatList.append(outLinkFeatNE2)
        linkFeatList.append(outLinkFeatSW2)
        linkFeatList.append(outLinkFeatWS2)
        linkFeatList.append(outLinkFeatSE2)
        linkFeatList.append(outLinkFeatES2)
        linkFeatList.append(outLinkFeatWN2)
        linkFeatList.append(outLinkFeatNW2)
        featID1List, featID2List, featIDListList, distList, angleList = (
            helper.createLists(linkFeatList)
        )
        arcpy.AddMessage("create lists done")

        # updates ids list and other lists when multiple elements share either "from" or "to" points
        # each outList1 element contains a list of featIDs
        list1, list2, outList1, list3, list4 = helper.doLists(
            featID1List,
            featID2List,
            featIDListList,
            distList,
            angleList,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
        )
        arcpy.AddMessage("do lists done at " + str(datetime.now()))
        # further updates ids list when multiple elements connected through sharing "from" and "to" points
        # each outList2 element contains a list of featIDs
        outList2 = helper.doLists1(
            list1,
            list2,
            outList1,
            list3,
            list4,
            distanceT,
            angleThreshold,
            distWeight,
            angleWeight,
        )
        arcpy.AddMessage("do lists1 done at " + str(datetime.now()))

        # merge elements of outList2 where appropriate (e.g., share at least one common id)
        leng1 = len(helper.getUnique(list(flatten(outList2))))
        arcpy.AddMessage("leng1:" + str(leng1))
        outList = helper.mergeList(outList2)
        leng2 = len(list(flatten(outList)))
        arcpy.AddMessage("leng2:" + str(leng2))
        # continue to merge until no more merge is possible
        while leng2 > leng1:
            arcpy.AddMessage("leng2:" + str(leng2))
            outList = helper.mergeList(outList)
            leng2 = len(list(flatten(outList)))
        arcpy.AddMessage("merge elements done at " + str(datetime.now()))

        # get the original featID list
        cursor = arcpy.SearchCursor(inFeat)
        featIDList = []
        for row in cursor:
            featID = row.getValue("featID")
            featIDList.append(featID)
        del cursor, row

        ### assign a same featID to features that have been identified as to be connected
        featIDNewList = featIDList.copy()
        for tempList in outList:
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = featIDList.index(idv)
                featureID = featIDList[index]
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]

        inFeat1 = "inFeat1"
        itemList.append(inFeat1)
        arcpy.Copy_management(inFeat, inFeat1)
        # update the featID
        cursor = arcpy.UpdateCursor(inFeat1)
        i = 0
        for row in cursor:
            featIDNew = featIDNewList[i]
            row.setValue("featID", featIDNew)
            cursor.updateRow(row)
            i += 1
        del cursor, row
        # merge connected features to generate output featureclass
        arcpy.Dissolve_management(inFeat1, dissolveFeat, "featID")
        arcpy.AddMessage("merge done")
        # call the helper function to re-calculate featID the output featureclass
        helper.calculateFeatID(dissolveFeat)
        # delete temporary data
        ##        HelperFunctions.deleteDataItems(itemList)

        return


# the helper functions are defined here
class helpers:      

    # This function gets unique values in a list
    def getUnique(self, l1):
        # l1: input list

        l2 = np.unique(np.asarray(l1)).tolist()
        return l2

    # This function gets the common element(s) between two lists and returns the number of these common element(s)
    def calculateCommon(self, l1, l2):
        # l1: first input list
        # l2: second input list

        l1_set = set(l1)
        intersection = l1_set.intersection(l2)
        return len(intersection)

    # This function gets unique values in a 2-D list
    def getUnique2D(self, l1):
        # l1: input 2-D list

        l2 = np.unique(np.asarray(l1), axis=0).tolist()
        return l2
    
    
    # This function adds and calculates unique featID field
    def calculateFeatID(self, inFeat):
        # inFeat: input features

        fieldName = "featID"
        fieldType = "Long"
        fieldPrecision = 6
        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(
                inFeat, fieldName, fieldType, field_precision=fieldPrecision
            )
        expression = "!OBJECTID!"
        arcpy.CalculateField_management(inFeat, fieldName, expression)
        return

    def calculateFeatIDAngle(self, inLinkFeat, originPointFeat, destPointFeat):
        field1 = "featID1"
        field2 = "angle1"  # orientation of the origin features
        inID = "ORIG_FID"
        joinID = "OBJECTID"
        expression = "!" + originPointFeat + "." + "featID" + "!"
        HelperFunctions.addLongField(inLinkFeat, originPointFeat, field1, inID, joinID, expression)
        expression = "!" + originPointFeat + "." + "angle" + "!"
        HelperFunctions.addField(inLinkFeat, originPointFeat, field2, inID, joinID, expression)

        field1 = "featID2"
        field2 = "angle2"  # orientation of the destination features
        inID = "DEST_FID"
        joinID = "OBJECTID"
        expression = "!" + destPointFeat + "." + "featID" + "!"
        HelperFunctions.addLongField(inLinkFeat, destPointFeat, field1, inID, joinID, expression)
        expression = "!" + destPointFeat + "." + "angle" + "!"
        HelperFunctions.addField(inLinkFeat, destPointFeat, field2, inID, joinID, expression)

        return

    
    # This function finds the polygon features that connect with each other (e.g, near_dist == 0)
    # and generate a new list of featID, with the connected features being assigned the same featID
    def findNewFeatIDs(self, inFeat, inIDList, nearIDList):
        # inFeat: input polygon features
        # inIDList: list of ids of individual input features that have connected features
        # nearIDList:  this list contains the ids of their nearest features

        cursor = arcpy.SearchCursor(inFeat)
        objectIDList = []
        featIDList = []
        for row in cursor:
            objectID = row.getValue("OBJECTID")
            featID = row.getValue("featID")
            featIDList.append(featID)
            objectIDList.append(objectID)
        del cursor, row

        tempListList = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 3], [1, 2, 3], [4, 9], [2, 3, 5], [6, 13]], first iteration
        anotherList = []  # flatten tempListList
        inIDArr = np.asarray(inIDList)
        inIDArrU = np.unique(inIDArr)
        i = 0
        # loop through each input feature
        while i < len(inIDList):
            tempList = []
            inID = inIDList[i]
            if inID not in anotherList:
                # get the id of its connected feature
                nearID = nearIDList[i]
                tempList.append(inID)
                tempList.append(nearID)
                tempArr = np.where(inIDArr == nearID)[
                    0
                ]  # the index position of the nearID

                for el in tempArr:
                    tempList.append(nearIDList[el])
                tempList = np.unique(np.asarray(tempList)).tolist()
                tempListList.append(tempList)
                # use the flatten function to convert 2-D list into 1-D list
                anotherList = list(flatten(tempListList))
            i += 1

        tempListList1 = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]], final results after more merge from tempListList
        tempListListCopy = tempListList.copy()  # deep copy
        while len(tempListList) > 0:
            tempList = tempListList[0]
            tempListCopy = tempList.copy()

            for tempList1 in tempListListCopy:
                # call the helper function to find the number of common elements bewtween the two lists
                leng = self.calculateCommon(tempListCopy, tempList1)
                if leng > 0:
                    tempListList.remove(tempList1)
                    for el in tempList1:
                        tempListCopy.append(el)
                    # call the helper function to get the unique values within a list
                    tempList3 = self.getUnique(tempListCopy)
                    tempListCopy = tempList3.copy()

            list1 = list(flatten(tempListCopy))
            list2 = self.getUnique(list1)
            tempListList1.append(list2)
            tempListListCopy = tempListList.copy()

        # generate a new list of featID
        # the connected features are assigned the same featID
        featIDNewList = featIDList.copy()
        for tempList in tempListList1:
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = objectIDList.index(idv)
                featureID = featIDList[index]
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]
        return featIDNewList

    # This function identifies the linear polygon features that can be connected
    # These features satitify the following conditions: 1. the distance between the head of one feature and the foot of another feature is less than a user-defined threshold,
    # 2.the two nearby features align in orientation with the intersecting angle < 45 degree.
    # Finally, this function generate a new list of featID, with the connected features being assigned the same featID
    def findNewFeatIDs_1(self, inFeat, headFeat, footFeat, distThreshold):
        # inFeat: input linear Bathymetric Low features
        # headFeat: input head features
        # footFeat: input foot features
        # distThreshold: a distance threshold used to evaluate the connecting condition

        ## connect features that have head to foot distance less than the distance threshold, and intersecting angle less than 45 degree

        ### calculate distances between the head and foot features
        itemList = []

        headFeat1 = "headFeat1"
        footFeat1 = "footFeat1"
        itemList.append(headFeat1)
        itemList.append(footFeat1)

        arcpy.Copy_management(headFeat, headFeat1)
        arcpy.Copy_management(footFeat, footFeat1)

        fieldName = "featID"
        HelperFunctions.deleteSelectedField(headFeat1, fieldName)
        HelperFunctions.deleteSelectedField(footFeat1, fieldName)

        fieldName = "rectangle_Orientation"
        HelperFunctions.deleteSelectedField(headFeat1, fieldName)
        HelperFunctions.deleteSelectedField(footFeat1, fieldName)

        headFeat2 = "headFeat2"
        footFeat2 = "footFeat2"
        itemList.append(headFeat2)
        itemList.append(footFeat2)
        ## use spatial join to copy the featID and rectangle_Orientation fields to the head and foot features
        arcpy.SpatialJoin_analysis(headFeat1, inFeat, headFeat2)
        arcpy.SpatialJoin_analysis(footFeat1, inFeat, footFeat2)
        # Calculates distances between head and foot features within the input distance threshold (searchRadius)
        nearTable = "head_foot_nearTable"
        itemList.append(nearTable)
        location = "NO_LOCATION"
        angle = "NO_ANGLE"
        closest = "ALL"
        searchRadius = distThreshold
        arcpy.GenerateNearTable_analysis(
            headFeat2,
            footFeat2,
            nearTable,
            search_radius=searchRadius,
            location=location,
            angle=angle,
            closest=closest,
        )

        ### get initial list of a pair of features that have head to foot distance less than the input distance threshold

        headIDList1 = []
        footIDList1 = []
        cursor = arcpy.SearchCursor(nearTable)
        for row in cursor:
            inFID = row.getValue("IN_FID")
            nearFID = row.getValue("NEAR_FID")
            headIDList1.append(inFID)
            footIDList1.append(nearFID)
        del cursor, row

        # get  attribute values from the input head features
        headIDAll = []
        headFeatIDAll = []
        headOrientationAll = []
        cursor = arcpy.SearchCursor(headFeat2)
        for row in cursor:
            objectID = row.getValue("OBJECTID")
            featID = row.getValue("featID")
            orientation = row.getValue("rectangle_Orientation")
            headIDAll.append(objectID)
            headFeatIDAll.append(featID)
            headOrientationAll.append(orientation)
        del cursor, row
        # get  attribute values from the input foot features
        footIDAll = []
        footFeatIDAll = []
        footOrientationAll = []
        cursor = arcpy.SearchCursor(footFeat2)
        for row in cursor:
            objectID = row.getValue("OBJECTID")
            featID = row.getValue("featID")
            orientation = row.getValue("rectangle_Orientation")
            footIDAll.append(objectID)
            footFeatIDAll.append(featID)
            footOrientationAll.append(orientation)
        del cursor, row

        headFeatIDList1 = []
        footFeatIDList1 = []
        headOrientationList1 = []
        footOrientationList1 = []

        for idv in headIDList1:
            featID = headFeatIDAll[headIDAll.index(idv)]
            orientation = headOrientationAll[headIDAll.index(idv)]
            headFeatIDList1.append(featID)
            headOrientationList1.append(orientation)

        for idv in footIDList1:
            featID = footFeatIDAll[footIDAll.index(idv)]
            orientation = footOrientationAll[footIDAll.index(idv)]
            footFeatIDList1.append(featID)
            footOrientationList1.append(orientation)

        ### calculate intersecting angles for the feature pairs
        angleList = []
        i = 0
        while i < len(headOrientationList1):
            orientation1 = headOrientationList1[i]
            orientation2 = footOrientationList1[i]
            orientation_diff = abs(orientation1 - orientation2)
            angleList.append(orientation_diff)
            i += 1

        ### select feature pairs that have intersecting angle less than 45 degree
        idListList1 = []
        headFeatIDList2 = []
        footFeatIDList2 = []
        i = 0
        while i < len(angleList):
            angle = angleList[i]
            headFeatID = headFeatIDList1[i]
            footFeatID = footFeatIDList1[i]
            if (angle < 45) or (angle > 135):
                idListList1.append([headFeatID, footFeatID])
                headFeatIDList2.append(headFeatID)
                footFeatIDList2.append(footFeatID)
            i += 1

        ### merge feature pairs if they share a common feature
        idListList2 = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]],
        i = 0
        headIDArray = np.asarray(headFeatIDList2)
        footIDArray = np.asarray(footFeatIDList2)
        while i < len(idListList1):
            tempList = []
            ids = idListList1[i]
            headID = headFeatIDList2[i]
            footID = footFeatIDList2[i]

            if (
                headFeatIDList2.count(headID) > 1
            ):  # if multiple pairs share the same headID (e.g. [1,2],[1,3]), select the feature pair with the minimum intersecting angle
                indices = np.where(headIDArray == headID)[0]
                angleListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                ids1 = idListList1[angleList.index(min(angleListTemp))]
                if ids1 not in idListList2:
                    idListList2.append(ids1)
            elif (
                footFeatIDList2.count(footID) > 1
            ):  # if multiple pairs share the same footID (e.g. [2,1],[3,1]), select the feature pair with the minimum intersecting angle
                indices = np.where(footIDArray == footID)[0]
                angleListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                ids1 = idListList1[angleList.index(min(angleListTemp))]
                if ids1 not in idListList2:
                    idListList2.append(ids1)
            elif (
                headID in footFeatIDList2
            ):  # if two pairs (e.g., [2,1],[5,2]), indicates the three features are connected, so add both pairs
                ids1 = idListList1[footFeatIDList2.index(headID)]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in idListList2:
                    idListList2.append(tempList)
            elif (
                footID in headFeatIDList2
            ):  # if two pairs (e.g., [1,2],[2,5]), indicates the three features are connected, so add both pairs
                ids1 = idListList1[headFeatIDList2.index(footID)]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in idListList2:
                    idListList2.append(tempList)
            else:  # otherwise, just keep the pair
                idListList2.append(ids)
            i += 1

        cursor = arcpy.SearchCursor(inFeat)
        featIDList = []
        for row in cursor:
            featID = row.getValue("featID")
            featIDList.append(featID)
        del cursor, row

        ### assign a same featID to features to be connected
        featIDNewList = featIDList.copy()
        for tempList in idListList2:
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = featIDList.index(idv)
                featureID = featIDList[index]
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]

        return featIDNewList

    # This function gets a count of feature sharing by borders and merges input features sharing points
    def mergeFeatures(self, inFeat, dissolveFeat, dissolveFeat1, dissolveFeat2):
        # inFeat: input features
        # dissolveFeat: input features after merging features sharing borders and points
        # dissolveFeat1: input features after merging only features sharing borders
        # dissolvedFeat2: output features after merging only features sharing points

        itemList = []

        # select individual input features that share points and those stand-alone features
        tempLayer = "tempLyr"
        arcpy.MakeFeatureLayer_management(inFeat, tempLayer)
        arcpy.SelectLayerByLocation_management(
            tempLayer, "ARE_IDENTICAL_TO", dissolveFeat1
        )
        selectFeat1 = "selectFeat1"
        itemList.append(selectFeat1)
        arcpy.CopyFeatures_management(tempLayer, selectFeat1)
        arcpy.AddMessage(selectFeat1 + " done")
        # select dissolved features sharing points and stand-alone features
        tempLayer = "tempLyr"
        arcpy.MakeFeatureLayer_management(dissolveFeat, tempLayer)
        arcpy.SelectLayerByLocation_management(tempLayer, "intersect", selectFeat1)
        selectFeat2 = "selectFeat2"
        itemList.append(selectFeat2)
        arcpy.CopyFeatures_management(tempLayer, selectFeat2)
        arcpy.AddMessage(selectFeat2 + " done")
        # select individual input features sharing borders
        tempLayer = "tempLyr"
        arcpy.MakeFeatureLayer_management(inFeat, tempLayer)
        arcpy.SelectLayerByLocation_management(
            tempLayer,
            "ARE_IDENTICAL_TO",
            dissolveFeat1,
            invert_spatial_relationship="INVERT",
        )
        selectFeat3 = "selectFeat3"
        itemList.append(selectFeat3)
        arcpy.CopyFeatures_management(tempLayer, selectFeat3)
        arcpy.AddMessage(selectFeat3 + " done")

        count = int(arcpy.GetCount_management(selectFeat3).getOutput(0))
        # erase features that share borders from selected dissolved features sharing points and stand-alone features
        erasedFeat = "easedFeat"
        itemList.append(erasedFeat)
        arcpy.Erase_analysis(selectFeat2, selectFeat3, erasedFeat)

        # select individual input features sharing both borders and points
        tempLayer = "tempLyr"
        arcpy.MakeFeatureLayer_management(selectFeat3, tempLayer)
        arcpy.SelectLayerByLocation_management(
            tempLayer,
            "BOUNDARY_TOUCHES",
            erasedFeat,
            invert_spatial_relationship="INVERT",
        )
        selectFeat3_1 = "selectFeat3_1"
        itemList.append(selectFeat3_1)
        arcpy.CopyFeatures_management(tempLayer, selectFeat3_1)
        arcpy.AddMessage(selectFeat3_1 + " done")

        # erase features that share borders from dissolved features sharing points and stand-alone features
        erasedFeat1 = "easedFeat1"
        itemList.append(erasedFeat1)
        arcpy.Erase_analysis(dissolveFeat, selectFeat3_1, erasedFeat1)

        # merge features in the erased and fourth sets
        # which results in output features after merging features sharing points
        inFeats = [erasedFeat1, selectFeat3_1]
        arcpy.Merge_management(inFeats, dissolveFeat2)
        itemList.append(tempLayer)
        ##        HelperFunctions.deleteDataItems(itemList)
        return count

   
    # This function lists duplicated elements
    def RiteshKumar(self, inList):
        return list({x for x in inList if inList.count(x) > 1})

    # This function selects two subsets from the input link features
    def doLinks1(
        self,
        inLinkFeat,
        outLinkFeat1,
        outLinkFeat2,
        distThreshold,
        angleThreshold,
        distWeight,
        angleWeight,
        linkDirection,
    ):
        # inLinkFeat: input link featureclass obtained from the GenerateOriginDestinationLinks ArcGIS tool
        # outLinkFeat1: output link featureclass after the first selection
        # outLinkFeat2: output link featureclass after the second selection
        # distThreshold: threshold value for distance between two nearby features
        # angleThreshold: threshold value for the intersecting angle between two nearby features
        # distWeight: weight assigned to distance, used to calculate a combined metric from the distance and angle metrics (used in getIndex())
        # angleWeight: weight assigned to angle, used to calculate a combined metric from the distance and angle metrics (used in getIndex())
        # linkDirection: a text string indicating the link direction to be processed

        # add and calculate a number of fields

        fields = arcpy.ListFields(inLinkFeat)
        fieldNames = [f.name for f in fields]

        fieldType = "LONG"
        fieldPrecision = 15
        fieldName = "tempID"
        if fieldName not in fieldNames:
            arcpy.AddField_management(inLinkFeat, fieldName, fieldType, fieldPrecision)
        expression = "!OBJECTID!"
        arcpy.CalculateField_management(inLinkFeat, fieldName, expression, "PYTHON3")

        if linkDirection != "FH":
            fieldType = "DOUBLE"
            fieldPrecision = 15
            fieldScale = 6
            fieldName = "idRatio"
            if fieldName not in fieldNames:
                arcpy.AddField_management(
                    inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
                )
            expression = "!ORIG_FID! / !DEST_FID!"
            arcpy.CalculateField_management(
                inLinkFeat, fieldName, expression, "PYTHON3"
            )

        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = "angle_diff"
        if fieldName not in fieldNames:
            arcpy.AddField_management(
                inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )
        expression = "getAngle(abs(!angle1! - !angle2!))"

        codeblock = """
def getAngle(inAngle):
    if(inAngle > 90):
        return 180 - inAngle
    else:
        return inAngle"""

        arcpy.CalculateField_management(
            inLinkFeat, fieldName, expression, "PYTHON3", codeblock
        )

        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = "X_diff"  # whether the origin feature is to the east or west of the destination feature
        if fieldName not in fieldNames:
            arcpy.AddField_management(
                inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )
        expression = "!ORIG_X! - !DEST_X!"
        arcpy.CalculateField_management(inLinkFeat, fieldName, expression, "PYTHON3")

        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = "Y_diff"  # whether the origin feature is to the south or north of the destination feature
        if fieldName not in fieldNames:
            arcpy.AddField_management(
                inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )
        expression = "!ORIG_Y! - !DEST_Y!"
        arcpy.CalculateField_management(inLinkFeat, fieldName, expression, "PYTHON3")

        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = (
            "link_angle"  # orientation of the links in relative to north (0-180)
        )
        if fieldName not in fieldNames:
            arcpy.AddField_management(
                inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )
        expression = "getAngle(!X_diff!,!Y_diff!)"
        codeblock = """
def getAngle(x,y):
    if y ==0:
        return 90
    else:
        inAngle = math.degrees(math.atan(x/y))
        
    if(inAngle < 0):
        return 180 + inAngle
    else:
        return inAngle"""

        arcpy.CalculateField_management(
            inLinkFeat, fieldName, expression, "PYTHON3", codeblock
        )

        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = "link_angle_diff"
        if fieldName not in fieldNames:
            arcpy.AddField_management(
                inLinkFeat, fieldName, fieldType, fieldPrecision, fieldScale
            )
        expression = "(getAngle(abs(!angle1! - !link_angle!)) + getAngle(abs(!angle2! - !link_angle!))) / 2"
        codeblock = """
def getAngle(inAngle):
    if(inAngle > 90):
        return 180 - inAngle
    else:
        return inAngle"""

        arcpy.CalculateField_management(
            inLinkFeat, fieldName, expression, "PYTHON3", codeblock
        )

        arcpy.AddMessage("fields added and calculated")

        # select a subset, removing self-links (e.g., from S point of a feature to the N point of the same feature, indicated by 'temp == 1')
        # removing links with angle_diff larger than the angle threshold
        linkTempFeat = "linkTempFeat"
        if linkDirection == "FH":
            whereClause = "angle_diff < " + str(angleThreshold)
        else:
            whereClause = (
                "(idRatio <> 1) And (angle_diff < " + str(angleThreshold) + ")"
            )
        arcpy.Select_analysis(inLinkFeat, linkTempFeat, whereClause)

        # further select from the above subset based on the speficied criteria for the link direction
        inFeatCount = int(arcpy.GetCount_management(linkTempFeat).getOutput(0))
        linkTempFeat1 = "linkTempFeat1"
        # inFeatCount = 0 indicates that there is not any feature satsifying the criterion specified (angle_diff < angleThreshold) for the link direction.
        if inFeatCount > 0:
            # These four threshold values are hard-coded here, for the time being.
            # They could be changed if deemed not suitable.
            # The other option is to expose these threshold values on the tool interface for user-input.
            laT = float(angleThreshold) + 20.0
            dT = float(distThreshold) * 0.3
            distT1 = 0.2 * float(distThreshold)
            distT2 = -0.2 * float(distThreshold)
            # Different link directions require different selection criteria.
            if linkDirection == "SN":
                # two "Or" conditions: 1. the northern feature is at some distance north of the southern feature (Y_diff attribute) and the two features have similar orientations (within a threshold)(link_angle_diff attribute); or
                # 2. the northern and southern features are close together in both the north-south direction (Y_diff attribute) and link direction (LINK_DIST attribute)
                whereClause = (
                    "((Y_diff >"
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + "))"
                    + " Or ((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ") And (LINK_DIST < "
                    + str(dT)
                    + "))"
                )
            elif linkDirection == "NS":
                # two "Or" conditions: 1. the southern feature is at some distance south of the northern feature (Y_diff attribute) and the two features have similar orientations (within a threshold)(link_angle_diff attribute); or
                # 2. the northern and southern features are close together in both the north-south direction (Y_diff attribute) and link direction (LINK_DIST attribute)
                whereClause = (
                    "((Y_diff <"
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + "))"
                    + " Or ((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ") And (LINK_DIST < "
                    + str(dT)
                    + "))"
                )
            elif linkDirection == "WE":
                # two "Or" conditions: 1. the western feature is at some distance west of the eastern feature (X_diff attribute) and the two features have similar orientations (within a threshold); or
                # 2. the western and eastern features are close together in both the east-west direction (X_diff attribute) and link direction
                whereClause = (
                    "((X_diff >"
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + "))"
                    + " Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + ") And (LINK_DIST < "
                    + str(dT)
                    + "))"
                )
            elif linkDirection == "EW":
                # two "Or" conditions: 1. the eastern feature is at some distance east of the western feature (X_diff attribute) and the two features have similar orientations (within a threshold); or
                # 2. the western and eastern features are close together in both the east-west direction (X_diff attribute) and link direction
                whereClause = (
                    "((X_diff <"
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + "))"
                    + " Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + ") And (LINK_DIST < "
                    + str(dT)
                    + "))"
                )
            elif linkDirection == "EN":
                # several "And" conditons: 1. the orientation of the eastern feature (angle1 attribute) must be 90-135; and 2. the orientation of the northern feature (anlge2 attribute) must be 135-180; and
                # 3. a complex "Or" conditon: a) the eastern feature and the northern feature must be at some distant away from each other in both N-S (Y_diff attribute) and E-W (X_diff attribute) directions
                # and the two features have similar orientations (within a threshold); or
                # b) the eastern feature and the northern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle1 >= 90) And (angle1 <= 135) And (angle2 >= 135) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff > "
                    + str(distT1)
                    + ") And (X_diff < "
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "NE":
                # several "And" conditons: 1. the orientation of the northern feature (angle1 attribute) must be 135-180; and 2. the orientation of the eastern feature (anlge1 attribute) must be 135-180; and
                # 3. a complex "Or" conditon: a) the northern feature and the eastern feature must be at some distant away from each other in both N-S (Y_diff attribute) and E-W (X_diff attribute) directions
                # and the two features have similar orientations (within a threshold); or
                # b) the eastern feature and the northern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle2 >= 90) And (angle2 <= 135) And (angle1 >= 135) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff < "
                    + str(distT2)
                    + ") And (X_diff > "
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "SW":
                # several "And" conditons: 1. the orientation of the southern feature must be 135-180; and 2. the orientation of the western feature must be 90-135; and
                # 3. a complex "Or" conditon: a) the southern feature and the western feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the southern feature and the western feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle1 >= 135) And (angle2 >= 90) And (angle2 <= 135) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff > "
                    + str(distT1)
                    + ") And (X_diff < "
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "WS":
                # several "And" conditons: 1. the orientation of the western feature must be 90-135; and 2. the orientation of the southern feature must be 135-180; and
                # 3. a complex "Or" conditon: a) the western feature and the southern feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the southern feature and the western feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle2 >= 135) And (angle1 >= 90) And (angle1 <= 135) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff < "
                    + str(distT2)
                    + ") And (X_diff > "
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "SE":
                # several "And" conditons: 1. the orientation of the southern feature must be 0-45; and 2. the orientation of the eastern feature must be 45-90; and
                # 3. a complex "Or" conditon: a) the southern feature and the eastern feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the southern feature and the eastern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle1 <= 45) And (angle2 >= 45) And (angle2 <= 90) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff > "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "ES":
                # several "And" conditons: 1. the orientation of the eastern feature must be 45-90; and 2. the orientation of the eastern feature must be 0-45; and
                # 3. a complex "Or" conditon: a) the southern feature and the eastern feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the southern feature and the eastern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle2 <= 45) And (angle1 >= 45) And (angle1 <= 90) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff < "
                    + str(distT2)
                    + ") And (X_diff < "
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "WN":
                # several "And" conditons: 1. the orientation of the western feature must be 45-90; and 2. the orientation of the northern feature must be 0-45; and
                # 3. a complex "Or" conditon: a) the western feature and the northern feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the western feature and the northern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle1 >= 45) And (angle1 <= 90) And (angle2 <= 45) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff > "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT1)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif linkDirection == "NW":
                # several "And" conditons: 1. the orientation of the northern feature must be 0-45; and 2. the orientation of the western feature must be 45-90; and
                # 3. a complex "Or" conditon: a) the northern feature and the western feature must be at some distant away from each other in both N-S and E-W directions and the two features have similar orientations (within a threshold); or
                # b) the western feature and the northern feature must be close in link direction and also close in either the N-S or E-W direction
                whereClause = (
                    "(angle2 >= 45) And (angle2 <= 90) And (angle1 <= 45) And "
                    + "(((((Y_diff < "
                    + str(distT1)
                    + ") And (Y_diff > "
                    + str(distT2)
                    + ")) Or ((X_diff < "
                    + str(distT1)
                    + ") And (X_diff > "
                    + str(distT2)
                    + "))) And (link_dist < "
                    + str(dT)
                    + ")) Or ((Y_diff < "
                    + str(distT2)
                    + ") And (X_diff < "
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + ")))"
                )
            elif (
                linkDirection == "FH"
            ):  # connect foot to head features, not longer in use
                # two "Or" conditions: 1. the two features are close together in both north-south and east-west directions (X_diff and Y_diff attributes) and link direction (LINK_DIST attribute); or
                # 2. the two features are not close in either north-south (Y_diff attribute) or east-west directions (X_diff attribute) and they have similar orientations (within a threshold) (link_angle_diff attribute).
                whereClause = (
                    "((X_diff <= "
                    + str(distT1)
                    + " And X_diff >= "
                    + str(distT2)
                    + " And Y_diff <= "
                    + str(distT1)
                    + " And Y_diff >= "
                    + str(distT2)
                    + ") AND (LINK_DIST < "
                    + str(dT)
                    + ")) OR ((X_diff > "
                    + str(distT1)
                    + " Or X_diff < "
                    + str(distT2)
                    + " Or Y_diff > "
                    + str(distT2)
                    + " Or Y_diff < "
                    + str(distT2)
                    + ") And (link_angle_diff < "
                    + str(laT)
                    + "))"
                )

            arcpy.Select_analysis(linkTempFeat, linkTempFeat1, whereClause)
        else:
            arcpy.Copy_management(linkTempFeat, linkTempFeat1)

        arcpy.AddMessage("first selection done")

        # further selection
        inFeatCount = int(arcpy.GetCount_management(linkTempFeat1).getOutput(0))
        if inFeatCount > 0:
            # here is different between the combined option and the other two options
            # the combined option would likely generate multiple records have the same [originID,destID]
            # we need to select the one with minimum distance
            cursor = arcpy.SearchCursor(linkTempFeat1)
            tempIDList = []
            originIDList = []
            destIDList = []
            distList = []
            idListList = []
            for row in cursor:
                tempID = row.getValue("tempID")
                originID = row.getValue("ORIG_FID")
                destID = row.getValue("DEST_FID")
                dist = row.getValue("LINK_DIST")
                idList = [originID, destID]
                tempIDList.append(tempID)
                originIDList.append(originID)
                destIDList.append(destID)
                distList.append(dist)
                idListList.append(idList)
            del row, cursor

            leng1 = len(idListList)
            idListList1 = self.getUnique2D(idListList)
            leng2 = len(idListList1)
            if (
                leng1 > leng2
            ):  # Mid points and Most distant points option (ie. the combined option) selected
                i = 0
                tempIDList1 = []
                idsArray = np.asarray(idListList)
                while i < leng2:  # loop through each unique [originID,destID]
                    idList = idListList1[i]
                    indices = np.where(
                        (idsArray[:, 0] == idList[0]) & (idsArray[:, 1] == idList[1])
                    )[0]
                    indexList = indices.tolist()
                    distListTemp = []
                    for index in indices:
                        dist = distList[index]
                        distListTemp.append(dist)
                    # select the index with minimum distance
                    j = indexList[distListTemp.index(min(distListTemp))]
                    tempIDList1.append(tempIDList[j])
                    i += 1
                # select subset
                text = "("
                for j in tempIDList1:
                    text = text + str(j) + ","
                text = text[0:-1] + ")"
                whereClause = "tempID IN " + text
                arcpy.Select_analysis(linkTempFeat1, outLinkFeat1, whereClause)

            else:  # one of the other two options selected
                arcpy.Copy_management(linkTempFeat1, outLinkFeat1)
        else:
            arcpy.Copy_management(linkTempFeat1, outLinkFeat1)
        arcpy.AddMessage("second selection done")

        # further selection
        inFeatCount = int(arcpy.GetCount_management(outLinkFeat1).getOutput(0))
        if inFeatCount > 0:
            # doing the third selection
            # if multiple records have the same ORIG_FID or DEST_ID (eg., between [1,3] and [1,4] or between [1,10] and [2,10]),
            # just select the one with min combination of distance and angle_diff
            cursor = arcpy.SearchCursor(outLinkFeat1)
            tempIDList = []
            originIDList = []
            destIDList = []
            distList = []
            angleList = []
            for row in cursor:
                tempID = row.getValue("tempID")
                originID = row.getValue("ORIG_FID")
                destID = row.getValue("DEST_FID")
                dist = row.getValue("LINK_DIST")
                angle = row.getValue("angle_diff")
                tempIDList.append(tempID)
                originIDList.append(originID)
                destIDList.append(destID)
                distList.append(dist)
                angleList.append(angle)
            del row, cursor
            inIDListList = []
            i = 0
            while i < len(originIDList):
                te = [originIDList[i], destIDList[i]]
                inIDListList.append(te)
                i += 1
            # call the doLists() function to conduct the selection
            list1, list2, list3, list4, list5 = self.doLists(
                originIDList,
                destIDList,
                inIDListList,
                distList,
                angleList,
                distThreshold,
                angleThreshold,
                distWeight,
                angleWeight,
            )
            tempIDList1 = []
            # update the list
            for l in list3:
                i = inIDListList.index(l)
                tempIDList1.append(tempIDList[i])

            # select subset
            text = "("
            for i in tempIDList1:
                text = text + str(i) + ","
            text = text[0:-1] + ")"
            whereClause = "tempID IN " + text
            arcpy.Select_analysis(outLinkFeat1, outLinkFeat2, whereClause)
        else:
            arcpy.Copy_management(outLinkFeat1, outLinkFeat2)
        arcpy.AddMessage("third selection done")

        arcpy.Delete_management(linkTempFeat)
        arcpy.Delete_management(linkTempFeat1)

    # This function gets the indices based on distance and angle criteria
    def getIndex(
        self,
        indexList,
        distList,
        angleList,
        distThreshold,
        angleThreshold,
        distWeight,
        angleWeight,
    ):
        # indexList: initial index list
        # distList: initial distance list
        # angleList: initial angle list
        # distThreshold: threshold value for distance between two nearby features
        # angleThreshold: threshold value for the intersecting angle between two nearby features
        # distWeight: weight assigned to distance, used to calculate a combination metric from distance and angle
        # angleWeight: weight assigned to angle, used to calculate a combination metric from distance and angle

        distThreshold = float(distThreshold)
        angleThreshold = float(angleThreshold)
        distWeight = float(distWeight)
        angleWeight = float(angleWeight)

        cL = []  # elements in list cL are calculated from distance and angle
        i = 0
        while i < len(distList):
            d = distList[i] / distThreshold
            a = angleList[i] / angleThreshold
            # calculate weighted average from distWeight and angleWeight
            c = (d * distWeight + a * angleWeight) / (distWeight + angleWeight)
            cL.append(c)
            i += 1

        cArr = np.asarray(cL)
        indices = np.where(cArr == np.min(cArr))[0]
        # if multiple elements satisfying the minimum criteria, select the one with a smaller anlge
        if len(indices) > 1:
            aList = []
            for i in indices:
                aList.append(angleList[i])
            return indexList[angleList.index(min(aList))]
        else:
            return indexList[indices[0]]

    # This function updates ids list when multiple elements share "from" or "to" points
    def doLists(
        self,
        featID1List,
        featID2List,
        inIDListList,
        distList,
        angleList,
        distThreshold,
        angleThreshold,
        distWeight,
        angleWeight,
    ):
        # featID1List: featIDs of the "from" points
        # featID2List: featIDs of the "to" points
        # inIDListList: list of [featID1,featID2]
        # distList: distance list
        # angleList: angle List
        # distThreshold: threshold value for distance between two nearby features
        # angleThreshold: threshold value for the intersecting angle between two nearby features
        # distWeight: weight assigned to distance, used to calculate a combination metric from distance and angle (used in getIndex())
        # angleWeight: weight assigned to angle, used to calculate a combination metric from distance and angle (used in getIndex())

        # first round, doing features sharing featID1 (featID of the from point)
        # each element in outIDListList1 contains ids of connected features
        # e.g. [[1, 2, 3, 5], [4, 9], [6, 13]]
        outIDListList1 = []
        featID1List1 = []
        featID2List1 = []
        distList1 = []
        angleList1 = []
        i = 0
        featID1Array = np.asarray(featID1List)
        featID2Array = np.asarray(featID2List)
        while i < len(inIDListList):  # loop through each [featID1,featID2]
            tempList = []
            ids = inIDListList[i]
            featID1 = featID1List[i]
            featID2 = featID2List[i]
            dist = distList[i]
            angle = angleList[i]
            # if multiple pairs share the same featID1
            # (e.g. [1,2],[1,3]), select the feature pair with the minimum combination of
            # intersecting angle and distance
            if featID1List.count(featID1) > 1:
                indices = np.where(featID1Array == featID1)[0]
                indexList = indices.tolist()
                angleListTemp = []
                distListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                    dist = distList[index]
                    distListTemp.append(dist)
                # call the getIndex()
                j = self.getIndex(
                    indexList,
                    distListTemp,
                    angleListTemp,
                    distThreshold,
                    angleThreshold,
                    distWeight,
                    angleWeight,
                )
                ids1 = inIDListList[j]
                # only append the list if it is not already in the existing list of lists
                if ids1 not in outIDListList1:
                    outIDListList1.append(ids1)
            else:  # otherwise, just keep the pair
                outIDListList1.append(ids)
            i += 1
        # update lists
        for l in outIDListList1:
            i = inIDListList.index(l)
            featID1List1.append(featID1List[i])
            featID2List1.append(featID2List[i])
            distList1.append(distList[i])
            angleList1.append(angleList[i])

        # second round, doing features sharing featID2
        # the inputs are the updated lists from the first round
        outIDListList2 = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]],
        featID1List2 = []
        featID2List2 = []
        distList2 = []
        angleList2 = []
        i = 0

        featID1Array = np.asarray(featID1List1)
        featID2Array = np.asarray(featID2List1)
        while i < len(outIDListList1):
            tempList = []
            ids = outIDListList1[i]
            featID1 = featID1List1[i]
            featID2 = featID2List1[i]
            dist = distList1[i]
            angle = angleList1[i]
            # if multiple pairs share the same featID2
            # (e.g. [3,2],[4,2]), select the feature pair with the minimum combination of
            # intersecting angle and distance
            if featID2List1.count(featID2) > 1:
                indices = np.where(featID2Array == featID2)[0]
                indexList = indices.tolist()
                angleListTemp = []
                distListTemp = []
                for index in indices:
                    angle = angleList1[index]
                    angleListTemp.append(angle)
                    dist = distList1[index]
                    distListTemp.append(dist)
                j = self.getIndex(
                    indexList,
                    distListTemp,
                    angleListTemp,
                    distThreshold,
                    angleThreshold,
                    distWeight,
                    angleWeight,
                )
                ids1 = outIDListList1[j]
                # only append the list if it is not already in the existing list of lists
                if ids1 not in outIDListList2:
                    outIDListList2.append(ids1)
            else:  # otherwise, just keep the pair
                outIDListList2.append(ids)
            i += 1
        for l in outIDListList2:
            i = outIDListList1.index(l)
            featID1List2.append(featID1List1[i])
            featID2List2.append(featID2List1[i])
            distList2.append(distList1[i])
            angleList2.append(angleList1[i])
        return featID1List2, featID2List2, outIDListList2, distList2, angleList2

    # This function further updates ids list when multiple elements connected through sharing "from" and "to" points
    # must be called after doLists() (e.g., using the outputs from doLists() as inputs)
    def doLists1(
        self,
        featID1List,
        featID2List,
        inIDListList,
        distList,
        angleList,
        distThreshold,
        angleThreshold,
        distWeight,
        angleWeight,
    ):
        # featID1List: featIDs of the "from" points
        # featID2List: featIDs of the "to" points
        # inIDListList: list of [featID1,featID2]
        # distList: distance list
        # angleList: angle List
        # distThreshold: threshold value for distance between two nearby features
        # angleThreshold: threshold value for the intersecting angle between two nearby features
        # distWeight: weight assigned to distance, used to calculate a combination metric from distance and angle (used in getIndex())
        # angleWeight: weight assigned to angle, used to calculate a combination metric from distance and angle (used in getIndex())

        outListList = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]],
        i = 0
        featID1Array = np.asarray(featID1List)
        featID2Array = np.asarray(featID2List)
        while i < len(inIDListList):
            tempList = []
            ids = inIDListList[i]
            featID1 = featID1List[i]
            featID2 = featID2List[i]

            if (
                featID2List.count(featID1) > 0
            ):  # if two pairs (e.g., [2,1],[5,2]), indicates the three features are connected, so add both pairs
                indices = np.where(featID2Array == featID1)[0]
                indexList = indices.tolist()
                angleListTemp = []
                distListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                    dist = distList[index]
                    distListTemp.append(dist)
                j = self.getIndex(
                    indexList,
                    distListTemp,
                    angleListTemp,
                    distThreshold,
                    angleThreshold,
                    distWeight,
                    angleWeight,
                )
                ids1 = inIDListList[j]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in outListList:
                    outListList.append(tempList)
            elif (
                featID1List.count(featID2) > 0
            ):  # if two pairs (e.g., [1,2],[2,5]), indicates the three features are connected, so add both pairs
                indices = np.where(featID1Array == featID2)[0]
                indexList = indices.tolist()
                angleListTemp = []
                distListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                    dist = distList[index]
                    distListTemp.append(dist)
                j = self.getIndex(
                    indexList,
                    distListTemp,
                    angleListTemp,
                    distThreshold,
                    angleThreshold,
                    distWeight,
                    angleWeight,
                )
                ids1 = inIDListList[j]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in outListList:
                    outListList.append(tempList)
            else:  # otherwise, just keep the pair
                outListList.append(ids)
            i += 1
        return outListList

    # This function merges common elements from multiple lists into one list
    def mergeList(self, inList):
        # inList: input list (of list) which contains multiple lists of featIDs

        tempListList1 = (
            []
        )  # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]], final results after more merge from tempListList
        tempListListCopy = inList.copy()  # deep copy
        # each loop remove an element list from inList, until none left
        # at the same time, build a new list (of list)
        while len(inList) > 0:
            tempList = inList[0]
            tempListCopy = tempList.copy()
            # compare the element with all elements in the list one by one
            for tempList1 in tempListListCopy:
                # call the helper function to find the number of common elements bewtween the two lists
                leng = self.calculateCommon(tempListCopy, tempList1)
                if leng > 0:
                    inList.remove(tempList1)
                    for el in tempList1:
                        tempListCopy.append(el)
                    # call the helper function to get the unique values within a list
                    tempList3 = self.getUnique(tempListCopy)
                    tempListCopy = tempList3.copy()

            list1 = list(flatten(tempListCopy))
            list2 = self.getUnique(list1)
            tempListList1.append(list2)
            tempListListCopy = inList.copy()
        return tempListList1

    def createLists(self, linkFeatList):
        # linkFeat1List: a list of input link features
        featID1List = []
        featID2List = []
        featIDListList = []
        angleList = []
        distList = []

        for linkFeat in linkFeatList:
            inFeatCount = int(arcpy.GetCount_management(linkFeat).getOutput(0))
            arcpy.AddMessage(linkFeat + " has " + str(inFeatCount) + " features.")
            if inFeatCount > 0:
                cursor = arcpy.SearchCursor(linkFeat)
                for row in cursor:
                    angle = row.getValue("angle_diff")
                    dist = row.getValue("LINK_DIST")
                    angleList.append(angle)
                    distList.append(dist)
                    featID1 = row.getValue("featID1")
                    featID2 = row.getValue("featID2")
                    featID1List.append(featID1)
                    featID2List.append(featID2)
                    tempList = []
                    tempList.append(featID1)
                    tempList.append(featID2)
                    featIDListList.append(tempList)

                del cursor, row
        return featID1List, featID2List, featIDListList, distList, angleList

    # This function generate direction point features from the input features and the bounding rectangle features
    # This one would potentially resulted in a small number of incorrect points, e.g., two points on different features may be on the same line
    def getDirectionPoints_old(
        self, inFeatClass, MbrLineClass, tempFolder, outPointFeat
    ):
        # inFeatClass: featureclass represents the polygons to be connected (input Bathymetric High features)
        # MbrLineClass: a subset of the lines from the minimum bounding rectangles of inFeatClass; for each feature there are two lines, either N and S or E and W.
        # tempFolder: folder location to store temporary files
        # outPointFeat: output direction point features

        inFeatVertices = "inFeatVertices"
        # convert each input feature to points;
        arcpy.FeatureVerticesToPoints_management(inFeatClass, inFeatVertices, "ALL")

        layer1 = "layer1"
        arcpy.MakeFeatureLayer_management(inFeatVertices, layer1)
        # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
        arcpy.SelectLayerByLocation_management(layer1, "INTERSECT", MbrLineClass)
        selectedPoints = "selectedPoints1"
        arcpy.CopyFeatures_management(layer1, selectedPoints)
        # spatial join to append attributes from MbrLineClass
        joinFeat = "joinFeat"
        arcpy.SpatialJoin_analysis(selectedPoints, MbrLineClass, joinFeat)

        # only need these attributes, with additional POINT_X and POINT_Y attributes added
        fieldsToKept = ["featID", "rectangle_Orientation", "direction"]
        fieldsToDelete = []
        fields = arcpy.ListFields(joinFeat)
        for field in fields:
            if not field.required:
                if not field.name in fieldsToKept:
                    fieldsToDelete.append(field.name)

        arcpy.DeleteField_management(joinFeat, fieldsToDelete)
        arcpy.AddXY_management(joinFeat)

        # delete schema.ini which may contains incorrect data types
        schemaFile = tempFolder + "/" + "schema.ini"
        if os.path.isfile(schemaFile):
            os.remove(schemaFile)
        # export the attributes to a csv file
        csvFile = tempFolder + "/joinFeat_points.csv"
        arcpy.CopyRows_management(joinFeat, csvFile)
        # read the csv file as a pandas data frame
        pointDF = pd.read_csv(csvFile, sep=",", header=0)
        pointDF.set_index("OBJECTID", inplace=True)

        idList = []
        angleList = []
        dirList = []
        xList = []
        yList = []
        # loop through each feature
        for id in np.unique(pointDF.featID):
            # intend to select two points (e.g., E and W, W and E, N and S, S and N) for each input feature; each point requires one row
            idList.append(id)  # for first point (one element in the list)
            idList.append(id)  # for second point (next element in the list)
            # tempDF contains candidate points for a selected polygon feature
            tempDF = pointDF.loc[pointDF.featID == id]
            angle = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.max()][
                "rectangle_Orientation"
            ].values[0]
            angleList.append(angle)
            angleList.append(angle)
            if (angle >= 45) & (angle <= 135):
                # POINT_X.max() indicates E
                direction = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.max()][
                    "direction"
                ].values[0]
                dirList.append(direction)
                x = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.max()][
                    "POINT_X"
                ].values[0]
                xList.append(x)
                y = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.max()][
                    "POINT_Y"
                ].values[0]
                yList.append(y)
                # POINT_X.min() indicates W
                direction = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.min()][
                    "direction"
                ].values[0]
                dirList.append(direction)
                x = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.min()][
                    "POINT_X"
                ].values[0]
                xList.append(x)
                y = tempDF.loc[tempDF.POINT_X == tempDF.POINT_X.min()][
                    "POINT_Y"
                ].values[0]
                yList.append(y)
            else:
                # POINT_Y.max() indicates N
                direction = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.max()][
                    "direction"
                ].values[0]
                dirList.append(direction)
                x = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.max()][
                    "POINT_X"
                ].values[0]
                xList.append(x)
                y = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.max()][
                    "POINT_Y"
                ].values[0]
                yList.append(y)
                # POINT_Y.min() indicates S
                direction = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.min()][
                    "direction"
                ].values[0]
                dirList.append(direction)
                x = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.min()][
                    "POINT_X"
                ].values[0]
                xList.append(x)
                y = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.min()][
                    "POINT_Y"
                ].values[0]
                yList.append(y)

        # create a new dataframe
        newPD = pd.DataFrame()
        newPD["featID"] = idList
        newPD["angle"] = angleList
        newPD["direction"] = dirList
        newPD["POINT_X"] = xList
        newPD["POINT_Y"] = yList
        # export the dataframe to a csv file
        outFile = tempFolder + "/joinFeat_points1_selected.csv"
        newPD.to_csv(outFile, sep=",", header=True)
        # create point featureclass from the csv file
        arcpy.XYTableToPoint_management(
            outFile, outPointFeat, "POINT_X", "POINT_Y", "#", MbrLineClass
        )

    ##
    ##        field = "direction"
    ##        inID = "OBJECTID"
    ##        joinID = "OBJECTID"
    ##        expression = "!" + MbrLineClass + "." + "direction" + "!"
    ##        HelperFunctions.addTextField(outPointFeat,MbrLineClass,field,inID,joinID,expression)
    ##        # delete temporary data
    ##        arcpy.Delete_management(inFeatVertices)
    ##        arcpy.Delete_management(selectedPoints)
    ##        arcpy.Delete_management(layer1)
    ##        arcpy.Delete_management(outFile)
    ##        arcpy.Delete_management(csvFile)

    # This function generate direction point features from the input features and the bounding rectangle features
    # This works but is very time consuming
    def getDirectionPoints_old1(
        self, inFeatClass, MbrLineClass, tempFolder, outPointFeat
    ):
        # inFeatClass: featureclass represents the polygons to be connected (input Bathymetric High features)
        # MbrLineClass: a subset of the lines from the minimum bounding rectangles of inFeatClass; for each feature there are two lines, either N and S or E and W.
        # tempFolder: folder location to store temporary files
        # outPointFeat: output direction point features

        inFeatVertices = "inFeatVertices"
        # convert each input feature to points;
        arcpy.FeatureVerticesToPoints_management(inFeatClass, inFeatVertices, "ALL")

        layer1 = "layer1"
        arcpy.MakeFeatureLayer_management(inFeatVertices, layer1)
        # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
        arcpy.SelectLayerByLocation_management(layer1, "INTERSECT", MbrLineClass)
        selectedPoints = "selectedPoints1"
        arcpy.CopyFeatures_management(layer1, selectedPoints)
        arcpy.AddXY_management(selectedPoints)

        MbrLineN = "MbrLineN"
        MbrLineS = "MbrLineS"
        MbrLineE = "MbrLineE"
        MbrLineW = "MbrLineW"

        whereClause = "direction = 'N'"
        arcpy.Select_analysis(MbrLineClass, MbrLineN, whereClause)
        whereClause = "direction = 'S'"
        arcpy.Select_analysis(MbrLineClass, MbrLineS, whereClause)
        whereClause = "direction = 'E'"
        arcpy.Select_analysis(MbrLineClass, MbrLineE, whereClause)
        whereClause = "direction = 'W'"
        arcpy.Select_analysis(MbrLineClass, MbrLineW, whereClause)

        idList = []
        angleList = []
        dirList = []
        xList = []
        yList = []

        cursor = arcpy.SearchCursor(MbrLineN)
        arcpy.AddMessage("MbrLineN")
        for row in cursor:
            featID = row.getValue("featID")
            arcpy.AddMessage("featID: " + str(featID))
            idList.append(featID)
            angle = row.getValue("rectangle_Orientation")
            angleList.append(angle)
            dirList.append("N")
            tempFeat = "tempFeat"
            whereClause = "featID = " + str(featID)
            arcpy.Select_analysis(selectedPoints, tempFeat, whereClause)

            tempFeat1 = "tempFeat1"
            arcpy.Select_analysis(MbrLineN, tempFeat1, whereClause)

            layerTemp = "layerTemp"
            arcpy.MakeFeatureLayer_management(tempFeat, layerTemp)
            # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
            arcpy.SelectLayerByLocation_management(layerTemp, "INTERSECT", tempFeat1)
            tempPoints = "tempPoints"
            arcpy.CopyFeatures_management(layerTemp, tempPoints)

            cursor1 = arcpy.SearchCursor(tempPoints)
            row1 = cursor1.next()
            pointX = row1.getValue("POINT_X")
            pointY = row1.getValue("POINT_Y")
            xList.append(pointX)
            yList.append(pointY)

            arcpy.Delete_management(tempFeat)
            arcpy.Delete_management(tempFeat1)
            arcpy.Delete_management(tempPoints)
            arcpy.Delete_management(layerTemp)

            del row1, cursor1
        del row, cursor

        cursor = arcpy.SearchCursor(MbrLineS)
        arcpy.AddMessage("MbrLineS")
        for row in cursor:
            featID = row.getValue("featID")
            arcpy.AddMessage("featID: " + str(featID))
            idList.append(featID)
            angle = row.getValue("rectangle_Orientation")
            angleList.append(angle)
            dirList.append("S")
            tempFeat = "tempFeat"
            whereClause = "featID = " + str(featID)
            arcpy.Select_analysis(selectedPoints, tempFeat, whereClause)

            tempFeat1 = "tempFeat1"
            arcpy.Select_analysis(MbrLineS, tempFeat1, whereClause)

            layerTemp = "layerTemp"
            arcpy.MakeFeatureLayer_management(tempFeat, layerTemp)
            # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
            arcpy.SelectLayerByLocation_management(layerTemp, "INTERSECT", tempFeat1)
            tempPoints = "tempPoints"
            arcpy.CopyFeatures_management(layerTemp, tempPoints)

            cursor1 = arcpy.SearchCursor(tempPoints)
            row1 = cursor1.next()
            pointX = row1.getValue("POINT_X")
            pointY = row1.getValue("POINT_Y")
            xList.append(pointX)
            yList.append(pointY)

            arcpy.Delete_management(tempFeat)
            arcpy.Delete_management(tempFeat1)
            arcpy.Delete_management(tempPoints)
            arcpy.Delete_management(layerTemp)

            del row1, cursor1
        del row, cursor

        cursor = arcpy.SearchCursor(MbrLineE)
        arcpy.AddMessage("MbrLineE")
        for row in cursor:
            featID = row.getValue("featID")
            arcpy.AddMessage("featID: " + str(featID))
            idList.append(featID)
            angle = row.getValue("rectangle_Orientation")
            angleList.append(angle)
            dirList.append("E")
            tempFeat = "tempFeat"
            whereClause = "featID = " + str(featID)
            arcpy.Select_analysis(selectedPoints, tempFeat, whereClause)

            tempFeat1 = "tempFeat1"
            arcpy.Select_analysis(MbrLineE, tempFeat1, whereClause)

            layerTemp = "layerTemp"
            arcpy.MakeFeatureLayer_management(tempFeat, layerTemp)
            # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
            arcpy.SelectLayerByLocation_management(layerTemp, "INTERSECT", tempFeat1)
            tempPoints = "tempPoints"
            arcpy.CopyFeatures_management(layerTemp, tempPoints)

            cursor1 = arcpy.SearchCursor(tempPoints)
            row1 = cursor1.next()
            pointX = row1.getValue("POINT_X")
            pointY = row1.getValue("POINT_Y")
            xList.append(pointX)
            yList.append(pointY)

            arcpy.Delete_management(tempFeat)
            arcpy.Delete_management(tempFeat1)
            arcpy.Delete_management(tempPoints)
            arcpy.Delete_management(layerTemp)

            del row1, cursor1
        del row, cursor

        cursor = arcpy.SearchCursor(MbrLineW)
        arcpy.AddMessage("MbrLineW")
        for row in cursor:
            featID = row.getValue("featID")
            arcpy.AddMessage("featID: " + str(featID))
            idList.append(featID)
            angle = row.getValue("rectangle_Orientation")
            angleList.append(angle)
            dirList.append("W")
            tempFeat = "tempFeat"
            whereClause = "featID = " + str(featID)
            arcpy.Select_analysis(selectedPoints, tempFeat, whereClause)

            tempFeat1 = "tempFeat1"
            arcpy.Select_analysis(MbrLineW, tempFeat1, whereClause)

            layerTemp = "layerTemp"
            arcpy.MakeFeatureLayer_management(tempFeat, layerTemp)
            # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
            arcpy.SelectLayerByLocation_management(layerTemp, "INTERSECT", tempFeat1)
            tempPoints = "tempPoints"
            arcpy.CopyFeatures_management(layerTemp, tempPoints)

            cursor1 = arcpy.SearchCursor(tempPoints)
            row1 = cursor1.next()
            pointX = row1.getValue("POINT_X")
            pointY = row1.getValue("POINT_Y")
            xList.append(pointX)
            yList.append(pointY)

            arcpy.Delete_management(tempFeat)
            arcpy.Delete_management(tempFeat1)
            arcpy.Delete_management(tempPoints)
            arcpy.Delete_management(layerTemp)

            del row1, cursor1
        del row, cursor

        # create a new dataframe
        newPD = pd.DataFrame()
        newPD["featID"] = idList
        newPD["angle"] = angleList
        newPD["direction"] = dirList
        newPD["POINT_X"] = xList
        newPD["POINT_Y"] = yList
        # export the dataframe to a csv file
        outFile = tempFolder + "/joinFeat_points1_selected.csv"
        newPD.to_csv(outFile, sep=",", header=True)
        # create point featureclass from the csv file
        arcpy.XYTableToPoint_management(
            outFile, outPointFeat, "POINT_X", "POINT_Y", "#", MbrLineClass
        )

    ##        # delete temporary data
    ##        arcpy.Delete_management(inFeatVertices)
    ##        arcpy.Delete_management(selectedPoints)
    ##        arcpy.Delete_management(layer1)
    ##        arcpy.Delete_management(outFile)
    ##        arcpy.Delete_management(MbrLineN)
    ##        arcpy.Delete_management(MbrLineS)
    ##        arcpy.Delete_management(MbrLineE)
    ##        arcpy.Delete_management(MbrLineW)

    # This function generate direction point features from the input features.
    # Two points are generated for each feature at its north and south sides or its east and west sides.
    def getDirectionPoints(self, inFeatClass, MbrLineClass, tempFolder, outPointFeat):
        # inFeatClass: featureclass represents the polygons to be connected (input Bathymetric High or Low features)
        # MbrLineClass: a subset of the lines from the minimum bounding rectangles of inFeatClass; for each feature there are two lines, either N and S or E and W.
        # tempFolder: folder location to store temporary files
        # outPointFeat: output direction point features
        itemList = []
        inFeatVertices = "inFeatVertices"
        itemList.append(inFeatVertices)
        # convert each input feature to points;
        arcpy.FeatureVerticesToPoints_management(inFeatClass, inFeatVertices, "ALL")
        # for each polygon, the first vertice and the last vertice are identical, need to remove the duplicate
        verticeTab = "verticeTab"
        itemList.append(verticeTab)
        statsField = [["OBJECTID", "MIN"]]
        caseField = "featID"
        arcpy.Statistics_analysis(inFeatVertices, verticeTab, statsField, caseField)

        idList = []
        cursor = arcpy.SearchCursor(verticeTab)
        for row in cursor:
            oID = row.getValue("MIN_OBJECTID")
            idList.append(oID)
        del cursor, row

        inFeatVertices1 = "inFeatVertices1"
        itemList.append(inFeatVertices1)
        # select subset
        text = "("
        for j in idList:
            text = text + str(j) + ","
        text = text[0:-1] + ")"
        whereClause = "OBJECTID NOT IN " + text
        arcpy.Select_analysis(inFeatVertices, inFeatVertices1, whereClause)

        # select polygon points on the bounding rectangle boundaries
        layer1 = "layer1"
        itemList.append(layer1)
        arcpy.MakeFeatureLayer_management(inFeatVertices1, layer1)
        # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
        arcpy.SelectLayerByLocation_management(layer1, "INTERSECT", MbrLineClass)
        selectedPoints = "selectedPoints1"
        itemList.append(selectedPoints)
        arcpy.CopyFeatures_management(layer1, selectedPoints)
        arcpy.AddXY_management(selectedPoints)

        # separate into four boundary types
        MbrLineN = "MbrLineN"
        MbrLineS = "MbrLineS"
        MbrLineE = "MbrLineE"
        MbrLineW = "MbrLineW"
        itemList.append(MbrLineN)
        itemList.append(MbrLineS)
        itemList.append(MbrLineE)
        itemList.append(MbrLineW)

        whereClause = "direction = 'N'"
        arcpy.Select_analysis(MbrLineClass, MbrLineN, whereClause)
        whereClause = "direction = 'S'"
        arcpy.Select_analysis(MbrLineClass, MbrLineS, whereClause)
        whereClause = "direction = 'E'"
        arcpy.Select_analysis(MbrLineClass, MbrLineE, whereClause)
        whereClause = "direction = 'W'"
        arcpy.Select_analysis(MbrLineClass, MbrLineW, whereClause)

        # when the orientation is straight north (=0) or straight east (=90), multiple points can be on the boundaries
        # in this case, need to select only one point (first point) for each boundary
        selectedPoints_1 = "selectedPoints1_1"
        itemList.append(selectedPoints_1)
        whereClause = "rectangle_Orientation = 0"
        arcpy.Select_analysis(selectedPoints, selectedPoints_1, whereClause)

        tab1 = "tab1"
        itemList.append(tab1)
        statsField = [["OBJECTID", "MIN"]]
        caseField = ["featID", "POINT_Y"]
        arcpy.Statistics_analysis(selectedPoints_1, tab1, statsField, caseField)

        idList = []
        cursor = arcpy.SearchCursor(tab1)
        for row in cursor:
            oID = row.getValue("MIN_OBJECTID")
            idList.append(oID)
        del cursor, row

        selectedPoints_1_1 = "selectedPoints1_1_1"
        itemList.append(selectedPoints_1_1)
        # select subset
        text = "("
        for j in idList:
            text = text + str(j) + ","
        text = text[0:-1] + ")"
        whereClause = "OBJECTID IN " + text
        arcpy.Select_analysis(selectedPoints_1, selectedPoints_1_1, whereClause)

        selectedPoints_2 = "selectedPoints1_2"
        itemList.append(selectedPoints_2)
        whereClause = "rectangle_Orientation = 90"
        arcpy.Select_analysis(selectedPoints, selectedPoints_2, whereClause)

        tab2 = "tab2"
        itemList.append(tab2)
        statsField = [["OBJECTID", "MIN"]]
        caseField = ["featID", "POINT_X"]
        arcpy.Statistics_analysis(selectedPoints_2, tab2, statsField, caseField)

        idList = []
        cursor = arcpy.SearchCursor(tab2)
        for row in cursor:
            oID = row.getValue("MIN_OBJECTID")
            idList.append(oID)
        del cursor, row

        selectedPoints_2_1 = "selectedPoints1_2_1"
        itemList.append(selectedPoints_2_1)
        # select subset
        text = "("
        for j in idList:
            text = text + str(j) + ","
        text = text[0:-1] + ")"
        whereClause = "OBJECTID IN " + text
        arcpy.Select_analysis(selectedPoints_2, selectedPoints_2_1, whereClause)
        # select those points that are not from features orienting straight north and straight east
        selectedPoints_4 = "selectedPoints1_4"
        itemList.append(selectedPoints_4)
        whereClause = "(rectangle_Orientation <> 0) And (rectangle_Orientation <> 90)"
        arcpy.Select_analysis(selectedPoints, selectedPoints_4, whereClause)
        # merge these three subsets to form a new set of points
        selectedPoints1 = "selectedPoints2"
        itemList.append(selectedPoints1)
        inputs = [selectedPoints_1_1, selectedPoints_2_1, selectedPoints_4]
        arcpy.Merge_management(inputs, selectedPoints1)

        # call the function to generate direction lists
        idList = []
        angleList = []
        dirList = []
        xList = []
        yList = []

        idList, angleList, dirList, xList, yList = self.generateDirectionPointLists(
            selectedPoints1, MbrLineN, idList, angleList, dirList, xList, yList, "N"
        )
        idList, angleList, dirList, xList, yList = self.generateDirectionPointLists(
            selectedPoints1, MbrLineS, idList, angleList, dirList, xList, yList, "S"
        )
        idList, angleList, dirList, xList, yList = self.generateDirectionPointLists(
            selectedPoints1, MbrLineE, idList, angleList, dirList, xList, yList, "E"
        )
        idList, angleList, dirList, xList, yList = self.generateDirectionPointLists(
            selectedPoints1, MbrLineW, idList, angleList, dirList, xList, yList, "W"
        )

        # create a new dataframe
        newPD = pd.DataFrame()
        newPD["featID"] = idList
        newPD["angle"] = angleList
        newPD["direction"] = dirList
        newPD["POINT_X"] = xList
        newPD["POINT_Y"] = yList
        # export the dataframe to a csv file
        outFile = tempFolder + "/points1_selected.csv"
        itemList.append(outFile)
        newPD.to_csv(outFile, sep=",", header=True)
        # create point featureclass from the csv file
        arcpy.XYTableToPoint_management(
            outFile, outPointFeat, "POINT_X", "POINT_Y", "#", MbrLineClass
        )

        # delete temporary data
        HelperFunctions.deleteDataItems(itemList)

    # This function generates five lists from the direction points input featureclass.
    def generateDirectionPointLists(
        self,
        pointFeat,
        MbrlineFeat,
        idList,
        angleList,
        dirList,
        xList,
        yList,
        direction,
    ):
        # pointFeat: input direction points featureclass
        # MbrlineFeat: input bounding rectangle boundaries featueclass
        # idList: output list of featIDs
        # angleList: output list of feature orientations
        # dirList: output list of the input direction indicated in the "direction" parameter
        # xList: output list of x coordinates
        # yList: output list of y coordinates
        # direction: a text field indicates the direction
        itemList = []
        layerTemp = "layerTemp"
        itemList.append(layerTemp)
        arcpy.MakeFeatureLayer_management(pointFeat, layerTemp)
        # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
        arcpy.SelectLayerByLocation_management(layerTemp, "INTERSECT", MbrlineFeat)
        selectedPointsTemp = "selectedPointsTemp"
        itemList.append(layerTemp)
        arcpy.CopyFeatures_management(layerTemp, selectedPointsTemp)

        # build two featID lists: one contains features with only one candidate point; the other contains mutliple candidate points
        sumTab = "sumTab"
        itemList.append(sumTab)
        statsField = [["featID", "COUNT"]]
        caseField = "featID"
        arcpy.Statistics_analysis(selectedPointsTemp, sumTab, statsField, caseField)
        featIDList1 = []
        featIDList2 = []
        cursor = arcpy.SearchCursor(sumTab)
        for row in cursor:
            count = row.getValue("COUNT_featID")
            featID = row.getValue("featID")
            if int(count) > 1:
                featIDList2.append(featID)
            else:
                featIDList1.append(featID)
        del cursor, row

        if len(featIDList1) > 0:
            # select subset
            text = "("
            for j in featIDList1:
                text = text + str(j) + ","
            text = text[0:-1] + ")"
            whereClause = "featID IN " + text
            selectedPointsTemp1 = "selectedPoints1Temp1"
            itemList.append(selectedPointsTemp1)
            arcpy.Select_analysis(selectedPointsTemp, selectedPointsTemp1, whereClause)

        # deal with the first subset
        inFeatCount = int(arcpy.GetCount_management(selectedPointsTemp1).getOutput(0))
        if inFeatCount > 0:
            cursor = arcpy.SearchCursor(selectedPointsTemp1)
            for row in cursor:
                featID = row.getValue("featID")
                arcpy.AddMessage("featID: " + str(featID))
                idList.append(featID)
                angle = row.getValue("rectangle_Orientation")
                angleList.append(angle)
                dirList.append(direction)
                x = row.getValue("POINT_X")
                xList.append(x)
                y = row.getValue("POINT_Y")
                yList.append(y)
            del cursor, row

        if len(featIDList2) > 0:
            # deal with the second subset
            for idV in featIDList2:
                arcpy.AddMessage("idV: " + str(idV))
                tempFeat = "tempFeat"
                whereClause = "featID = " + str(idV)
                arcpy.Select_analysis(pointFeat, tempFeat, whereClause)

                tempFeat1 = "tempFeat1"
                arcpy.Select_analysis(MbrlineFeat, tempFeat1, whereClause)

                layerTemp1 = "layerTemp1"
                arcpy.MakeFeatureLayer_management(tempFeat, layerTemp1)
                # select those points that are on the selected bounding rectangle boundaries (N and S or E and W)
                arcpy.SelectLayerByLocation_management(
                    layerTemp1, "INTERSECT", tempFeat1
                )
                tempPoints = "tempPoints"
                arcpy.CopyFeatures_management(layerTemp1, tempPoints)

                inFeatCount = int(arcpy.GetCount_management(tempPoints).getOutput(0))
                if inFeatCount > 0:
                    idList.append(idV)
                    cursor1 = arcpy.SearchCursor(tempPoints)
                    row1 = cursor1.next()  # get the first candidate point
                    pointX = row1.getValue("POINT_X")
                    pointY = row1.getValue("POINT_Y")
                    xList.append(pointX)
                    yList.append(pointY)

                    angle = row1.getValue("rectangle_Orientation")
                    angleList.append(angle)
                    dirList.append(direction)
                    del cursor1, row1
                arcpy.Delete_management(tempFeat)
                arcpy.Delete_management(tempFeat1)
                arcpy.Delete_management(tempPoints)
                arcpy.Delete_management(layerTemp)

        HelperFunctions.deleteDataItems(itemList)
        return idList, angleList, dirList, xList, yList

    # This function selects a subset of input links.
    def selectLinks(self, inLinksFeat, pointsFeatFrom, pointsFeatTo, outLinksFeat):
        # inLinksFeat: input links featureclass
        # pointsFeatFrom: featureclass represents the from point of a link
        # pointsFeatTo: featureclass represents the to point of a link
        # outLinksFeat: output the subset of links after the selection process

        # add and calculate fields
        field1 = "featID1"
        field2 = "fromLocation"  # location of the origin features (e.g., F and H)
        field3 = (
            "fromDirection"  # orientation of the origin features (e.g., N, S, E and W)
        )
        inID = "ORIG_FID"
        joinID = "OBJECTID"
        expression = "!" + pointsFeatFrom + "." + "featID" + "!"
        HelperFunctions.addLongField(inLinksFeat, pointsFeatFrom, field1, inID, joinID, expression)
        expression = "!" + pointsFeatFrom + "." + "location" + "!"
        HelperFunctions.addTextField(inLinksFeat, pointsFeatFrom, field2, inID, joinID, expression)
        expression = "!" + pointsFeatFrom + "." + "direction" + "!"
        HelperFunctions.addTextField(inLinksFeat, pointsFeatFrom, field3, inID, joinID, expression)

        field1 = "featID2"
        field2 = "toLocation"  # location of the destination features
        field3 = "toDirection"  # orientation of the destination features
        inID = "DEST_FID"
        joinID = "OBJECTID"
        expression = "!" + pointsFeatTo + "." + "featID" + "!"
        HelperFunctions.addLongField(inLinksFeat, pointsFeatTo, field1, inID, joinID, expression)
        expression = "!" + pointsFeatTo + "." + "location" + "!"
        HelperFunctions.addTextField(inLinksFeat, pointsFeatTo, field2, inID, joinID, expression)
        expression = "!" + pointsFeatTo + "." + "direction" + "!"
        HelperFunctions.addTextField(inLinksFeat, pointsFeatTo, field3, inID, joinID, expression)

        # add more fields
        fieldName1 = "idDiff"
        fieldType = "LONG"
        fieldPrecision = 15
        arcpy.AddField_management(inLinksFeat, fieldName1, fieldType, fieldPrecision)

        expression = "!featID1! - !featID2!"
        arcpy.CalculateField_management(inLinksFeat, fieldName1, expression)
        linksFeat1Temp = "links1Temp"
        whereClause = "idDiff <> 0"
        arcpy.Select_analysis(inLinksFeat, linksFeat1Temp, whereClause)

        # generate summary statistics
        tab1 = "tab1"
        statsField = [["LINK_DIST", "MIN"]]
        caseField = "featID1"
        arcpy.Statistics_analysis(linksFeat1Temp, tab1, statsField, caseField)

        fieldName2 = "distDiff"
        inID = "featID1"
        joinID = "featID1"
        expression = "!" + linksFeat1Temp + ".LINK_DIST! - !" + tab1 + ".MIN_LINK_DIST!"
        HelperFunctions.addField(linksFeat1Temp, tab1, fieldName2, inID, joinID, expression)
        # select a subset o links based on the following condition
        linksFeat2Temp = "links2Temp"
        whereClause = "distDiff = 0"
        arcpy.Select_analysis(linksFeat1Temp, linksFeat2Temp, whereClause)
        # further selection based on the following condition
        whereClause = "(fromLocation = 'F') And (toLocation = 'H')"
        arcpy.Select_analysis(linksFeat2Temp, outLinksFeat, whereClause)

        arcpy.Delete_management(linksFeat1Temp)
        arcpy.Delete_management(linksFeat2Temp)
        arcpy.Delete_management(tab1)

    # This function identifies the input points as either head (H) points or foot (F) points.
    def toFHpoints(self, inPointFeat, mosaicBathy, tempFolder, outPointFeat):
        # inPointFeat: input featureclass represents direction points
        # mosaicBathy: input bathymetry data
        # tempFolder: the tempFolder to store temporary files
        # outPointFeat: output point featureclass with a new field indicating the H or F location

        pointFeatTemp = "pointFeatTemp"
        # to identify a point as either H or F point, we need to obtain the bathymetry value for this point
        ExtractValuesToPoints(inPointFeat, mosaicBathy, pointFeatTemp)
        arcpy.AddMessage("extract depth values done")

        # delete schema.ini which may contains incorrect data types
        schemaFile = tempFolder + "/" + "schema.ini"
        if os.path.isfile(schemaFile):
            os.remove(schemaFile)
        # export the attributes to a csv file
        csvFile = tempFolder + "/pointFeat1.csv"
        arcpy.CopyRows_management(pointFeatTemp, csvFile)
        # read the csv file as a pandas data frame
        pointDF = pd.read_csv(csvFile, sep=",", header=0)
        pointDF.set_index("OBJECTID", inplace=True)

        idList = []
        angleList = []
        dirList = []
        locList = []
        xList = []
        yList = []
        # loop through each feature
        for id in np.unique(pointDF.featID):
            # intend to select two points (e.g., E and W, W and E, N and S, S and N) for each input feature; each point requires one row
            idList.append(id)  # for first point (one element in the list)
            idList.append(id)  # for second point (next element in the list)
            # tempDF contains candidate points for a selected polygon feature
            tempDF = pointDF.loc[pointDF.featID == id]
            angle = tempDF.loc[tempDF.POINT_Y == tempDF.POINT_Y.max()]["angle"].values[
                0
            ]
            angleList.append(angle)
            angleList.append(angle)

            # RASTERVALU.max() indicates head
            x = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.max()][
                "POINT_X"
            ].values[0]
            xList.append(x)
            y = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.max()][
                "POINT_Y"
            ].values[0]
            yList.append(y)
            dirV = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.max()][
                "direction"
            ].values[0]
            dirList.append(dirV)
            locList.append("H")
            # RASTERVALU.min() indicates foot
            x = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.min()][
                "POINT_X"
            ].values[0]
            xList.append(x)
            y = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.min()][
                "POINT_Y"
            ].values[0]
            yList.append(y)
            dirV = tempDF.loc[tempDF.RASTERVALU == tempDF.RASTERVALU.min()][
                "direction"
            ].values[0]
            dirList.append(dirV)
            locList.append("F")

        # create a new dataframe
        newPD = pd.DataFrame()
        newPD["featID"] = idList
        newPD["angle"] = angleList
        newPD["direction"] = dirList
        newPD["location"] = locList
        newPD["POINT_X"] = xList
        newPD["POINT_Y"] = yList
        # export the dataframe to a csv file
        outFile = tempFolder + "/pointFeat2.csv"
        newPD.to_csv(outFile, sep=",", header=True)
        # create point featureclass from the csv file
        arcpy.XYTableToPoint_management(
            outFile, outPointFeat, "POINT_X", "POINT_Y", "#", inPointFeat
        )

        # delete temporary data
        arcpy.Delete_management(pointFeatTemp)
        arcpy.Delete_management(csvFile)
        arcpy.Delete_management(outFile)
