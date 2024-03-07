#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: August 15, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import math
import os
from datetime import datetime

import arcpy
import numpy as np
import pandas as pd
from arcpy import env
from arcpy.sa import *

arcpy.CheckOutExtension("Spatial")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "AddAttributes"

        # List of tool classes associated with this toolbox
        # There are six tools. Three for generating attributes for Bathymetric High features. The other three for Bathymetric Low features.
        # The three tools are used to add three sets of attributes: shape attributes, topographic attributes and profile attributes, in that order.
        self.tools = [
            Add_Shape_Attributes_High_Tool,
            Add_Shape_Attributes_Low_Tool,
            Add_Profile_Attributes_High_Tool,
            Add_Profile_Attributes_Low_Tool,
            Add_Topographic_Attributes_High_Tool,
            Add_Topographic_Attributes_Low_Tool,
        ]


class Add_Shape_Attributes_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Shape Attributes High Tool"
        self.description = "Add Shape Attributes to the Bathymetric High features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Features",
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

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter, used to hold temporaray files
        param3 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="required",
            direction="Input",
        )

        parameters = [param0, param1, param2, param3]
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
        inBathy = parameters[2].valueAsText
        tempFolder = parameters[3].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        inBathy = helper.convert_backslach_forwardslach(inBathy)

        tempFolder = helper.convert_backslach_forwardslach(tempFolder)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )

        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
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

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # calculate compactness attribute
        helper.calculateCompactness(inFeatClass)
        # calculate circularity, convexity and solidity attributes
        helper.calculateCircularity_Convexity_Solidity(inFeatClass)
        # calculate sinuosity, length to width ratio, and other shape attributes
        helper.calculateSinuosity_LwR(workspaceName, tempFolder, inFeatClass, inBathy)
        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


class Add_Shape_Attributes_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Shape Attributes Low Tool"
        self.description = "Add Shape Attributes to the Bathymetric Low features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Features",
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

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="required",
            direction="Input",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Output Head Features",
            name="headFeatClass",
            datatype="DEFeatureClass",
            parameterType="required",
            direction="Output",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Output Foot Features",
            name="footFeatClass",
            datatype="DEFeatureClass",
            parameterType="required",
            direction="Output",
        )

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Calculate additional attributes",
            name="additionalOption",
            datatype="GPBoolean",
            parameterType="required",
            direction="Input",
        )
        param6.value = False

        parameters = [param0, param1, param2, param3, param4, param5, param6]
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
        inBathy = parameters[2].valueAsText
        tempFolder = parameters[3].valueAsText
        headFeatClass = parameters[4].valueAsText
        footFeatClass = parameters[5].valueAsText
        additionalOption = parameters[6].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        inBathy = helper.convert_backslach_forwardslach(inBathy)
        headFeatClass = helper.convert_backslach_forwardslach(headFeatClass)
        footFeatClass = helper.convert_backslach_forwardslach(footFeatClass)
        tempFolder = helper.convert_backslach_forwardslach(tempFolder)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
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

        # check that the output head featureclass is in a correct format
        if headFeatClass.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output head featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output foot featureclass is in a correct format
        if footFeatClass.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output foot featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # calculate compactness attribute
        helper.calculateCompactness(inFeatClass)
        # calculate circularity, convexity and solidity attributes
        helper.calculateCircularity_Convexity_Solidity(inFeatClass)
        # calculate sinuosity, length to width ratio, width to depth ratio, and other shape attributes
        helper.calculateSinuosity_LwR_WdR_Slopes(
            workspaceName,
            tempFolder,
            inFeatClass,
            inBathy,
            headFeatClass,
            footFeatClass,
            additionalOption,
        )
        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


