#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: updated on December 15, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from datetime import datetime
from arcpy.sa import *
import os
import sys
import multiprocessing
from importlib import reload
import ClassificationToolsFunctions
from ClassificationToolsFunctions import execute_verify_depression
import HelperFunctions

arcpy.CheckOutExtension("Spatial")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "ClassifyFeatures"

        # List of tool classes associated with this toolbox
        # There are two tools. One tool is used to classify Bathymetric High features. The other is used to classify Bathymetric Low features.
        self.tools = [
            Classify_Bathymetric_High_Features_Tool,
            Classify_Bathymetric_Low_Features_Tool,
            Verify_Depression_Tool
        ]


# This tool is used to classify Bathymetric Low features based on their attributes.
class Classify_Bathymetric_Low_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Classify Bathymetric Low Features Tool"
        self.description = "Classify each Bathymetric Low feature according to the morphological classification scheme"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric Low Features",
            name="inFeatClass",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )
        param1.parameterDependencies = [param0.name]

        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Length_to_Width Ratio Threshold",
            name="lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param2.value = 8.0

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Head Depth Threshold (m)",
            name="headDepthT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param3.value = 4000.0

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Mean Segment Slope Threshold Large (degree)",
            name="meanSegmentSlopeT1",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param4.value = 7.0

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Head_to_Foot Depth Range Threshold (m)",
            name="hfdepthRangeT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 600.0

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Mean Segment Slope Threshold Small (degree)",
            name="meanSegmentSlopeT2",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = 2.0

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Shape Circularity Threshold",
            name="circularityT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param7.value = 0.5

        parameters = [param0, param1, param2, param3, param4, param5, param6, param7]
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

        inFeatClass = parameters[0].valueAsText
        outFeatClass = parameters[1].valueAsText
        lwRatioT = float(parameters[2].valueAsText)
        headDepthT = float(parameters[3].valueAsText)
        meanSegmentSlopeT1 = float(parameters[4].valueAsText)
        hfdepthRangeT = float(parameters[5].valueAsText)
        meanSegmentSlopeT2 = float(parameters[6].valueAsText)
        circularityT = float(parameters[7].valueAsText)

        # make sure meanSegmentSlopeT2 is smaller than meanSegmentSlopeT1
        if meanSegmentSlopeT2 > meanSegmentSlopeT1:
            messages.addErrorMessage(
                "Mean Segment Slope Threshold Small must be smaller than Mean Segment Slope Threshold Large!"
            )
            raise arcpy.ExecuteError

        # enable helper
        helper = helpers()
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = HelperFunctions.convert_backslash_forwardslash(
                            lyr.dataSource
                        )

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input feature class is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # make sure all the required attributes exist in the input featureclass
        attributeList = [
            "featID",
            "LengthWidthRatio",
            "head_foot_depthRange",
            "mean_width",
            "profileSymmetry",
            "profile_bottom_SlopeClass",
            "profile_side_SlopeClass",
            "headDepth",
            "mean_segment_slope",
            "mean_width_thickness_ratio",
            "mean_thickness",
            "width_distance_slope",
            "width_distance_correlation",
            "thick_distance_slope",
            "thick_distance_correlation",
            "Circularity",
        ]

        attributeList = [
            "featID",
            "LengthWidthRatio",
            "head_foot_depthRange",
            "mean_width",
            "profileSymmetry",
            "profile_bottom_SlopeClass",
            "profile_side_SlopeClass",
            "headDepth",
            "mean_segment_slope",
            "Circularity",
        ]
        for attribute in attributeList:
            if attribute not in field_names:
                messages.addErrorMessage(
                    "The input featureclass does not have "
                    + attribute
                    + " attribute. You have to calculate the attribute using the Attributes Tool!"
                )
                raise arcpy.ExecuteError

        # check the 'Morphology_feature' field exists
        field = "Morphology_feature"
        fieldType = "TEXT"
        fieldLength = 200
        if field in field_names:
            arcpy.AddMessage(field + " exists and will be recalculated.")
        else:
            arcpy.management.AddField(
                inFeatClass, field, fieldType, field_length=fieldLength
            )

        # loop through each feature
        cursor = arcpy.UpdateCursor(inFeatClass)

        for row in cursor:
            # get attributes values
            featID = row.getValue("featID")
            arcpy.AddMessage("classifying featID: " + str(featID))
            lwRatio = float(row.getValue("LengthWidthRatio"))
            hfdepthRange = float(row.getValue("head_foot_depthRange"))
            meanWidth = float(row.getValue("mean_width"))
            profileSymmetry = row.getValue("profileSymmetry")
            profileSymmetryL = profileSymmetry.split(",")
            profileBottomClass = row.getValue("profile_bottom_SlopeClass")
            profileBottomClassL = profileBottomClass.split(",")
            profileSideClass = row.getValue("profile_side_SlopeClass")
            profileSideClassL = profileSideClass.split(",")
            headDepth = float(row.getValue("headDepth"))
            meanSegmentSlope = float(row.getValue("mean_segment_slope"))
            circularity = float(row.getValue("Circularity"))

            # the bottom slope list combines profile's bottom slope and side slope (only when the profile is triangle)
            slopeL = []
            j = 0
            while j < len(profileBottomClassL):
                bottomSlope = profileBottomClassL[j]
                sideSlope = profileSideClassL[j]
                if bottomSlope == "no bottom":  # triangle profile
                    slopeL.append(sideSlope)
                else:
                    slopeL.append(bottomSlope)
                j += 1
            arcpy.AddMessage("slopeL: " + str(slopeL))
            # bottom slope class count
            flatSlopeCount = slopeL.count("flat")
            gentleSlopeCount = slopeL.count("gentle")
            moderateSlopeCount = slopeL.count("moderate")
            steepSlopeCount = slopeL.count("steep")
            # side slope class count
            sFlatCount = profileSideClassL.count("flat")
            sGentleCount = profileSideClassL.count("gentle")
            sModerateCount = profileSideClassL.count("moderate")
            sSteepCount = profileSideClassL.count("steep")

            # profile symmetry class count
            SymmCount = profileSymmetryL.count("Symmetric")
            AsymmCount = profileSymmetryL.count("Asymmetric")

            # classification of Bathymetric Low features starts here
            # The classification rules are based on the morphological classification scheme. Please see the metadata of the tool for detailed description of the rules.
            feature = "unclassified"
            if lwRatio >= lwRatioT:
                if abs(headDepth) >= headDepthT:
                    if (AsymmCount >= SymmCount) and (
                        steepSlopeCount + moderateSlopeCount
                        >= flatSlopeCount + gentleSlopeCount
                    ):
                        feature = "Trench"
                    else:
                        feature = "Trough"
                else:
                    if (meanSegmentSlope > meanSegmentSlopeT1) and (
                        sSteepCount + sModerateCount >= sFlatCount + sGentleCount
                    ):
                        feature = "Gully"
                    else:
                        if (hfdepthRange >= hfdepthRangeT) and (
                            meanSegmentSlope >= meanSegmentSlopeT2
                        ):
                            feature = "Canyon"
                        else:
                            feature = "Valley/Channel"
            else:
                sCount = sSteepCount + sModerateCount + sGentleCount + sFlatCount
                if sCount == 0:
                    feature = "Depression"
                elif (
                    (circularity >= circularityT)
                    and (sSteepCount >= sModerateCount)
                    and (sSteepCount >= sGentleCount)
                    and (sSteepCount >= sFlatCount)
                ):
                    feature = "Hole"
                else:
                    feature = "Depression"

            row.setValue(field, feature)
            cursor.updateRow(row)
            arcpy.AddMessage(feature)
        del cursor, row

        return


