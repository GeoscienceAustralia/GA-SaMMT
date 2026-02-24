"""
Author: Zhi Huang
Organisation: Geoscience Australia
Email: Zhi.Huang@ga.gov.au
Last update: June 04, 2024
Python version: 3+
ArcGIS Pro: 2.6.4 and above """

import math
import os
from datetime import datetime

import arcpy
import numpy as np
import pandas as pd
from arcpy import env
from arcpy.sa import *
from importlib import reload
import HelperFunctions
import AddAttributesFunctions

arcpy.CheckOutExtension("Spatial")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "AddAttributes"

        # List of tool classes associated with this toolbox
        # There are six tools. Three for generating attributes for Bathymetric High features.
        # The other three for Bathymetric Low features.
        # The three tools are used to add three sets of attributes: shape attributes, topographic attributes
        # and profile attributes, in that order.
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

        # fourth parameter, used to hold temporary files
        param3 = arcpy.Parameter(
            displayName="Temporary Folder",
            name="tempFolder",
            datatype="DEFolder",
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
        tempFolder = parameters[3].valueAsText

        # calling the helper functions
        
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)

        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)

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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeatClass, "featID")

        # calculate compactness attribute
        AddAttributesFunctions.calculateCompactness(inFeatClass)
        # calculate circularity, convexity and solidity attributes
        AddAttributesFunctions.calculateCircularity_Convexity_Solidity(workspaceName, inFeatClass)
        # calculate sinuosity, length to width ratio, and other shape attributes
        AddAttributesFunctions.calculateSinuosity_LwR(workspaceName, tempFolder, inFeatClass, inBathy)
        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
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
            parameterType="Required",
            direction="Input",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Output Head Features",
            name="headFeatClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Output Foot Features",
            name="footFeatClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Calculate additional attributes",
            name="additionalOption",
            datatype="GPBoolean",
            parameterType="Required",
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

        # set the output head and foot featureclasses to be at the
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
                        
            parameters[4].value = inFeatClass + "_head"
            parameters[5].value = inFeatClass + "_foot"    

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
        
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)
        headFeatClass = HelperFunctions.convert_backslash_forwardslash(headFeatClass)
        footFeatClass = HelperFunctions.convert_backslash_forwardslash(footFeatClass)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)

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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeatClass, "featID")

        # calculate compactness attribute
        AddAttributesFunctions.calculateCompactness(inFeatClass)
        # calculate circularity, convexity and solidity attributes
        AddAttributesFunctions.calculateCircularity_Convexity_Solidity(workspaceName, inFeatClass)
        # calculate sinuosity, length to width ratio, width to depth ratio, and other shape attributes
        AddAttributesFunctions.calculateSinuosity_LwR_WdR_Slopes(
            workspaceName,
            tempFolder,
            inFeatClass,
            inBathy,
            headFeatClass,
            footFeatClass,
            additionalOption,
        )
        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
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
       
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)
        inSlope = HelperFunctions.convert_backslash_forwardslash(inSlope)

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
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)
        # if the input slope raster is selected from a drop-down list, the inSlope does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inSlope.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inSlope == lyr.name:
                        inSlope = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
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
            HelperFunctions.addIDField(inFeatClass, "featID")

        # add new topographic fields
        for field in fieldList:
            fieldType = "DOUBLE"
            fieldPrecision = 15
            fieldScale = 6
            if field in field_names:
                arcpy.AddMessage(field + " exists")
            else:
                arcpy.management.AddField(
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
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "maxDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MAX" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "depthRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "RANGE" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "meanDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MEAN" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "stdDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "STD" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "minGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MIN" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "maxGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MAX" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "gradientRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "RANGE" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "meanGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MEAN" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "stdGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "STD" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        arcpy.AddMessage("All attributes added")
        # delete intermediate files
        HelperFunctions.deleteDataItems(itemList)
        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
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
            parameterType="Required",
            direction="Input",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Input Foot Features",
            name="footFeatClass",
            datatype="GPFeatureLayer",
            parameterType="Required",
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

        
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)
        inSlope = HelperFunctions.convert_backslash_forwardslash(inSlope)
        headFeatClass = HelperFunctions.convert_backslash_forwardslash(headFeatClass)
        footFeatClass = HelperFunctions.convert_backslash_forwardslash(footFeatClass)

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
        # if the input bathymetry raster is selected from a drop-down list, the inBathy does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inBathy.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inBathy == lyr.name:
                        inBathy = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)
        # if the input slope raster is selected from a drop-down list, the inSlope does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inSlope.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if inSlope == lyr.name:
                        inSlope = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if headFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if headFeatClass == lyr.name:
                        headFeatClass = HelperFunctions.convert_backslash_forwardslash(
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
                        footFeatClass = HelperFunctions.convert_backslash_forwardslash(
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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
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
            HelperFunctions.addIDField(inFeatClass, "featID")

        # check the 'head_foot_length' field exists
        if "head_foot_length" not in field_names:
            messages.addErrorMessage(
                inFeatClass
                + " does not have the head_foot_length attribute. Please use the Add_Shape_Attribute_Tool to"
                + " calculate the attribute."
            )
            raise arcpy.ExecuteError
        # check the depth attributes field exist in the headFeatClass
        fields1 = arcpy.ListFields(headFeatClass)
        field_names1 = [f.name for f in fields1]
        if ("depth" not in field_names1) | ("depth1" not in field_names1):
            messages.addErrorMessage(
                headFeatClass
                + " does not have the required depth attributes."
                + " Please use the Add_Shape_Attribute_Tool to generate the head featureclass"
                + " with the required depth attributes."
            )
            raise arcpy.ExecuteError

        fields2 = arcpy.ListFields(footFeatClass)
        field_names2 = [f.name for f in fields2]
        if ("depth" not in field_names2) | ("depth1" not in field_names2):
            messages.addErrorMessage(
                footFeatClass
                + " does not have the required depth attributes."
                + " Please use the Add_Shape_Attribute_Tool to generate the foot featureclass"
                + " with the required depth attributes."
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
                arcpy.management.AddField(
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
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "maxDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MAX" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "depthRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "RANGE" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "meanDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "MEAN" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "stdDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab1 + "." + "STD" + "!"
        HelperFunctions.addField(inFeatClass, outTab1, field, inID, joinID, expression)

        field = "minGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MIN" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "maxGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MAX" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "gradientRange"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "RANGE" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "meanGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "MEAN" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        field = "stdGradient"
        inID = "featID"
        joinID = "featID"
        expression = "!" + outTab2 + "." + "STD" + "!"
        HelperFunctions.addField(inFeatClass, outTab2, field, inID, joinID, expression)

        # spatial join
        joinFeat1 = "joinFeat1"
        itemList.append(joinFeat1)
        arcpy.analysis.SpatialJoin(inFeatClass, headFeatClass, joinFeat1)

        joinFeat2 = "joinFeat2"
        itemList.append(joinFeat2)
        arcpy.analysis.SpatialJoin(inFeatClass, footFeatClass, joinFeat2)

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
        HelperFunctions.addField(inFeatClass, mergedFeat1, field, inID, joinID, expression)

        field = "footDepth"
        inID = "featID"
        joinID = "featID"
        expression = "!" + mergedFeat2 + "." + "depth" + "!"
        HelperFunctions.addField(inFeatClass, mergedFeat2, field, inID, joinID, expression)

        field = "head_foot_depthRange"
        expression = "!headDepth! - !footDepth!"
        arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")

        field = "head_foot_gradient"
        expression = (
            "math.degrees(math.atan(!head_foot_depthRange! / !head_foot_length!))"
        )
        arcpy.management.CalculateField(inFeatClass, field, expression, "PYTHON3")

        arcpy.AddMessage("All attributes added")

        HelperFunctions.deleteDataItems(itemList)
        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
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
            parameterType="Required",
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

        # the code below turns off theSettingwithCopyWarning related to pandas dataframe processing
        # which would cause arcpy to throw exceptions
        # pd.set_option('mode.chained_assignment',None)

        inFeatClass = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        outFeatClass = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tempFolder = parameters[4].valueAsText

        # calling the helper functions       
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)
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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True
        # areaThreshold input has two components: the threshold value and the area unit
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You can't provide an unknown area unit.")
            raise arcpy.ExecuteError

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeatClass, "featID")

        # check the 'LengthWidthRatio' field exists
        if "LengthWidthRatio" not in field_names:
            messages.addErrorMessage(
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can run."
                + " Please use Add Shape Attribute Tool to calculate the attribute"
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
                arcpy.management.DeleteField(inFeatClass, field)

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
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThresholdValue = converter * float(areaThresholdValue)
        # convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        # generate bounding rectangle
        MbrFeatClass = "bounding_rectangle"
        itemList1.append(MbrFeatClass)
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
        # to catch the failed feature(s)
        failedIDList = []
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
                    AddAttributesFunctions.create_profiles3(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile3.")
                elif (
                    LwR <= 5.0
                ):  # for a feature that is not elongated, create five profiles passing through the polygon centre
                    time1 = datetime.now()
                    AddAttributesFunctions.create_profiles1(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profiles1.")
                else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                    time1 = datetime.now()
                    AddAttributesFunctions.create_profiles2(
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
                    ) = AddAttributesFunctions.calculate_profile_attributes_high(
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
                failedIDList.append(featID)
                continue
            k += 1

        del cursor, row

        # merge all individual features together
        mergedFeat = "mergedFeat"
        arcpy.management.Merge(mergeList, mergedFeat)
        arcpy.AddMessage("merged all done")

        HelperFunctions.deleteDataItems(mergeList)
        HelperFunctions.deleteDataItems(itemList1)
        arcpy.AddMessage("data deletion done")

        # transfer the field values to inFeatClass

        for field in fieldList:
            inID = "featID"
            joinID = "featID"
            expression = "!" + mergedFeat + "." + field + "!"
            HelperFunctions.addTextField(
                inFeatClass, mergedFeat, field, inID, joinID, expression
            )

        arcpy.AddMessage("Profile attributes added and calculated")

        arcpy.management.Delete(mergedFeat)

        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
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
            parameterType="Required",
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

        # the code below turns off theSettingwithCopyWarning related to pandas dataframe processing
        # which would cause arcpy to throw exceptions
        # pd.set_option('mode.chained_assignment',None)

        inFeatClass = parameters[0].valueAsText
        inBathy = parameters[1].valueAsText
        outFeatClass = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tempFolder = parameters[4].valueAsText

        # calling the helper functions        
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)
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

        workspaceName = inFeatClass[0:inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You can't provide an unknown area unit.")
            raise arcpy.ExecuteError

        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]

        # check the 'featID' field exists
        # if not, add and calculate it
        if "featID" not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            HelperFunctions.addIDField(inFeatClass, "featID")

        # check the 'LengthWidthRatio' field exists
        if "LengthWidthRatio" not in field_names:
            messages.addErrorMessage(
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can be run."
                + " Please use Add Shape Attribute Tool to calculate the attribute."
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
                arcpy.management.DeleteField(inFeatClass, field)

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
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThresholdValue = converter * float(areaThresholdValue)
        # convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        # generate bounding rectangle
        MbrFeatClass = "bounding_rectangle"
        itemList1.append(MbrFeatClass)
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
        failedIDList = []
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
                    AddAttributesFunctions.create_profiles3(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile3.")
                elif (
                    LwR <= 5.0
                ):  # for a feature that is not elongated, create five profiles passing through the polygon centre
                    time1 = datetime.now()
                    AddAttributesFunctions.create_profiles1(
                        inFeat, boundFeat, profilePointFC, tempFolder
                    )
                    time2 = datetime.now()
                    diff = time2 - time1
                    arcpy.AddMessage("took " + str(diff) + " to create profile1.")
                else:  # for an elongated polygon feature, create five profiles across the long axis of the polygon
                    time1 = datetime.now()
                    AddAttributesFunctions.create_profiles2(
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
                    ) = AddAttributesFunctions.calculate_profile_attributes_low(
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
                failedIDList.append(featID)
                continue
            k += 1

        del cursor, row
        # merge all individual features together
        mergedFeat = "mergedFeat"
        arcpy.management.Merge(mergeList, mergedFeat)
        arcpy.AddMessage("merged all done")

        HelperFunctions.deleteDataItems(itemList1)
        HelperFunctions.deleteDataItems(mergeList)
        arcpy.AddMessage("data deletion done")

        # transfer the field values to inFeatClass

        for field in fieldList:
            inID = "featID"
            joinID = "featID"
            expression = "!" + mergedFeat + "." + field + "!"
            HelperFunctions.addTextField(
                inFeatClass, mergedFeat, field, inID, joinID, expression
            )

        arcpy.AddMessage("Profile attributes added and calculated")

        arcpy.management.Delete(mergedFeat)

        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        return



   

   
   
    
      
    