class Add_Topographic_Attributes_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Topographic Attributes High Tool"
        self.description = "Add Topographic Attributes to the Bathymetric High features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Features",
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

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Input Slope Raster",
            name="slopeRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        parameters = [param0, param1, param2, param3]
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
        inBathy = parameters[2].valueAsText
        inSlope = parameters[3].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        inBathy = helper.convert_backslach_forwardslach(inBathy)
        inSlope = helper.convert_backslach_forwardslach(inSlope)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)
        # if the input slope raster is selected from a drop-down list, the inSlope does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inSlope.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inSlope == lyr.name:
                        inSlope = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
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

        # check that the input slope grid is in a correct format
        rasDesc1 = arcpy.Describe(inSlope)
        rasFormat1 = rasDesc1.format
        if rasFormat1 != "FGDBR":
            messages.addErrorMessage(
                "The input slope raster must be a raster dataset in a File GeoDatabase!"
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

        # check that the input slope grid is in a projected coordinate system
        spatialReference = rasDesc1.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input slope grid is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True
        itemList = []
        fieldList = [
            "minDepth",
            "maxDepth",
            "depthRange",
            "meanDepth",
            "stdDepth",
            "minGradient",
            "maxGradient",
            "gradientRange",
            "meanGradient",
            "stdGradient",
        ]

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # add new topographic fields
        for field in fieldList:
            fieldType = "DOUBLE"
            fieldPrecision = 15
            fieldScale = 6
            if field in field_names:
                arcpy.AddMessage(field + " exists")
            else:
                arcpy.AddField_management(
                    inFeatClass, field, fieldType, fieldPrecision, fieldScale
                )

        # zonal statistics
        zoneField = "featID"
        outTab1 = "outTab1"
        outTab2 = "outTab2"
        itemList.append(outTab1)
        itemList.append(outTab2)
        outZ1 = ZonalStatisticsAsTable(
            inFeatClass, zoneField, inBathy, outTab1, "DATA", "ALL"
        )
        outZ2 = ZonalStatisticsAsTable(
            inFeatClass, zoneField, inSlope, outTab2, "DATA", "ALL"
        )

        # calculate these topographic fields
        field = "minDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MIN" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "maxDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MAX" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "depthRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "RANGE" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "meanDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MEAN" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "stdDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "STD" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "minGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MIN" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "maxGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MAX" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "gradientRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "RANGE" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "meanGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MEAN" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "stdGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "STD" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        arcpy.AddMessage("All attributes added")
        # delete intermediate files
        helper.deleteDataItems(itemList)
        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


class Add_Topographic_Attributes_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Topographic Attributes Low Tool"
        self.description = "Add Topographic Attributes to the Bathymetric Low features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Features",
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

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Input Slope Raster",
            name="slopeRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Input Head Features",
            name="headFeatClass",
            datatype="GPFeatureLayer",
            parameterType="required",
            direction="Input",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Input Foot Features",
            name="footFeatClass",
            datatype="GPFeatureLayer",
            parameterType="required",
            direction="Input",
        )

        parameters = [param0, param1, param2, param3, param4, param5]
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
        inBathy = parameters[2].valueAsText
        inSlope = parameters[3].valueAsText
        headFeatClass = parameters[4].valueAsText
        footFeatClass = parameters[5].valueAsText

        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        inBathy = helper.convert_backslach_forwardslach(inBathy)
        inSlope = helper.convert_backslach_forwardslach(inSlope)
        headFeatClass = helper.convert_backslach_forwardslach(headFeatClass)
        footFeatClass = helper.convert_backslach_forwardslach(footFeatClass)

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)
        # if the input slope raster is selected from a drop-down list, the inSlope does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inSlope.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inSlope == lyr.name:
                        inSlope = helper.convert_backslach_forwardslach(lyr.dataSource)
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if headFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if headFeatClass == lyr.name:
                        headFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if footFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if footFeatClass == lyr.name:
                        footFeatClass = helper.convert_backslach_forwardslach(
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

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(inBathy)
        rasFormat = rasDesc.format
        if rasFormat != "FGDBR":
            messages.addErrorMessage(
                "The input bathymetry raster must be a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input slope grid is in a correct format
        rasDesc1 = arcpy.Describe(inSlope)
        rasFormat1 = rasDesc1.format
        if rasFormat1 != "FGDBR":
            messages.addErrorMessage(
                "The input slope raster must be a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input head feature class is in a correct format
        vecDesc1 = arcpy.Describe(headFeatClass)
        vecType1 = vecDesc1.dataType
        if (vecType1 != "FeatureClass") or (headFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input head featureclass must be a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the input foot feature class is in a correct format
        vecDesc2 = arcpy.Describe(footFeatClass)
        vecType2 = vecDesc2.dataType
        if (vecType2 != "FeatureClass") or (footFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage(
                "The input foot featureclass must be a feature class in a File GeoDatabase!"
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

        # check that the input slope grid is in a projected coordinate system
        spatialReference = rasDesc1.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input slope grid is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        # check that the input head featureclass is in a projected coordinate system
        spatialReference = vecDesc1.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input head featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        # check that the input foot featureclass is in a projected coordinate system
        spatialReference = vecDesc2.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage(
                "Coordinate system of input foot featureclass is Geographic. A projected coordinate system is required!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
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
            "minGradient",
            "maxGradient",
            "gradientRange",
            "meanGradient",
            "stdGradient",
        ]

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # check the 'head_foot_length' field exists
        if "head_foot_length" not in field_names:
            messages.addErrorMessage(
                inFeatClass
                + " does not have the head_foot_length attribute. Please use the Add_Shape_Attribute_Tool to calculate the attribute."
            )
            raise arcpy.ExecuteError
        # check the depth attributes field exist in the headFeatClass
        fields1 = arcpy.ListFields(headFeatClass)
        field_names1 = [f.name for f in fields1]
        if ("depth" not in field_names1) | ("depth1" not in field_names1):
            messages.addErrorMessage(
                headFeatClass
                + " does not have the required depth attributes. Please use the Add_Shape_Attribute_Tool to generate the head featureclass with the required depth attributes."
            )
            raise arcpy.ExecuteError

        fields2 = arcpy.ListFields(footFeatClass)
        field_names2 = [f.name for f in fields2]
        if ("depth" not in field_names2) | ("depth1" not in field_names2):
            messages.addErrorMessage(
                footFeatClass
                + " does not have the required depth attributes. Please use the Add_Shape_Attribute_Tool to generate the foot featureclass with the required depth attributes."
            )
            raise arcpy.ExecuteError

        # add new topographic fields
        for field in fieldList:
            fieldType = "DOUBLE"
            fieldPrecision = 15
            fieldScale = 6
            if field in field_names:
                arcpy.AddMessage(field + " exists")
            else:
                arcpy.AddField_management(
                    inFeatClass, field, fieldType, fieldPrecision, fieldScale
                )

        # zonal statistics
        zoneField = "featID"
        outTab1 = "outTab1"
        outTab2 = "outTab2"
        itemList.append(outTab1)
        itemList.append(outTab2)
        outZ1 = ZonalStatisticsAsTable(
            inFeatClass, zoneField, inBathy, outTab1, "DATA", "ALL"
        )
        outZ2 = ZonalStatisticsAsTable(
            inFeatClass, zoneField, inSlope, outTab2, "DATA", "ALL"
        )
        # calculate these fields
        field = "minDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MIN" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "maxDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MAX" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "depthRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "RANGE" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "meanDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MEAN" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "stdDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "STD" + "!"
        helper.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "minGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MIN" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "maxGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MAX" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "gradientRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "RANGE" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "meanGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MEAN" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "stdGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "STD" + "!"
        helper.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        # spatial join
        joinFeat1 = "joinFeat1"
        itemList.append(joinFeat1)
        arcpy.SpatialJoin_analysis(inFeatClass, headFeatClass, joinFeat1)

        joinFeat2 = "joinFeat2"
        itemList.append(joinFeat2)
        arcpy.SpatialJoin_analysis(inFeatClass, footFeatClass, joinFeat2)

        # selection analysis
        selectFeat1 = "selectFeat1"
        itemList.append(selectFeat1)
        whereClause = '"depth" IS NULL'
        arcpy.Select_analysis(joinFeat1, selectFeat1, whereClause)

        selectFeat2 = "selectFeat2"
        itemList.append(selectFeat2)
        whereClause = '"depth" IS NOT NULL'
        arcpy.Select_analysis(joinFeat1, selectFeat2, whereClause)
        # if the depth is null, replace it with the depth1 field
        arcpy.CalculateField_management(selectFeat1, "depth", "!depth1!", "PYTHON_9.3")
        mergedFeat1 = "mergedFeat1"
        itemList.append(mergedFeat1)
        mergedFeats = [selectFeat1, selectFeat2]
        arcpy.Merge_management(mergedFeats, mergedFeat1)

        # selection analysis
        selectFeat3 = "selectFeat3"
        itemList.append(selectFeat3)
        whereClause = '"depth" IS NULL'
        arcpy.Select_analysis(joinFeat2, selectFeat3, whereClause)

        selectFeat4 = "selectFeat4"
        itemList.append(selectFeat4)
        whereClause = '"depth" IS NOT NULL'
        arcpy.Select_analysis(joinFeat2, selectFeat4, whereClause)

        arcpy.CalculateField_management(selectFeat3, "depth", "!depth1!", "PYTHON_9.3")
        mergedFeat2 = "mergedFeat2"
        itemList.append(mergedFeat2)
        mergedFeats = [selectFeat3, selectFeat4]
        arcpy.Merge_management(mergedFeats, mergedFeat2)

        field = "headDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + mergedFeat1 + "." + "depth" + "!"
        helper.addField(inFeatClass, mergedFeat1, field, inID, joinID, expression)

        field = "footDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + mergedFeat2 + "." + "depth" + "!"
        helper.addField(inFeatClass, mergedFeat2, field, inID, joinID, expression)

        field = "head_foot_depthRange"
        inID = "featID"
        joinID = "featID"
        expression = "!headDepth! - !footDepth!"
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")

        field = "head_foot_gradient"
        inID = "featID"
        joinID = "featID"
        expression = (
            "math.degrees(math.atan(!head_foot_depthRange! / !head_foot_length!))"
        )
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")

        arcpy.AddMessage("All attributes added")

        helper.deleteDataItems(itemList)
        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


class Add_Profile_Attributes_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Profile Attributes High Tool"
        self.description = "Add Profile Attributes to the Bathymetric High features"
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
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )
        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )
        param2.parameterDependencies = [param0.name]

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="required",
            direction="Input",
        )

        parameters = [param0, param1, param2, param3, param4]
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

        # the code below turns off theSettingwithCopyWarning related to pandas dataframe procesing which would cause arcpy to throw exceptions
        # pd.set_option('mode.chained_assignment',None)

        inFeatClass = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        outFeatClass = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tempFolder = parameters[4].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        tempFolder = helper.convert_backslach_forwardslach(tempFolder)
        inBathy = helper.convert_backslach_forwardslach(inBathy)
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
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

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True
        # areaThreshold input has two components: the threshold value and the area unit
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # check the 'LengthWidthRatio' field exists
        if "LengthWidthRatio" not in field_names:
            messages.addErrorMessage(
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can run. Please use Add Shape Attribute Tool to calculate the attribute"
            )
            raise arcpy.ExecuteError

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
        for field in fieldList:
            if field in field_names:
                arcpy.AddMessage(field + " already exists and will be deleted")
                arcpy.DeleteField_management(inFeatClass, field)

        itemList1 = []
        # expand inBathy
        # This is to ensure that the profile point(s) at the edge of bathymetry grid have depth values
        inFocal = inBathy + "_focal"
        itemList1.append(inFocal)
        outFocalStat = FocalStatistics(
            inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
        )
        outFocalStat.save(inFocal)
        # mosaic to new raster
        mosaicBathy = "mosaicBathy"
        itemList1.append(mosaicBathy)
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
        converter = helper.areaUnitConverter(areaUnit)
        areaThresholdValue = converter * float(areaThresholdValue)
        # convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        # generate bounding rectangle
        MbrFeatClass = "bounding_rectangle"
        itemList1.append(MbrFeatClass)
        arcpy.MinimumBoundingGeometry_management(
            inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )
        arcpy.AddMessage("bouning rectangle generated")
        noFeat = int(arcpy.GetCount_management(inFeatClass).getOutput(0))
        noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
        arcpy.AddMessage("noFeat: " + str(noFeat))
        arcpy.AddMessage("noRectangle: " + str(noRectangle))
        # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
        # if not, regenerate the bounding rectanlge up to three times
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
                            + " doesnot equal to noFeat: "
                            + str(noFeat)
                        )

        # loop through each input feature
        cursor = arcpy.SearchCursor(inFeatClass)
        # to catch the failed feature(s)
        failedIDList = []
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
                    helper.create_profiles3(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile3.")
                elif (
                    LwR <= 5.0
                ):  # for a polygon feature that is not elongated, create five profiles passing through the polygon centre
                    time1 = datetime.now()
                    helper.create_profiles1(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profiles1.")
                else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                    time1 = datetime.now()
                    helper.create_profiles2(
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
                    ) = helper.calculate_profile_attributes_high(
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
                        inFeat, field, expression, "PYTHON_9.3"
                    )
                    i += 1

                arcpy.AddMessage("profile fields calculated")

                # delete intermediate data
                helper.deleteDataItems(itemList)
                arcpy.AddMessage("intermediate data deleted")
            except:
                arcpy.AddMessage("failed on " + str(featID))
                failedIDList.append(featID)
                continue
            k += 1

        del cursor, row

        # merge all individual features together
        mergedFeat = "mergedFeat"
        arcpy.Merge_management(mergeList, mergedFeat)
        arcpy.AddMessage("merged all done")

        helper.deleteDataItems(mergeList)
        helper.deleteDataItems(itemList1)
        arcpy.AddMessage("data deletion done")

        # transfer the field values to inFeatClass

        for field in fieldList:
            inID = "featID"
            joinID = "featID"
            expression = "!" + mergedFeat + "." + field + "!"
            helper.addTextField(
                inFeatClass, mergedFeat, field, inID, joinID, expression
            )

        arcpy.AddMessage("Profile attributes added and calculated")

        arcpy.Delete_management(mergedFeat)

        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


class Add_Profile_Attributes_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Profile Attributes Low Tool"
        self.description = "Add Profile Attributes to the Bathymetric Low features"
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
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )
        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output",
        )
        param2.parameterDependencies = [param0.name]

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter
        param4 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
            parameterType="required",
            direction="Input",
        )

        parameters = [param0, param1, param2, param3, param4]
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

        # the code below turns off theSettingwithCopyWarning related to pandas dataframe procesing which would cause arcpy to throw exceptions
        # pd.set_option('mode.chained_assignment',None)

        inFeatClass = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        outFeatClass = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tempFolder = parameters[4].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)
        tempFolder = helper.convert_backslach_forwardslach(tempFolder)
        inBathy = helper.convert_backslach_forwardslach(inBathy)
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(
                            lyr.dataSource
                        )
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType
        if (vecType != "FeatureClass") or (inFeatClass.rfind(".gdb") == -1):
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

        workspaceName = inFeatClass[0 : inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeatClass, "featID")

        # checck the 'LengthWidthRatio' field exists
        if "LengthWidthRatio" not in field_names:
            messages.addErrorMessage(
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can be run. Please use Add Shape Attribute Tool to calculate the attribute"
            )
            raise arcpy.ExecuteError

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
        for field in fieldList:
            if field in field_names:
                arcpy.AddMessage(field + " already exists and will be deleted")
                arcpy.DeleteField_management(inFeatClass, field)

        itemList1 = []
        # expand inBathy
        # This is to ensure that the profile point(s) at the edge of bathymetry grid have depth values
        inFocal = inBathy + "_focal"
        itemList1.append(inFocal)
        outFocalStat = FocalStatistics(
            inBathy, NbrRectangle(3, 3, "CELL"), "MEAN", "DATA"
        )
        outFocalStat.save(inFocal)
        # mosaic to new raster
        mosaicBathy = "mosaicBathy"
        itemList1.append(mosaicBathy)
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
        converter = helper.areaUnitConverter(areaUnit)
        areaThresholdValue = converter * float(areaThresholdValue)
        # convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        # generate bounding rectangle
        MbrFeatClass = "bounding_rectangle"
        itemList1.append(MbrFeatClass)
        arcpy.MinimumBoundingGeometry_management(
            inFeatClass, MbrFeatClass, "RECTANGLE_BY_WIDTH", "NONE", "", "MBG_FIELDS"
        )
        noFeat = int(arcpy.GetCount_management(inFeatClass).getOutput(0))
        noRectangle = int(arcpy.GetCount_management(MbrFeatClass).getOutput(0))
        arcpy.AddMessage("noFeat: " + str(noFeat))
        arcpy.AddMessage("noRectangle: " + str(noRectangle))
        # Number of features in the bounding rectangle is expected to be the same as in the input featureclass
        # if not, regenerate the bounding rectanlge up to three times
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
                            + " doesnot equal to noFeat: "
                            + str(noFeat)
                        )
        cursor = arcpy.SearchCursor(inFeatClass)
        failedIDList = []
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
                    helper.create_profiles3(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile3.")
                elif (
                    LwR <= 5.0
                ):  # for a polygon feature that is not elongated, create five profiles passing through the polygon centre
                    time1 = datetime.now()
                    helper.create_profiles1(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile1.")
                else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                    time1 = datetime.now()
                    helper.create_profiles2(
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
                    ) = helper.calculate_profile_attributes_low(
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
                        inFeat, field, expression, "PYTHON_9.3"
                    )
                    i += 1

                arcpy.AddMessage("profile fields calculated")

                # delete intermediate data
                helper.deleteDataItems(itemList)
                arcpy.AddMessage("intermediate data deleted")

            except:
                arcpy.AddMessage("failed on " + str(featID))
                failedIDList.append(featID)
                continue
            k += 1

        del cursor, row
        # merge all individual features together
        mergedFeat = "mergedFeat"
        arcpy.Merge_management(mergeList, mergedFeat)
        arcpy.AddMessage("merged all done")

        helper.deleteDataItems(itemList1)
        helper.deleteDataItems(mergeList)
        arcpy.AddMessage("data deletion done")

        # transfer the field values to inFeatClass

        for field in fieldList:
            inID = "featID"
            joinID = "featID"
            expression = "!" + mergedFeat + "." + field + "!"
            helper.addTextField(
                inFeatClass, mergedFeat, field, inID, joinID, expression
            )

        arcpy.AddMessage("Profile attributes added and calculated")

        arcpy.Delete_management(mergedFeat)

        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        # compact the geodatabase to reduce its size
        arcpy.Compact_management(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return


# All the helper functions are defined here
class helpers:
    # This function splits each polygon in the featureclass into mutiple sub-polygons along its long axis
    def splitPolygon(self, workspace, inFeatClass, MbrFeatClass, splitFeatClass):
        # workspace: location of workspace
        # inFeatClass: input Bathymetric High (Low) features
        # MbrFeatClass: input bounding recentagle featureclass
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
            MbrO = row1.getValue("rectangle_Orientation")
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
            # determine the size of each cell (sub-polygon) based on the length of bounding recentagle (unit: metre)
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

            oppositeCoorner = "#"
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
                oppositeCoorner,
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
        self.deleteDataItems(itemList)

    # This function calculates a converter value for the input area unit. The base unit is "SquareKilometers".
    def areaUnitConverter(self, inAreaUnit):
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

    # This function converts backslach (accepted through the ArcGIS tool) to forwardslach (needed in python script) in a path
    def convert_backslach_forwardslach(self, inText):
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

    # This function adds and calculates fields with Double type
    def addField(self, inFeat, joinFeat, fieldName, inID, joinID, expression):
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

        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")

        arcpy.RemoveJoin_management(layerName, joinFeat)

        arcpy.Delete_management(layerName)
        arcpy.AddMessage(fieldName + " added and calculated")
        return

    # added 2023-06-20
    # This function delete fields not to be kept
    def deleteFields(self, inFeat, fieldsTokeep):
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
    def addTextField(self, inFeat, joinFeat, fieldName, inID, joinID, expression):
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

        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")

        arcpy.RemoveJoin_management(layerName, joinFeat)

        arcpy.Delete_management(layerName)
        arcpy.AddMessage(fieldName + " added and calculated")
        return

    # This function adds a featID field with unique ID values
    def addIDField(self, inFeat, fieldName):
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

    # This function deletes all intermediate data items
    def deleteDataItems(self, inDataList):
        # inDataList: a list of data items to be deleted

        if len(inDataList) == 0:
            arcpy.AddMessage("no data item in the list")
        else:
            for item in inDataList:
                arcpy.AddMessage("Deleting " + item)
                arcpy.Delete_management(item)
        return

    # This functions calculates Compactness
    def calculateCompactness(self, inFeatClass):
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
            inFeatClass, fieldName, expression, "PYTHON_9.3"
        )
        arcpy.AddMessage(fieldName + " added and calculated")

    # This function calculates Circularity, Convexity and Solidity
    def calculateCircularity_Convexity_Solidity(self, inFeatClass):
        # inFeatClass: input Bathymetry High (Low) features

        itemList = []
        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
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
        self.addField(inFeatClass, chFeat, field, inID, joinID, expression)
        field = "convexhull_Perimeter"
        expression = "!" + chFeat + "." + "SHAPE_LENGTH" + "!"
        self.addField(inFeatClass, chFeat, field, inID, joinID, expression)
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
                # Solidiy equation
                expression = (
                    "!" + "SHAPE_AREA" + "!" + "/" + "!" + "convexhull_Area" + "!"
                )

            arcpy.CalculateField_management(
                inFeatClass, fieldName, expression, "PYTHON_9.3"
            )
        arcpy.AddMessage(" Circularity, Convexity and Solidity added and calculated")
        self.deleteDataItems(itemList)

    # This functions calculates sinuosity, length to width ratio, and other shape attributes for the Bathymetric High features
    def calculateSinuosity_LwR(self, workspace, tempFolder, inFeatClass, inBathy):
        # workspace: the location of the workspace
        # tempFolder: the location of the temporary folder
        # inFeatClass: input Bathymetry High (Low) features
        # inBathy: input bathymetry grid

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
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
        field = "rectangle_Width"
        expression = "!" + MbrFeatClass + "." + "MBG_Width" + "!"
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
        field = "rectangle_Orientation"
        expression = "!" + MbrFeatClass + "." + "MBG_Orientation" + "!"
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
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
        self.splitPolygon(workspace, inFeatClass, MbrFeatClass, splitFeatClass)
        arcpy.AddMessage("inFeatClass splitted")
        # convert polygon to line
        lineFeatClass1 = workspace + "/" + "lineFeatClass1"
        itemList.append(lineFeatClass1)
        arcpy.PolygonToLine_management(splitFeatClass, lineFeatClass1)
        arcpy.AddMessage("ploygon to line done")
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
        self.addField(inFeatClass, outTab2, field, inID, joinID, expression)
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
        self.deleteFields(inFeatVertices, fieldsToKeep)
        arcpy.AddMessage("delete fields done")

        arcpy.CopyRows_management(inFeatVertices, csvFile1)
        arcpy.AddMessage("export to first csv done")
        # read the csv file as a pandas data frame, add dtype parameter (2023-06-20)
        # this is to prevent mix type warning and potentially improve efficency in reading a large csv file
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
        # The idea is to find a point representing 'head' (or first) and a point representing 'foot' (or last) of the feature
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

        arcpy.CopyRows_management(pointFeat1, csvFile2)
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

        lineFeat1_2 = "curveLine2"
        itemList.append(lineFeat1_2)
        lineField = "featID"
        sortField = "OBJECTID"
        # Execute PointsToLine
        arcpy.PointsToLine_management(mergedFeat1_2, lineFeat1_2, lineField, sortField)
        arcpy.AddMessage("points to curve line done")

        # merge curvelines
        # We donot know which curveline is the true curveline connecting the points in correct order.
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

        # merge to create a straight line connecting the first and last point in order to calculate the straight length (head to foot length)
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
        arcpy.AddMessage("points to straight line done")

        # add sinuous_length field
        field = "sinuous_length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + "outTab3" + "." + "MIN_Shape_Length" + "!"
        self.addField(inFeatClass, outTab3, field, inID, joinID, expression)
        arcpy.AddMessage("add sinuous_length field done")
        # add head_foot_length field
        field = "head_foot_length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + "straightLine" + "." + "Shape_Length" + "!"
        self.addField(inFeatClass, lineFeat2, field, inID, joinID, expression)
        arcpy.AddMessage("add heat_foot_length field done")
        field = "Sinuosity"
        expression = "!sinuous_length! / !head_foot_length!"
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")
        arcpy.AddMessage("caculate Sinuosity field done")
        field = "LengthWidthRatio"
        expression = "!sinuous_length! / !mean_width!"
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")
        arcpy.AddMessage("calculate LengthWidthRatio field done")
        self.deleteDataItems(itemList)
        arcpy.AddMessage("data deletion done")
        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to have all attributes generated.")

    # This function calculates mean_segment_slope attribute.
    # mean_segment_slope: A number of linear segments are created by connecting the head, each point of minimum depth on a profile, and the foot.
    # The slopes of the segments are calculated and averaged as this mean_segment_slope value.
    def calculate_segmentSlope(
        self, inFeat, inTab, dissolveLineFeat, headFeat, footFeat, outFeat
    ):
        # inFeat: input point featureclass represents points along the cross-feature profiles, each point must have a depth value
        # inTab: input table that has some statistical values calculated from inFeat
        # dissolveLineFeat: the name of the line featureclass resulted from dissolving the inLineFeat
        # headFeat: input head feature
        # footFeat: input foot feature
        # outFeat: output point featureclass represents the start and end points of line segements

        itemList = []
        # for each profile, select a point with the minimum depth
        # the outFeat is the output also used in the Near_analysis function that follow this function
        field = "min_depth"
        inID = "RIGHT_FID"
        joinID = "RIGHT_FID"
        expression = "!" + inTab + "." + "MIN_RASTERVALU" + "!"
        self.addField(inFeat, inTab, field, inID, joinID, expression)
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
            distance = self.calculateDistance(headX, headY, footX, footY)
            # calculate slope between head and foot as the mean_segment_slope
            meanSlope = abs(self.calculateSlope(footDepth, headDepth, distance))
        else:
            # each feature in outFeat2 represents one or multiple points that have the minimum depth along a profile
            # multiple points along a profile may have the same depth value as the minimum depth
            # in this case, only one point is selected by compiling a ids_tobeDeleted list
            # add and calculate field
            # sort
            outFeat3 = "outFeat2_sorted"
            itemList.append(outFeat3)
            sortField = [["RIGHT_FID", "Descending"]]
            arcpy.Sort_management(outFeat2, outFeat3, sortField)
            ## get a list of ids and fids
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
                idV = idList[i]
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
            idList = []
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
                distance = self.calculateDistance(startX, startY, endX, endY)
                slope = abs(
                    self.calculateSlope(endDepthList[i], startDepthList[i], distance)
                )
                slopeList.append(slope)
                i += 1
            # calculate mean segment slope
            meanSlope = np.nanmean(np.asarray(slopeList))
        self.deleteDataItems(itemList)
        return meanSlope

    # This function calculats 8 additional attributes: mean_width_thickness_ratio, std_width_thickness_ratio, mean_thickness, mean_segment_slope,
    # width_distance_slope, width_distance_correlation, thick_distance_slope, and thick_distance_correlation. These attributes are used to
    # classify Gully, Valley and Channel, and Canyon features.
    # mean_thickness: calculated as the mean feature thickness (top depth minus bottom depth) of a number of cross-feature profiles
    # mean_width_thickness_ratio: mean ratio between the width and the thickness of five profiles
    # std_width_thickness_ratio: standard deviation of the ratios between the width and the thickness of a number of profiles
    # mean_segment_slope: A number of linear segments are created by connecting the head, each point of minimum depth on a profile, and the foot. The slopes of the segments are calculated and averaged as this value.
    # width_distance_slope: The slope of the linear fitting line between the widths of the sub-polygons and the distances of the sub-polygons to the feature head
    # width_distance_correlation: The correlation coefficient between the widths of the sub-polygons and the distances of the sub-polygons to the feature head
    # thick_distance_slope: The slope of the linear fitting line between the thicknesses of the sub-polygons and the distances of the sub-polygons to the feature head
    # thick_distance_correlation: The correlation coefficient between the thicknesses of the sub-polygons and the distances of the sub-polygons to the feature head
    def calculate_Ratio_Slopes(
        self, inLineFeat, inBathy, dissolveLineFeat, headFeat, footFeat
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
        # This calculates the minimum depth of the start and end points of the profile, which represents the surface depth of the feature
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
        meanSlope = self.calculate_segmentSlope(
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
        self.addField(dissolveLineFeat, outTab1, field, inID, joinID, expression)

        field = "min_depth"
        inID = "RIGHT_FID"
        joinID = "RIGHT_FID"
        expression = "!" + outTab2 + "." + "MIN_RASTERVALU" + "!"
        self.addField(dissolveLineFeat, outTab2, field, inID, joinID, expression)

        field = "distance"
        inID = "RIGHT_FID"
        joinID = "RIGHT_FID"
        expression = "!" + outFeat1 + "." + "NEAR_DIST" + "!"
        self.addField(dissolveLineFeat, outFeat1, field, inID, joinID, expression)

        # feature thickness equals surface depth minus bottom depth
        field = "thickness"
        expression = "!surface_depth! - !min_depth!"
        arcpy.CalculateField_management(
            dissolveLineFeat, field, expression, "PYTHON_9.3"
        )

        field = "widthThicknessRatio"
        expression = "abs(!Shape_Length! / !thickness!)"
        arcpy.CalculateField_management(
            dissolveLineFeat, field, expression, "PYTHON_9.3"
        )

        ratioList = []
        widthList = []
        distList = []
        thickList = []
        cursor = arcpy.SearchCursor(dissolveLineFeat)
        # loop through each profile
        for row in cursor:
            ratio = row.getValue("widthThicknessRatio")
            if ratio == None:  # caused by thickness = 0
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

        self.deleteDataItems(itemList)
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

    # This function calculats the mean segment slope attribute. This attribute is used to
    # classify Gully, Valley and Channel, and Canyon features.
    # mean_segment_slope: A number of linear segments are created by connecting the head, each point of minimum depth on a profile, and the foot. The slopes of the segments are calculated and averaged as this value.
    def calculate_meansegment_Slopes(
        self, inLineFeat, inBathy, dissolveLineFeat, headFeat, footFeat
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
        # This calculates the minimum depth of the start and end points of the profile, which represents the surface depth of the feature
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
        meanSlope = self.calculate_segmentSlope(
            depthFeat2, outTab2, dissolveLineFeat, headFeat, footFeat, outFeat1
        )

        self.deleteDataItems(itemList)
        return meanSlope

    # This function calculates sinuosity, length to width ratio, width to depth (thickness) ratio, and a number of other attributes for the Bathymetric Low features
    def calculateSinuosity_LwR_WdR_Slopes(
        self,
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
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
        field = "rectangle_Width"
        expression = "!" + MbrFeatClass + "." + "MBG_Width" + "!"
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
        field = "rectangle_Orientation"
        expression = "!" + MbrFeatClass + "." + "MBG_Orientation" + "!"
        self.addField(inFeatClass, MbrFeatClass, field, inID, joinID, expression)
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
            arcpy.AddMessage("Wonot calculate additional attributes")
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
        self.splitPolygon(workspace, inFeatClass, MbrFeatClass, splitFeatClass)
        arcpy.AddMessage("inFeatClass splitted")
        # convert polygon to line
        lineFeatClass1 = workspace + "/" + "lineFeatClass1"
        itemList.append(lineFeatClass1)
        arcpy.PolygonToLine_management(splitFeatClass, lineFeatClass1)
        arcpy.AddMessage("ploygon to line done")
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
        self.addField(inFeatClass, outTab2, field, inID, joinID, expression)
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
        self.deleteFields(inFeatVertices, fieldsToKeep)
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
        # The idea is to find a point representing 'head' (first) and a point representing 'foot' (last) of the Bathymetric Low feature
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

        arcpy.CopyRows_management(pointFeat1, csvFile2)
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

        lineFeat1_2 = "curveLine2"
        itemList.append(lineFeat1_2)
        lineField = "featID"
        sortField = "OBJECTID"
        # Execute PointsToLine
        arcpy.PointsToLine_management(mergedFeat1_2, lineFeat1_2, lineField, sortField)
        arcpy.AddMessage("points to curve line done")

        # merge curvelines
        # We donot know which curveline is the true curveline connecting the points in correct order.
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

        # merge to create a straight line connecting the first and last point in order to calculate the straight length (head to foot length)
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
        arcpy.AddMessage("points to straight line done")

        # add sinuous_length field
        field = "sinuous_length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + "outTab3" + "." + "MIN_Shape_Length" + "!"
        self.addField(inFeatClass, outTab3, field, inID, joinID, expression)
        arcpy.AddMessage("add sinuous_length field done")
        # calculate and add head_foot_length, sinuosity and LengthWidthRatio fields
        field = "head_foot_length"
        inID = "featID"
        joinID = "featID"
        expression = "!" + "straightLine" + "." + "Shape_Length" + "!"
        self.addField(inFeatClass, lineFeat2, field, inID, joinID, expression)
        arcpy.AddMessage("add heat_foot_length field done")
        field = "Sinuosity"
        expression = "!sinuous_length! / !head_foot_length!"
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")
        arcpy.AddMessage("caculate Sinuosity field done")
        field = "LengthWidthRatio"
        expression = "!sinuous_length! / !mean_width!"
        arcpy.CalculateField_management(inFeatClass, field, expression, "PYTHON_9.3")
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
                # These 8 attributes: mean_width_thickness_ratio, std_width_thickness_ratio, mean_thickness, mean_segment_slope,
                # width_distance_slope, width_distance_correlation, thick_distance_slope, and thick_distance_correlation are used to
                # classify Gully, Valley and Channel features. These three types of features are elongated features with large LengthWidthRatio.
                if (
                    lwRatio < 5
                ):  # skipping the non-elongated features and assigning them default values. This saves a lot time calulating these attributes.
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
                    ) = self.calculate_Ratio_Slopes(
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
                ):  # skipping the non-elongated features and assigning them default values. This saves a lot time calulating these attributes.
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
                    meanSlope = self.calculate_meansegment_Slopes(
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

        self.deleteDataItems(itemList)
        arcpy.AddMessage("data deletion done")
        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to have all attributes generated.")
        return

    # This function generates five profiles passing through the centre point
    def create_profiles1(self, inFeat, rectangleFeat, outPointFeat, tempFolder):
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
        # if the centre point is not inside the polygon (e.g., in case of a multipart feature after using the connection tools)
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
            # normally, the lineFC1 should only have one feature,
            # but occasionally it has 2 or more features due to the default cluster tolerance setting in the above intersect analysis
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
                if lineLength > 10000:
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
                # add a ID field
                fieldType = "LONG"
                fieldPrecision = 10
                fieldName = "profileID"
                arcpy.AddField_management(lineFC1, fieldName, fieldType, fieldPrecision)
                expression = oID
                arcpy.CalculateField_management(
                    lineFC1, fieldName, expression, "PYTHON_9.3"
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
        self.deleteDataItems(itemList)

    # This function generates five cross-feature profiles
    def create_profiles2(self, inFeat, rectangleFeat, outPointFeat, tempFolder):
        # inFeat: input polygon feature represents a Bathymetry High (Low) feature
        # rectangleFeat: input polygon feature represents the bounding rectangle of the Bathymetry High (Low) feature
        # outPointFeat: output point featureclass represents all profile points
        # tempFolder: the location of temporal folder

        itemList = []
        cursor = arcpy.SearchCursor(rectangleFeat)
        row = cursor.next()
        MbrA = row.getValue("MBG_Orientation")
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

        oppositeCoorner = "#"

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
            oppositeCoorner,
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

                # normally, the lineFC1 should only have one feature,
                # but occasionally it has 0 feature due to intersecting with a point (or does not intersect the feature at all, e.g., in case of the feature is linearly connected multipart feature)
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
                    if lineLength > 10000:
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

                    # add a ID field
                    fieldType = "LONG"
                    fieldPrecision = 10
                    fieldName = "profileID"
                    arcpy.AddField_management(
                        lineFC1, fieldName, fieldType, fieldPrecision
                    )
                    expression = oID
                    arcpy.CalculateField_management(
                        lineFC1, fieldName, expression, "PYTHON_9.3"
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
        # when none of the five cross-section profiles cross the input feature, we force it to generate one profile passing through the centre point
        else:
            arcpy.AddMessage(
                "None of the five cross-section profiles cross the input feature. Instead, we are creating one profile passing through the centre point."
            )
            self.create_profiles3(inFeat, rectangleFeat, outPointFeat, tempFolder)

        self.deleteDataItems(itemList)

    # This function generates one profile passing through the centre point
    def create_profiles3(self, inFeat, rectangleFeat, outPointFeat, tempFolder):
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
        # if the centre point is not inside the polygon (e.g., in case of a multipart feature after using the connection tools)
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
            # normally, the lineFC1 should only have one feature,
            # but occasionally it has 2 or more features due to the default cluster tolerance setting in the above intersect analysis
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
            if lineLength > 10000:
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
            # add a ID field
            fieldType = "LONG"
            fieldPrecision = 10
            fieldName = "profileID"
            arcpy.AddField_management(lineFC1, fieldName, fieldType, fieldPrecision)
            expression = oID
            arcpy.CalculateField_management(
                lineFC1, fieldName, expression, "PYTHON_9.3"
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
        self.deleteDataItems(itemList)

    # This function calculates eucliean distance between two points
    def calculateDistance(self, x1, y1, x2, y2):
        # x1,y1: coordinates of the start point
        # x2,y2: coordinates of the end point
        distance = np.sqrt(np.power(x1 - x2, 2) + np.power(y1 - y2, 2))
        return distance

    # This function calculates slope gradient of the line segment connecting two points
    def calculateSlope(self, e1, e2, d):
        # e1: elevation of the end point
        # e2: elevation of the start point
        # d: eucliean distance between the two point
        if d == 0:
            slope = 90.0
        else:
            slope = (e1 - e2) / d
            slope = np.degrees(np.arctan(slope))  # slope as degree
        return slope

    # This function calculates a slope threshold from a elevation (depth) profile
    # the slope threshold is the slope between the point with the maximum elevation and the point with the minimum elevation
    def calculateSlopeThreshold(self, profileDF, depthCol, xCol, yCol):
        # profileDF: profile data as a pandas dataframe
        # depthCol: the name of the depth column in the profileDF
        # xCol: the name of the x coordinate column in the profileDF
        # yCol: the name of the y coordinate column in the profileDF
        maxDepth = profileDF.loc[profileDF[depthCol] == profileDF[depthCol].max()]
        minDepth = profileDF.loc[profileDF[depthCol] == profileDF[depthCol].min()]
        dist = self.calculateDistance(
            maxDepth[xCol].values[0],
            maxDepth[yCol].values[0],
            minDepth[xCol].values[0],
            minDepth[yCol].values[0],
        )
        slope = self.calculateSlope(
            maxDepth[depthCol].values[0], minDepth[depthCol].values[0], dist
        )
        return slope

    # This is the main function conducting the profile analysis
    # The function is used to find knickpoint(s) along the profile
    def profileAnalysis(self, profileDF, depthCol, xCol, yCol, idArr, slopeThreshold):
        # profileDF: profile data as a pandas dataframe
        # depthCol: the name of the depth column in the profileDF
        # xCol: the name of the x coordinate column in the profileDF
        # yCol: the name of the y coordinate column in the profileDF
        # idArr: the id array
        # slopeThreshold: the desinated slope threshold
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
                    dist1 = self.calculateDistance(x, y, x1, y1)
                    slope1 = self.calculateSlope(depth, depth1, dist1)
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
                    dist1 = self.calculateDistance(x, y, x1, y1)
                    slope1 = self.calculateSlope(depth1, depth, dist1)
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
        # 2. must be larger than the desinated slope threshold;
        # 3. must be at least larger than 1.0 degree (to remove very flat profile).
        # selectedID = profileDF[profileDF.diffSlope>=max(profileDF.diffSlope.mean()+2*profileDF.diffSlope.std(),slopeThreshold,1)].index.values
        selectedID = profileDF.loc[
            profileDF.diffSlope
            >= max(profileDF.diffSlope.quantile(0.99), slopeThreshold, 1)
        ].index.values

        # removing the above row(s) from the profile data
        # profileDF = profileDF[profileDF.diffSlope<max(profileDF.diffSlope.mean()+2*profileDF.diffSlope.std(),slopeThreshold,1)]
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
    def findGroup(self, arr, gap):
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
    def profileSlope(self, profileDF, xCol, yCol, depthCol):
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
                dist = self.calculateDistance(
                    profileDF.iloc[i, xColIndex],
                    profileDF.iloc[i, yColIndex],
                    profileDF.iloc[0, xColIndex],
                    profileDF.iloc[0, yColIndex],
                )
                slope = abs(
                    self.calculateSlope(
                        profileDF.iloc[i, dColIndex], profileDF.iloc[0, dColIndex], dist
                    )
                )
                slList.append(slope)
                dList.append(dist)
            # other profile segments
            else:
                dist = self.calculateDistance(
                    profileDF.iloc[i, xColIndex],
                    profileDF.iloc[i, yColIndex],
                    profileDF.iloc[i + 1, xColIndex],
                    profileDF.iloc[i + 1, yColIndex],
                )
                slope = abs(
                    self.calculateSlope(
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
    def profileAngle(self, profileDF, slopeCol):
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
    def slopeClass(self, slope):
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
    def calculate_profile_attributes_high(self, profileDF, depthCol, xCol, yCol, gap):
        # profileDF: profile data as a pandas dataframe
        # depthCol: the name of the depth column in the profileDF
        # xCol: the name of the x coordinate column in the profileDF
        # yCol: the name of the y coordinate column in the profileDF
        # gap: the maximum gap allowed between knick points to form the group
        xColIndex = np.where(profileDF.columns.values == xCol)[0][0]
        yColIndex = np.where(profileDF.columns.values == yCol)[0][0]
        dColIndex = np.where(profileDF.columns.values == depthCol)[0][0]
        distL = []
        x = profileDF.iloc[0, xColIndex]
        y = profileDF.iloc[0, yColIndex]
        # loop through each profile
        for i in profileDF.index:
            x1 = profileDF.loc[i, xCol]
            y1 = profileDF.loc[i, yCol]
            dist = self.calculateDistance(x, y, x1, y1)
            distL.append(dist)
        profileDF.loc[:, "distance"] = distL

        profileDF_copy = profileDF.copy(deep=True)

        # initialise an id array
        idArr = np.arange(0)
        # calculate a slope threshold
        slopeThreshold = abs(
            self.calculateSlopeThreshold(profileDF_copy, depthCol, xCol, yCol)
        )

        # conduct the first round of profile analysis using the slopeThreshold
        profileDF_copy, idArr1, idArr2, diffSlope_95 = self.profileAnalysis(
            profileDF_copy, depthCol, xCol, yCol, idArr, slopeThreshold
        )

        # conduct the follwoing round(s) of profile analysis using the diffSlope_95 as the slopeThreshold
        # stop the loop when there is no element to be appended into the new array, thus the size of the input id array equals
        # the size of the updated id array
        while idArr2.size > idArr1.size:
            profileDF_copy, idArr1, idArr2, dumy_95 = self.profileAnalysis(
                profileDF_copy, depthCol, xCol, yCol, idArr2, diffSlope_95
            )

        # sort the id array
        idArray = np.sort(idArr2)
        idList = idArray.tolist()
        i = 0
        # find the ids groups
        while i < len(idList):
            if idArray.size > 0:
                idList[i], idArray = self.findGroup(idArray, gap)
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
            # the minimum value indeicates the id of the knick point
            z2.append(z_1[indexX])
            i += 1
        # select the key profileDF from the profile data to form a simplied profile (profileDF1)
        z2.insert(0, profileDF.index[0])
        z2.insert(len(z2), profileDF.index[-1])
        profileDF1 = profileDF.loc[z2].copy()
        # add 'knick_point' column
        profileDF.loc[:, "knick_point"] = profileDF.loc[:, "distance"] < 0
        profileDF.loc[z2, "knick_point"] = True

        dList, slList = self.profileSlope(profileDF1, xCol, yCol, depthCol)
        profileDF1.loc[:, "slope"] = slList
        profileDF1.loc[:, "dist"] = dList
        angleList = self.profileAngle(profileDF1, "slope")
        profileDF1.loc[:, "polygonAngle"] = angleList

        ## calculate profile attributes
        ## topSlopeClass: the slope class of the top of a bathymetic high; 'no top' indicates a triangle shape without top
        ## sideSlopeClass: the slope class of the sides of a bathmetric high
        ## shape: profile shape
        ## concave: profile concavity
        ## symmetry: profile symmetry
        ## topDepth: the depth of the top of a bathymetric high
        ## height: the height of the profile
        ## length: the length of the profile

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
            # to prevent divide by 0; changed on 20230419
            if (dist1 == 0) or (dist2 == 0):
                sideSlope = (slope1 + slope2) / 2
            else:
                sideSlope = slope1 * dist1 / (dist1 + dist2) + slope2 * dist2 / (
                    dist1 + dist2
                )
            slClass = self.slopeClass(sideSlope)
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
            slClass = self.slopeClass(sideSlope)
            sList = []
            i = 1
            while i < profileDF1.index.size - 2:
                s1 = profileDF1.iloc[i, sColIndex]
                sList.append(s1)
                i += 1
            # top slope equals the mean of the slopes of all non-side segments
            topSlope = abs(sum(sList) / len(sList))
            topClass = self.slopeClass(topSlope)
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
                self.calculateDistance(
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
    def calculate_profile_attributes_low(self, profileDF, depthCol, xCol, yCol, gap):
        # profileDF: profile data as a pandas dataframe
        # depthCol: the name of the depth column in the profileDF
        # xCol: the name of the x coordinate column in the profileDF
        # yCol: the name of the y coordinate column in the profileDF
        # gap: the maximum gap allowed between knick points to form the group

        xColIndex = np.where(profileDF.columns.values == xCol)[0][0]
        yColIndex = np.where(profileDF.columns.values == yCol)[0][0]
        dColIndex = np.where(profileDF.columns.values == depthCol)[0][0]
        distL = []
        x = profileDF.iloc[0, xColIndex]
        y = profileDF.iloc[0, yColIndex]
        for i in profileDF.index:
            x1 = profileDF.loc[i, xCol]
            y1 = profileDF.loc[i, yCol]
            dist = self.calculateDistance(x, y, x1, y1)
            distL.append(dist)
        profileDF.loc[:, "distance"] = distL
        profileDF_copy = profileDF.copy(deep=True)

        # initialise an id array
        idArr = np.arange(0)
        # calculate a slope threshold
        slopeThreshold = abs(
            self.calculateSlopeThreshold(profileDF_copy, depthCol, xCol, yCol)
        )
        # conduct the first round of profile analysis using the slopeThreshold
        profileDF_copy, idArr1, idArr2, diffSlope_95 = self.profileAnalysis(
            profileDF_copy, depthCol, xCol, yCol, idArr, slopeThreshold
        )
        # conduct the follwoing round(s) of profile analysis using the diffSlope_95 as the slopeThreshold
        # stop the loop when there is no element to be appended into the new array, thus the size of the input id array equals
        # the size of the updated id array
        while idArr2.size > idArr1.size:
            profileDF_copy, idArr1, idArr2, dumy_95 = self.profileAnalysis(
                profileDF_copy, depthCol, xCol, yCol, idArr2, diffSlope_95
            )

        # sort the id array
        idArray = np.sort(idArr2)
        idList = idArray.tolist()
        i = 0
        # find the ids groups
        while i < len(idList):
            if idArray.size > 0:
                idList[i], idArray = self.findGroup(idArray, gap)
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
            # the minimum value indeicates the id of the knick point
            z2.append(z_1[indexX])
            i += 1
        # select the key profileDF from the profile data to form a simplied profile (profileDF1)
        z2.insert(0, profileDF.index[0])
        z2.insert(len(z2), profileDF.index[-1])
        profileDF1 = profileDF.loc[z2].copy()
        # add 'knick_point' column
        profileDF.loc[:, "knick_point"] = profileDF.loc[:, "distance"] < 0
        profileDF.loc[z2, "knick_point"] = True

        dList, slList = self.profileSlope(profileDF1, xCol, yCol, depthCol)
        profileDF1.loc[:, "slope"] = slList
        profileDF1.loc[:, "dist"] = dList
        angleList = self.profileAngle(profileDF1, "slope")
        profileDF1.loc[:, "polygonAngle"] = angleList

        ## calculate profile attributes
        ## bottomSlopeClass: the slope class of the bottom of a bathymetic low; 'no bottom' indicates a triangle shape without bottom
        ## sideSlopeClass: the slope class of the sides of a bathmetric high
        ## shape: profile shape
        ## concave: profile concavity
        ## symmetry: profile symmetry
        ## bottomDepth: the depth of the bottom of a bathymetric low
        ## height: the relief of the profile
        ## length: the length of the profile

        sColIndex = np.where(profileDF1.columns.values == "slope")[0][0]
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
            slClass = self.slopeClass(sideSlope)
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
            slClass = self.slopeClass(sideSlope)
            sList = []
            i = 1
            while i < profileDF1.index.size - 2:
                s1 = profileDF1.iloc[i, sColIndex]
                sList.append(s1)
                i += 1
            # top slope equals the mean of the slopes of all non-side segments
            bottomSlope = abs(sum(sList) / len(sList))
            bottomClass = self.slopeClass(bottomSlope)
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
                self.calculateDistance(
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