# This tool is used to classify Bathymetric High features based on their attributes
class Classify_Bathymetric_High_Features_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Classify Bathymetric High Features Tool"
        self.description = "Classify each Bathymetric High feature according to the morphological classification scheme"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric High Features",
            name="inFeatClass",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )
        param1.parameterDependencies = [param0.name]

        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Ridge Length_to_Width Ratio Threshold",
            name="ridge_lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param2.value = 5.0

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Bank Minimum Depth Threshold (m)",
            name="bank_minDepthT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param3.value = 200.0

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Bank Area Threshold (km^2)",
            name="bank_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param4.value = 1.0

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Plateau Area Threshold (km^2)",
            name="plateau_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 100.0

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Hummock Depth Range Threshold (m)",
            name="hummock_depthRangeT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = 10.0

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Hummock Area Threshold (m^2)",
            name="hummock_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param7.value = 1000.0

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Cone Circularity Threshold",
            name="cone_circularityT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param8.value = 0.75

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

        inFeatClass = parameters[0].valueAsText
        outFeatClass = parameters[1].valueAsText
        ridge_lwRatioT = float(parameters[2].valueAsText)
        bank_minDepthT = float(parameters[3].valueAsText)
        bank_areaT = float(parameters[4].valueAsText)
        plateau_areaT = float(parameters[5].valueAsText)
        hummock_depthRangeT = float(parameters[6].valueAsText)
        hummock_areaT = float(parameters[7].valueAsText)
        cone_circularityT = float(parameters[8].valueAsText)

        # enable helper functions
        helper = helpers()
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = HelperFunctions.convert_backslash_forwardslash(
                            lyr.dataSource
                        )
        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input feature class is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # make sure all the required attributes exist in the input featureclass
        attributeList = [
            "featID",
            "LengthWidthRatio",
            "depthRange",
            "profileShape",
            "profile_top_SlopeClass",
            "profile_side_SlopeClass",
            "minDepth",
            "mean_width",
            "Circularity",
        ]
        for attribute in attributeList:
            if attribute not in field_names:
                messages.addErrorMessage(
                    "The input featureclass does not have "
                    + attribute
                    + " attribute. You have to calculate the attribute using the Attributes Tool!"
                )
                raise arcpy.ExecuteError
        # check the 'Morphology_feature' field exists
        field = "Morphology_feature"
        fieldType = "TEXT"
        fieldLength = 200
        if field in field_names:
            arcpy.AddMessage(field + " exists and will be recalculated.")
        else:
            arcpy.management.AddField(
                inFeatClass, field, fieldType, field_length=fieldLength
            )

        # loop through each feature
        cursor = arcpy.UpdateCursor(inFeatClass)
        i = 1
        for row in cursor:
            featID = row.getValue("featID")
            arcpy.AddMessage("classifying featID: " + str(featID))
            # get attributes values
            lwRatio = float(row.getValue("LengthWidthRatio"))
            depthRange = float(row.getValue("depthRange"))
            profileShape = row.getValue("profileShape")
            profileShapeL = profileShape.split(",")
            profileTopClass = row.getValue("profile_top_SlopeClass")
            profileTopClassL = profileTopClass.split(",")
            profileSideClass = row.getValue("profile_side_SlopeClass")
            profileSideClassL = profileSideClass.split(",")
            minDepth = float(row.getValue("minDepth"))
            meanWidth = float(row.getValue("mean_width"))
            area = float(row.getValue("Shape_Area"))
            circularity = float(row.getValue("Circularity"))
            # get profile shape class count
            RegularCount = profileShapeL.count("Regular")
            IrregularCount = profileShapeL.count("Irregular")
            TriangleCount = profileShapeL.count("Triangle")
            FlatCount = profileShapeL.count("Flat")

            # if profile shape is a triangle, add its profile side slope class
            triangle_sideSlopeL = []
            k = 0
            while k < len(profileShapeL):
                pShape = profileShapeL[k]
                sideSlope = profileSideClassL[k]
                if pShape == "Triangle":
                    triangle_sideSlopeL.append(sideSlope)
                k += 1

            # triangle side slope count
            moderateSlopeCountTriangle = triangle_sideSlopeL.count("moderate")
            steepSlopeCountTriangle = triangle_sideSlopeL.count("steep")

            # the top slope list combines profile's top slope and side slope (only when the profile is triangle)
            slopeL = []
            j = 0
            while j < len(profileTopClassL):
                topSlope = profileTopClassL[j]
                sideSlope = profileSideClassL[j]
                if topSlope == "no top":  # triangle profile
                    slopeL.append(sideSlope)
                else:
                    slopeL.append(topSlope)
                j += 1

            # top slope class count
            flatSlopeCount = slopeL.count("flat")
            gentleSlopeCount = slopeL.count("gentle")
            moderateSlopeCount = slopeL.count("moderate")
            steepSlopeCount = slopeL.count("steep")

            # side slope class count
            flatSlopeCountSide = profileSideClassL.count("flat")
            gentleSlopeCountSide = profileSideClassL.count("gentle")
            moderateSlopeCountSide = profileSideClassL.count("moderate")
            steepSlopeCountSide = profileSideClassL.count("steep")

            # classification of Bathymetric High features starts here
            # The classification rules are based on the morphological classification scheme. Please see the metadata of the tool for detailed description of the rules.
            feature = "unclassified"

            if lwRatio >= ridge_lwRatioT:
                feature = "Ridge"
            elif depthRange >= 1000:
                feature = "Seamount"
            elif depthRange >= meanWidth:
                feature = "Pinnacle"
            elif (
                (TriangleCount >= RegularCount)
                and (TriangleCount >= IrregularCount)
                and (TriangleCount >= FlatCount)
                and (moderateSlopeCountTriangle + steepSlopeCountTriangle >= 1)
                and (circularity >= cone_circularityT)
            ):
                feature = "Cone"
            elif (
                (
                    flatSlopeCount
                    >= gentleSlopeCount + moderateSlopeCount + steepSlopeCount
                )
                and (abs(minDepth) <= bank_minDepthT)
                and (area > bank_areaT * 1000000)
            ):
                feature = "Bank"
            elif (
                (
                    flatSlopeCount
                    >= gentleSlopeCount + moderateSlopeCount + steepSlopeCount
                )
                and (moderateSlopeCountSide + steepSlopeCountSide >= 1)
                and (area > plateau_areaT * 1000000)
            ):
                feature = "Plateau"
            elif depthRange >= 500:
                if (
                    (RegularCount >= IrregularCount)
                    and (RegularCount >= TriangleCount)
                    and (RegularCount >= FlatCount)
                ):
                    feature = "Knoll"
                else:
                    feature = "Hill"
            elif (depthRange < hummock_depthRangeT) and (area < hummock_areaT):
                feature = "Hummock"
            else:
                feature = "Mound"
            row.setValue(field, feature)
            cursor.updateRow(row)
            arcpy.AddMessage(feature)
            i += 1
        del cursor, row

        return


# This tool is used to verify Depression Feature.
class Verify_Depression_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Verify Depression Feature Tool"
        self.description = "Verify that the Bathymetric Low Features are indeed proper Depression"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric Low Features",
            name="inFeatClass",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="inBathy",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Area Ratio Threshold",
            name="areaRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param3.value = 0.1

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Maximum Number of Unique Contours",
            name="maxContour",
            datatype="GPLong",
            parameterType="Optional",
            direction="Input",
        )
        param4.value = 10

        parameters = [param0, param1, param2, param3, param4]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # set the output featureclass to be at the
        # same FileGeodatabase as the input featureclass
        if parameters[0].value:
            inFeatClass = parameters[0].valueAsText
            if inFeatClass.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isFeatureLayer:
                        if inFeatClass == lyr.name:
                            inFeatClass = lyr.dataSource

            parameters[2].value = inFeatClass + "_outFeats"
                

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        inFeatClass = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        outFeatClass = parameters[2].valueAsText
        areaRatioT = float(parameters[3].valueAsText)
        maxContour = int(parameters[4].valueAsText)

        # enable helper
        helper = helpers()
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = HelperFunctions.convert_backslash_forwardslash(
                            lyr.dataSource
                        )

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input feature class is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        # if the input inBathy is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(inBathy)
        rasFormat = rasDesc.format
        if rasFormat != "FGDBR":
            messages.addErrorMessage(
                "The input bathymetry raster must be a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input bathymetry grid is in a projected coordinate system
        spatialReference = rasDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        # check that the areaRatioT parameter is valid
        if (areaRatioT > 1.0) | (areaRatioT < 0):
            messages.addErrorMessage(
                "The Area Ratio Threshold must be between 0 and 1!"
            )
            raise arcpy.ExecuteError

        # check that the maxContour parameter is valid
        if (maxContour < 1):
            messages.addErrorMessage(
                "The Maximum Number of Unique Contours must be greater than 0!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        time1 = datetime.now()
        # select the input bathymetric low features that are originally classified as the Depression
        whereClause = "Morphology_feature = " + "'Depression'"
        depressionFeat = "depressionFeat"
        arcpy.analysis.Select(inFeatClass, depressionFeat, whereClause)
        # select the input bathymetric low features that are originally classified as other feature types
        whereClause = "Morphology_feature <> " + "'Depression'"
        otherFeat = "otherFeat"
        arcpy.analysis.Select(inFeatClass, otherFeat, whereClause)
        # get the cell size of the input bathymetric grid, assuming the cell is square shape
        result1 = arcpy.management.GetRasterProperties(inBathy, "CELLSIZEX")
        cellSize = result1.getOutput(0)
        if cellSize.find(",") > 0:
            cellSize = HelperFunctions.convertDecimalSeparator(cellSize)
        # get the total number of Depression feature to be verified through the multiprocessing process
        nuFeats = int(arcpy.management.GetCount(depressionFeat)[0])
        arcpy.AddMessage("They are " + str(nuFeats) + " features for multiprocessing.")
        # set the maximum number of CPUs for the multiprocessing job equals to half of those available
        maxCPU = int(multiprocessing.cpu_count() / 2) - 1
        # the name of the featureclass after merging all output features resulted from the multiprocessing jobs
        depressionFeat1 = depressionFeat + "_merged"
        # only doing the multiprocessing jobs if there is at least one Depression feature to verify
        if nuFeats > 0:
            # determine how many CPUs to use depending on the feature count of the Depression features
            if nuFeats % 5 > 0:
                x = int(nuFeats / 5) + 1
            else:
                x = int(nuFeats / 5)
            if x > maxCPU:
                nCPU = maxCPU
            else:
                nCPU = x

            arcpy.AddMessage("Using " + str(nCPU) + " CPU processors for multiprocessing")
            workspaceName = env.workspace
            # calling the splitDepressionFeat function to split the depression features, copy the input bathymetry grid, etc
            workspaceList, depressionFeatList, bathyList, outFeatList = helper.splitDepressionFeat(
                workspaceName,
                depressionFeat,
                inBathy,
                depressionFeat1,
                nCPU)

            argList = []
            i = 0
            while i < len(workspaceList):
                argList.append(
                    [workspaceList[i], depressionFeatList[i], bathyList[i], areaRatioT, maxContour,
                     cellSize, outFeatList[i]])
                i += 1

            arcpy.AddMessage(argList)
            # important, need to set the python.exe within ArcGIS Pro as the python set_executable
            # this will make sure the multiprocessing opens multiple python windows for processing
            # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
            # which would not process the task as expected.
            arcpy.AddMessage(os.path.join(sys.exec_prefix, 'python.exe'))
            multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
            # important, need to reload the module so that we use the most up-to-date coding in the module
            reload(ClassificationToolsFunctions)

            arcpy.AddMessage('Starting multiprocessing...')
            # call the execute_verify_depression() from the ClassificationToolsFunctions module
            # the function is the entry point for the multiprocessing
            execute_verify_depression(argList, nCPU)
            arcpy.AddMessage('multiprocessing Done.')

            # merge the individual outputs from the multiprocessing
            arcpy.management.Merge(outFeatList, depressionFeat1)
            arcpy.AddMessage("depressionFeats merge done")

            # delete all temporary workspaces and folders
            for workspace in workspaceList:
                arcpy.management.Delete(workspace)
            arcpy.AddMessage("All temporary workspaces are deleted")
        else: # if there isn't any depression feature to verify, just copy
            arcpy.management.Copy(depressionFeat, depressionFeat1)
        # merge the updated depression features and the other features to the final output featureclass
        arcpy.management.Merge([depressionFeat1, otherFeat], outFeatClass)
        arcpy.AddMessage("final merge finished")

        arcpy.AddMessage("Deleting temporary datasets")
        arcpy.management.Delete(depressionFeat)
        arcpy.management.Delete(depressionFeat1)
        arcpy.management.Delete(otherFeat)

        arcpy.AddMessage("Deletion finished")

        time2 = datetime.now()
        time_diff = time2 - time1
        arcpy.AddMessage("It took: " + str(time_diff) + " to finish")

        return


# define helper functions here
class helpers:    
    # This function input depression features into a number of subsets determined by the noSplit parameter
    def splitDepressionFeat(self, workspace, depressionFeat, inBathy, outFeat, noSplit):
        # workspace: the workspace which contains depressionFeat and inBathy
        # depressionFeat: the featureclass to be split
        # inBathy: the input bathymetric grid to be copied to the new workspace
        # outFeat: the basename for a featureclass
        # noSplit: the number of subsets to split the depressionFeat into

        # calculate the number of features in a subset
        noFeat = int(arcpy.management.GetCount(depressionFeat).getOutput(0))
        featCount = int(noFeat / noSplit)

        workspaceList = []
        depressionFeatList = []
        bathyList = []
        outFeatList = []
        # get the path to the input workspace
        path = workspace.rstrip(workspace.split('/')[-1])
        path = path.rstrip('/')
        # get the base name of the input workspace name
        baseName = workspace.split('/')[-1]
        baseName = baseName.split('.')[0]
        # get the name of the input bathymetric grid (without the path)
        inBathy = inBathy.split('/')[-1]
        # doing the splitting and copying, etc
        i = 1
        while i <= noSplit:
            # create a File Geodatabase
            gdbName = baseName + str(i) + '.gdb'
            arcpy.management.CreateFileGDB(path, gdbName)
            arcpy.AddMessage(gdbName + ' created')
            workspace = path + '/' + gdbName
            workspaceList.append(workspace)
            # select a subset of depressionFeat depending on the number of splits
            startID = (i - 1) * featCount
            if i == noSplit:
                endID = noFeat
            else:
                endID = i * featCount
            whereClause = '((OBJECTID > ' + str(startID) + ') And (OBJECTID <= ' + str(endID) + '))'
            tempFeat = path + '/' + gdbName + '/' + depressionFeat + '_' + str(i)
            arcpy.analysis.Select(depressionFeat, tempFeat, whereClause)
            arcpy.AddMessage(tempFeat + ' generated')
            depressionFeatList.append(tempFeat)
            # copy inBathy
            data1 = path + '/' + gdbName + '/' + inBathy
            arcpy.AddMessage(data1)
            bathyList.append(data1)
            arcpy.management.Copy(inBathy, data1)
            arcpy.AddMessage(inBathy + ' copied')
            # create a new name based on the basename of a featureclass
            data2 = path + '/' + gdbName + '/' + outFeat + '_' + str(i)
            outFeatList.append(data2)

            i += 1
        return workspaceList, depressionFeatList, bathyList, outFeatList






