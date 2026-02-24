#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: November 21, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import math
import warnings

import arcpy
from arcpy import env
import numpy as np
from arcpy.sa import *
import os
import sys
import multiprocessing
from importlib import reload
from datetime import datetime
import ContourToolsFunctions
from ContourToolsFunctions import execute_contour_BL
import HelperFunctions


arcpy.CheckOutExtension("Spatial")

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "BathymetricLow"

        # List of tool classes associated with this toolbox
        # There are three tools in this toolset used to map Bathymetric High features.
        self.tools = [TPIToolLow, Openness_Low_Tool, TPI_CI_Low_Tool, ContourBL_Tool, PseudoContourBL_Tool]


# TPIToolLow uses Topographic Position Index (TPI) technique to map Bathymetric Low features
class TPIToolLow:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "TPI Tool Bathymetric Low"
        self.description = "Cacluate TPI and generate an output Featureclass"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output TPI Raster",
            name="tpiRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

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
            displayName="TPI Circle Radius (unit: cell)",
            name="tpiRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 3

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="TPI STD Scale",
            name="tpiSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 1.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
        param6.defaultEnvironmentName = "workspace"

        parameters = [param0, param1, param2, param3, param4, param5, param6]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # set the output TPI raster and output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            bathyRas = parameters[0].valueAsText
            if bathyRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if bathyRas == lyr.name:
                            bathyRas = lyr.dataSource
            parameters[1].value = bathyRas + "_tpi"
            parameters[2].value = bathyRas + "_outFeats"    

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        bathyRas = parameters[0].valueAsText
        tpiRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tpiRadius = parameters[4].valueAsText
        tpiSTDScale = parameters[5].valueAsText
        tempWS = parameters[6].valueAsText
        # enable the helper function
        helper = helpers()
        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        tpiRas = HelperFunctions.convert_backslash_forwardslash(tpiRas)
        outFeat = HelperFunctions.convert_backslash_forwardslash(outFeat)
        tempWS = HelperFunctions.convert_backslash_forwardslash(tempWS)
        # if the input bathyRas is selected from a drop-down list, the bathyRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
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
        # check that the output TPI grid must be in a correct format
        if tpiRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output TPI raster must be nominated as a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The temporary workspace must be nominated as a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0 : bathyRas.rfind("/")]
        workspaceName1 = tpiRas[0 : tpiRas.rfind("/")]
        workspaceName2 = outFeat[0 : outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        # waterproof some unusal errors
        if tpiRas == outFeat:
            messages.addErrorMessage(
                "The output TPI raster and output Featureclass cannot have the same name in the same workspace!"
            )
            raise arcpy.ExecuteError

        if (
            (tempWS == workspaceName)
            or (tempWS == workspaceName1)
            or (tempWS == workspaceName2)
        ):
            messages.addErrorMessage(
                "The temporary workspace must be different from the input/output workspace(s)."
            )
            raise arcpy.ExecuteError

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to calculate TPI and generate output Bathymetric Low features
        helper.TPI_Tool_Low(
            tempWS,
            bathyRas,
            tpiRas,
            outFeat,
            areaThresholdValue,
            areaUnit,
            tpiRadius,
            tpiSTDScale,
        )
        return


# Openness_Low_Tool uses Openness technique to map Bathymetric Low features
class Openness_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Openness Tool Bathymetric Low"
        self.description = (
            "Cacluate Positive Openness and generate an output Featureclass"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Positive Openness Raster",
            name="poRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

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
            displayName="Openness Circle Radius (unit: cell)",
            name="poRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 3

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="PO STD Scale Large",
            name="poSTDScaleLarge",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 2.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="PO STD Scale Small",
            name="poSTDScaleSmall",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = 1.0

        # eighth parameter
        param7 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
        param7.defaultEnvironmentName = "workspace"

        parameters = [param0, param1, param2, param3, param4, param5, param6, param7]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # set the output Openness raster and output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            bathyRas = parameters[0].valueAsText
            if bathyRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if bathyRas == lyr.name:
                            bathyRas = lyr.dataSource
            parameters[1].value = bathyRas + "_po"
            parameters[2].value = bathyRas + "_outFeats" 

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # enable the helper function
        helper = helpers()
        bathyRas = parameters[0].valueAsText
        poRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        poRadius = parameters[4].valueAsText
        poSTDScaleLarge = parameters[5].valueAsText
        poSTDScaleSmall = parameters[6].valueAsText
        tempWS = parameters[7].valueAsText

        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        poRas = HelperFunctions.convert_backslash_forwardslash(poRas)
        outFeat = HelperFunctions.convert_backslash_forwardslash(outFeat)
        tempWS = HelperFunctions.convert_backslash_forwardslash(tempWS)
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
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
        # check that the output TPI grid must be in a correct format
        if poRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output PO raster must be nominated as a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The temporary workspace must be nominated as a File GeoDatabase!"
            )
            raise arcpy.ExecuteError
        workspaceName = bathyRas[0 : bathyRas.rfind("/")]
        workspaceName1 = poRas[0 : poRas.rfind("/")]
        workspaceName2 = outFeat[0 : outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        # waterproof some unusal errors
        if poRas == outFeat:
            messages.addErrorMessage(
                "The output Positive Openness raster and output Featureclass cannot have the same name in the same workspace!"
            )
            raise arcpy.ExecuteError
        if (
            (tempWS == workspaceName)
            or (tempWS == workspaceName1)
            or (tempWS == workspaceName2)
        ):
            messages.addErrorMessage(
                "The temporary workspace must be different from the input/output workspace(s)."
            )
            raise arcpy.ExecuteError

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to calculate openness and generate Bathymetric Low features
        helper.opennessLow(
            tempWS,
            bathyRas,
            poRas,
            outFeat,
            areaThresholdValue,
            areaUnit,
            poRadius,
            poSTDScaleLarge,
            poSTDScaleSmall,
            messages,
        )
        return


# TPI_CI_Low_Tool use TPI and convergence index (CI) techniques to map Bathymetric Low features
class TPI_CI_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "TPI CI Tool Bathymetric Low"
        self.description = "Cacluate TPI, CI and generate an output Featureclass"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output TPI Raster",
            name="tpiRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output CI Raster",
            name="ciRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="TPI Circle Radius (unit: cell)",
            name="tpiRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param5.value = 3

        # seven parameter
        param6 = arcpy.Parameter(
            displayName="TPI STD Scale",
            name="tpiSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = 1.0

        # eight parameter
        param7 = arcpy.Parameter(
            displayName="CI STD Scale",
            name="ciSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param7.value = 1.0

        # nineth parameter
        param8 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
        param8.defaultEnvironmentName = "workspace"

        # tenth parameter
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

        # set the output TPI raster, the output CI raster and output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            bathyRas = parameters[0].valueAsText
            if bathyRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if bathyRas == lyr.name:
                            bathyRas = lyr.dataSource
            parameters[1].value = bathyRas + "_tpi"
            parameters[2].value = bathyRas + "_ci"
            parameters[3].value = bathyRas + "_outFeats" 

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # enable the helper functions
        helper = helpers()
        bathyRas = parameters[0].valueAsText
        tpiRas = parameters[1].valueAsText
        ciRas = parameters[2].valueAsText
        outFeat = parameters[3].valueAsText
        areaThreshold = parameters[4].valueAsText
        tpiRadius = parameters[5].valueAsText
        tpiSTDScale = parameters[6].valueAsText
        ciSTDScale = parameters[7].valueAsText
        tempWS = parameters[8].valueAsText
        tempFolder = parameters[9].valueAsText

        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        tpiRas = HelperFunctions.convert_backslash_forwardslash(tpiRas)
        ciRas = HelperFunctions.convert_backslash_forwardslash(ciRas)
        outFeat = HelperFunctions.convert_backslash_forwardslash(outFeat)
        tempWS = HelperFunctions.convert_backslash_forwardslash(tempWS)
        tempFolder = HelperFunctions.convert_backslash_forwardslash(tempFolder)
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
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
        # check that the output TPI grid must be in a correct format
        if tpiRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output TPI raster must be nominated as a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError
        # check that the output CI grid must be in a correct format
        if ciRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output CI raster must be nominated as a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The temporary workspace must be nominated as a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0 : bathyRas.rfind("/")]
        workspaceName1 = tpiRas[0 : tpiRas.rfind("/")]
        workspaceName2 = ciRas[0 : ciRas.rfind("/")]
        workspaceName3 = outFeat[0 : outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        # waterproof some unusual errors
        if (outFeat == tpiRas) or (outFeat == ciRas):
            messages.addErrorMessage(
                "The output CI and TPI rasters cannot have the same name as the output Featureclass in the same workspace!"
            )
            raise arcpy.ExecuteError
        if (
            (tempWS == workspaceName)
            or (tempWS == workspaceName1)
            or (tempWS == workspaceName2)
            or (tempWS == workspaceName3)
        ):
            messages.addErrorMessage(
                "The temporary workspace must be different from the input/output workspace(s)."
            )
            raise arcpy.ExecuteError

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to calculate TPI and CI, and map Bathymetric Low features
        helper.TPI_CI_Low(
            tempWS,
            bathyRas,
            tpiRas,
            ciRas,
            outFeat,
            areaThresholdValue,
            areaUnit,
            tpiRadius,
            tpiSTDScale,
            ciSTDScale,
            tempFolder,
        )
        return

# This tool is used to map bathymetric low features using the contour-based methods
class ContourBL_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Contour Tool Bathymetric Low"
        self.description = "Use contour method to generate Bathymetric Low features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # 2nd parameter
        param1 = arcpy.Parameter(
            displayName="Output Contour Featureclass",
            name="outContour",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Output Bathymetric Low Featureclass",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Shallowest Contour Depth",
            name="sDepth",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Deepest Contour Depth",
            name="dDepth",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Contour interval",
            name="cInterval",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="Depth Difference",
            name="depthFactor",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Depth Difference Calculation Method",
            name="depthMethod",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param7.filter.type = "ValueList"
        param7.filter.list = ['As Percentage of the Contour Value (%)', 'As Absolute Depth Value (m)']
        param7.value = 'As Absolute Depth Value (m)'

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # 10th parameter
        param9 = arcpy.Parameter(
            displayName="Mapping Method",
            name="method",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param9.filter.type = "ValueList"
        param9.filter.list = ['First Derivative', 'Second Derivative']

        parameters = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # set the output contour featureclass and output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            bathyRas = parameters[0].valueAsText
            if bathyRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if bathyRas == lyr.name:
                            bathyRas = lyr.dataSource
            parameters[1].value = bathyRas + "_contour"
            parameters[2].value = bathyRas + "_outFeats"   

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        bathyRas = parameters[0].valueAsText
        outContour = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        sDepth = parameters[3].valueAsText
        dDepth = parameters[4].valueAsText
        cInterval = parameters[5].valueAsText
        depthFactor = float(parameters[6].valueAsText)
        depthMethod = parameters[7].valueAsText
        areaThreshold = parameters[8].valueAsText
        method = parameters[9].valueAsText
        # enable helper function
        helper = helpers()

        if len(str(float(sDepth)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The shallowest contour depth value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(sDepth) > 0:
            messages.addErrorMessage(
                "The shallowest contour depth value must be negative!"
            )
            raise arcpy.ExecuteError

        if len(str(float(dDepth)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The deepest contour depth value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(dDepth) > 0:
            messages.addErrorMessage(
                "The deepest contour depth value must be negative!"
            )
            raise arcpy.ExecuteError

        if len(str(float(cInterval)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The contour interval value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(cInterval) <= 0:
            messages.addErrorMessage(
                "The contour interval value must be greater than 0!"
            )
            raise arcpy.ExecuteError

        if float(dDepth) >= float(sDepth):
            messages.addErrorMessage(
                "The deepest contour depth value must be smaller than the shallowest contour depth value!"
            )
            raise arcpy.ExecuteError

        if round((float(dDepth) - float(sDepth)) % float(cInterval), 5) != 0:
            messages.addErrorMessage(
                "The difference between the deepest and the shallowest contour depths must be divisible to "
                + "the contour interval!"
            )
            raise arcpy.ExecuteError

        if depthFactor < 0:
            messages.addErrorMessage(
                "The depth difference factor must be greater than 0! "
            )
            raise arcpy.ExecuteError

        # if the input bathymetry raster is selected from a drop-down list, the bathyRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
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

        # check that the output featureclass must be in a correct format
        if outContour.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output Contour featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output Bathymetric High featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0: bathyRas.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        sDepth = float(sDepth)
        dDepth = float(dDepth)
        cInterval = float(cInterval)

        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThresholdValue = converter * float(areaThresholdValue)
        # convert to "square meters"
        areaThresholdValue = areaThresholdValue * 1000000

        depth = sDepth
        mergeList = []
        time1 = datetime.now()
        Contour(bathyRas, outContour, cInterval, sDepth)
        arcpy.AddMessage("contours are generated")
        # Add a new field to the contour features
        # The contour field have many decimal place. This would potentially cause issue when selecting contours due to
        # the rounding issue.
        # The contour1 field will only have one decimal place. Thus, the rounding issue has been avoided.
        fieldType = "DOUBLE"
        fieldPrecision = 15
        fieldScale = 6
        fieldName = "contour1"
        arcpy.management.AddField(outContour, fieldName, fieldType, fieldPrecision, fieldScale)
        # rounding float number to one decimal place
        codeblock = """
def roundNumber(a):
    b = round(a,1)
    return b
                    """
        expression = "roundNumber(!contour!)"
        arcpy.management.CalculateField(
            outContour, fieldName, expression, "PYTHON3", codeblock
        )
        itemList = []
        # loop though each contour value
        while depth >= dDepth:
            arcpy.AddMessage("processing contour " + str(depth))
            # select contours at a depth
            # has to use the contour1 field to avoid the rounding issue
            whereClause = "contour1 = " + str(depth)
            arcpy.AddMessage(whereClause)
            tempString = str(abs(depth)) + "m"
            tempString = tempString.replace('.', 'p')
            contourFeat = outContour + "_" + tempString
            itemList.append(contourFeat)
            arcpy.analysis.Select(outContour, contourFeat, whereClause)
            # convert these contours to polygons
            contourPoly = contourFeat + "_poly"
            itemList.append(contourPoly)
            arcpy.management.FeatureToPolygon(contourFeat, contourPoly)
            nuFeats = int(arcpy.management.GetCount(contourPoly)[0])
            if nuFeats > 0:
                # select only those contour polygons with their areas greater than a threshold
                whereClause = "Shape_Area >= " + str(areaThresholdValue)
                selectedFeat = contourPoly + "_selected"
                itemList.append(selectedFeat)
                arcpy.analysis.Select(contourPoly, selectedFeat, whereClause)
                nuFeats = int(arcpy.management.GetCount(selectedFeat)[0])
                if nuFeats > 0:
                    # eliminate all holes in the selected contour polygons
                    eliminatedFeat = selectedFeat + "1"
                    itemList.append(eliminatedFeat)
                    arcpy.management.EliminatePolygonPart(selectedFeat, eliminatedFeat, "AREA",
                                                          "1000 SquareKilometers", "", "CONTAINED_ONLY")
                    # eliminate a hole feature within a larger feature
                    overlapFeat = "temp1"
                    arcpy.analysis.CountOverlappingFeatures(eliminatedFeat, overlapFeat, 2)
                    nuFeats = int(arcpy.management.GetCount(overlapFeat)[0])
                    while nuFeats > 0:
                        layer1 = arcpy.management.SelectLayerByLocation(eliminatedFeat, "ARE_IDENTICAL_TO", overlapFeat)
                        arcpy.management.DeleteFeatures(layer1)
                        arcpy.analysis.CountOverlappingFeatures(eliminatedFeat, overlapFeat, 2)
                        nuFeats = int(arcpy.management.GetCount(overlapFeat)[0])
                    arcpy.management.Delete(overlapFeat)
                    arcpy.AddMessage("selected1 done")
                    # add and calculate a contour field
                    fieldType = "DOUBLE"
                    fieldPrecision = 15
                    fieldScale = 6
                    fieldName = "contour"
                    arcpy.management.AddField(eliminatedFeat, fieldName, fieldType, fieldPrecision, fieldScale)
                    expression = str(depth)
                    arcpy.management.CalculateField(eliminatedFeat, fieldName, expression)
                    # dissolve to obtain updated boundaries
                    dissolvedFeat = selectedFeat + "2"
                    itemList.append(dissolvedFeat)
                    arcpy.management.Dissolve(eliminatedFeat, dissolvedFeat, fieldName, "", "SINGLE_PART")
                    arcpy.AddMessage("selected2 done")
                    # calculate mean depth for each polygon
                    outTab = "outTab"
                    outZSat = ZonalStatisticsAsTable(dissolvedFeat, "OBJECTID", bathyRas, outTab, "DATA", "MEAN")

                    field = "mean_depth"
                    inID = "OBJECTID"
                    joinID = "OBJECTID_1"
                    expression = "!" + outTab + "." + "MEAN" + "!"
                    HelperFunctions.addField(dissolvedFeat, outTab, field, inID, joinID, expression)
                    arcpy.management.Delete(outTab)
                    # delete feature(s) with null mean_depth
                    tempLayer = "tempLayer"
                    whereClause = '"mean_depth" is NULL'
                    arcpy.management.MakeFeatureLayer(dissolvedFeat, tempLayer)
                    arcpy.management.SelectLayerByAttribute(tempLayer, "NEW_SELECTION", whereClause)
                    if int(arcpy.management.GetCount(tempLayer)[0]) > 0:
                        arcpy.management.DeleteFeatures(tempLayer)
                    arcpy.management.Delete(tempLayer)
                    # for each polygon, calculate the depth difference between its mean depth and the contour
                    fieldType = "DOUBLE"
                    fieldPrecision = 15
                    fieldScale = 6
                    fields = arcpy.ListFields(dissolvedFeat)
                    field_names = [f.name for f in fields]
                    fieldName = "depth_diff"
                    if fieldName in field_names:
                        arcpy.AddMessage(fieldName + " exists and will be recalculated")
                    else:
                        arcpy.management.AddField(
                            dissolvedFeat, fieldName, fieldType, fieldPrecision, fieldScale
                        )

                    expression = (
                            "!"
                            + "mean_depth"
                            + "!"
                            + "-"
                            + "!"
                            + "contour"
                            + "!"
                    )
                    arcpy.management.CalculateField(
                        dissolvedFeat, fieldName, expression, "PYTHON3"
                    )
                    # further select only those features that have negative depth difference smaller than a negative
                    # threshold
                    # These selected features are thus bathymetric low features
                    # depthFactor = 0.07
                    if depthMethod == 'As Percentage of the Contour Value (%)':
                        depthThreshold = abs(depthFactor / 100 * depth) * -1.0
                    else:
                        depthThreshold = depthFactor * -1.0
                    whereClause = "depth_diff < " + str(depthThreshold)
                    arcpy.AddMessage("depth_diff " + str(depthThreshold))
                    selectedFeat = selectedFeat + "3"
                    itemList.append(selectedFeat)
                    arcpy.analysis.Select(dissolvedFeat, selectedFeat, whereClause)
                    arcpy.AddMessage("selected3 done")
                    mergeList.append(selectedFeat)

            depth = depth - cInterval

        # merge selected features for all contour values (e.g., -40m to -150m),
        # in the descending order (from -40m to -150m)
        outFeat1 = "contours_merged_BL"
        arcpy.management.Merge(mergeList, outFeat1)
        arcpy.AddMessage("merge done")
        # add a temporary field for dissolve action
        fieldName = "temp"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 2)
        expression = "1"
        arcpy.management.CalculateField(outFeat1, fieldName, expression)
        # dissolve to obtain updated boundaries
        # this results in the out most boundary (e.g., the deepest contour) for each selected bathymetric high feature
        outFeat2 = outFeat1 + "_dissolved"
        arcpy.management.Dissolve(outFeat1, outFeat2, fieldName, "", "SINGLE_PART")
        arcpy.AddMessage("dissolve done")
        # spatial join to get attributes from outFeat1
        outFeat3 = outFeat2 + "_joined"
        arcpy.analysis.SpatialJoin(outFeat2, outFeat1, outFeat3, "JOIN_ONE_TO_MANY", "KEEP_ALL", "#", "CONTAINS")
        arcpy.AddMessage("spatial join done")
        # get a statistics for the relationship between each dissolved feature and merged feature(s)
        # each dissolved feature is associated with one to several merged features
        sumTab = "sumTable"
        caseField = "TARGET_FID"
        statField = [["JOIN_FID", "First"]]
        arcpy.analysis.Statistics(outFeat3, sumTab, statField, caseField)
        arcpy.AddMessage("summary statistic done")
        # select those records that indicate that there are one or two merged features being associated with a dissolved
        # feature
        view1 = "view1"
        arcpy.management.MakeTableView(sumTab, view1)
        whereClause = '"FREQUENCY" < 3'
        sumTab1 = "sumTable1"
        arcpy.management.SelectLayerByAttribute(view1, 'NEW_SELECTION', whereClause)
        arcpy.management.CopyRows(view1, sumTab1)
        # select those records that indicate that there are more than two merged features being associated
        # with a dissolved feature
        whereClause = '"FREQUENCY" > 2'
        sumTab2 = "sumTable2"
        arcpy.management.SelectLayerByAttribute(view1, 'NEW_SELECTION', whereClause)
        arcpy.management.CopyRows(view1, sumTab2)
        arcpy.management.Delete(view1)
        # first selection
        # If a dissolved feature has only one associated merged feature, select the merged feature
        # if a dissolved features has two associated merged features (e.g., -50m, -60m), select the merged feature with
        # a shallower contour (-50m in this case, represented by the FIRST_JOIN_FID).
        fieldName = "idV"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 10)
        layer1 = "layer1"
        arcpy.management.MakeFeatureLayer(outFeat1, layer1)
        arcpy.management.AddJoin(layer1, "OBJECTID", sumTab1, "FIRST_JOIN_FID")
        expression = "!sumTable1.FIRST_JOIN_FID!"
        arcpy.management.CalculateField(layer1, fieldName, expression)
        arcpy.management.RemoveJoin(layer1)
        arcpy.management.Delete(layer1)

        outFeat1_Selected1 = outFeat1 + "_selected1"
        whereClause = fieldName + ' > 0'
        arcpy.analysis.Select(outFeat1, outFeat1_Selected1, whereClause)
        arcpy.AddMessage("first selection done")

        arcpy.AddMessage("starting second section ...")
        arcpy.AddMessage("This could take a while, be patient")
        # second selection
        # If a dissolved feature has more than two associated merged features, we need to select the merged features
        # using the following process

        arcpy.management.AddField(outFeat2, fieldName, "LONG", 10)
        layer2 = "layer2"
        arcpy.management.MakeFeatureLayer(outFeat2, layer2)
        arcpy.management.AddJoin(layer2, "OBJECTID", sumTab2, "TARGET_FID")
        expression = "!sumTable2.TARGET_FID!"
        arcpy.management.CalculateField(layer2, fieldName, expression)
        arcpy.management.RemoveJoin(layer2)
        arcpy.management.Delete(layer2)
        arcpy.management.Delete(sumTab)
        arcpy.management.Delete(sumTab1)
        arcpy.management.Delete(sumTab2)

        # select the dissolved features that have more than two associated merged features
        outFeat2_Selected = outFeat2 + "_selected"
        arcpy.analysis.Select(outFeat2, outFeat2_Selected, whereClause)
        # get the feature count of outFeat2_Selected
        nuFeats = int(arcpy.management.GetCount(outFeat2_Selected)[0])
        arcpy.AddMessage("They are " + str(nuFeats) + " features for multiprocessing.")
        # set the maximum number of CPUs for the multiprocessing job equals to half of those available
        maxCPU = int(multiprocessing.cpu_count() / 2)
        if nuFeats > 0:
            # determine how many CPUs to use depending on the feature count of outFeat2_Selected
            if nuFeats % 5 > 0:
                x = int(nuFeats / 5) + 1
            else:
                x = int(nuFeats / 5)
            if x > maxCPU:
                nCPU = maxCPU
            else:
                nCPU = x

            # the name of the second selection
            outFeat1_Selected2 = outFeat1 + "_selected2"

            # now let us call the multiprocessing model to speed up the second selection process

            arcpy.AddMessage("Using " + str(nCPU) + " CPU processors for multiprocessing")
            workspaceName = env.workspace

            workspaceList, tempfolderList, outFeat2List, mergeFeatList, joinFeatList, outFeat1List = HelperFunctions.splitFeat(
                workspaceName,
                outFeat2_Selected,
                outFeat1,
                outFeat3,
                outFeat1_Selected2,
                nCPU)

            argList = []
            i = 0
            while i < len(workspaceList):
                argList.append(
                    [workspaceList[i], mergeFeatList[i], outFeat2List[i], joinFeatList[i], tempfolderList[i],
                     outFeat1List[i]])
                i += 1

            arcpy.AddMessage(argList)

            # important, need to set the python.exe within ArcGIS Pro as the python set_executable
            # this will make sure the multiprocessing opens multiple python windows for processing
            # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
            # which would not process the task as expected.
            arcpy.AddMessage(os.path.join(sys.exec_prefix, 'python.exe'))
            multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
            # important, need to reload the module so that we use the most up-to-date coding in the module
            reload(ContourToolsFunctions)

            arcpy.AddMessage('Starting multiprocessing...')
            # call the execute_contour_BL() from the ContourToolsFunctions module
            # the function is the entry point for the multiprocessing
            if method == 'First Derivative':
                arcpy.AddMessage("Using the First Derivative method!")
            else:
                arcpy.AddMessage("Using the Second Derivative method!")
            execute_contour_BL(argList, method, nCPU)
            arcpy.AddMessage('multiprocessing Done.')

            # merge the individual outputs from the multiprocessing as the second selection
            arcpy.management.Merge(outFeat1List, outFeat1_Selected2)
            # merge the first selection and second selection as the final selection from the merged features

            arcpy.management.Merge([outFeat1_Selected1, outFeat1_Selected2], outFeat)
            arcpy.AddMessage("final merged done")

            # delete all temporary workspaces and folders
            for workspace in workspaceList:
                arcpy.management.Delete(workspace)
            arcpy.AddMessage("All temporary workspaces are deleted")

            for folder in tempfolderList:
                arcpy.management.Delete(folder)
            arcpy.AddMessage("All temporary folders are deleted")
        else:  # no feature in the second selection, just copy the first selection
            arcpy.management.Copy(outFeat1_Selected1, outFeat)

        # delete intermediate datasets
        HelperFunctions.deleteDataItems(itemList)

        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to finish.")

        return


# This tool is used to map bathymetric low features using the pseudo contour-based methods
class PseudoContourBL_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pseudo Contour Tool Bathymetric Low"
        self.description = "Use pseudo contour method to generate Bathymetric Low features"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Bathymetric Low Featureclass",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Shallowest Contour Depth",
            name="sDepth",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Deepest Contour Depth",
            name="dDepth",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Contour interval",
            name="cInterval",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Depth Difference",
            name="depthFactor",
            datatype="GPDouble",
            parameterType="Required",
            direction="Input",
        )

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Depth Difference Calculation Method",
            name="depthMethod",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param6.filter.type = "ValueList"
        param6.filter.list = ['As Percentage of the Contour Value (%)', 'As Absolute Depth Value (m)']
        param6.value = 'As Absolute Depth Value (m)'

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Minimum Area Threshold",
            name="minAreaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Maximum Area Threshold",
            name="maxAreaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # 10th parameter
        param9 = arcpy.Parameter(
            displayName="Mapping Method",
            name="method",
            datatype="GPString",
            parameterType="Required",
            direction="Input",
        )
        param9.filter.type = "ValueList"
        param9.filter.list = ['First Derivative', 'Second Derivative']

        parameters = [param0, param1, param2, param3, param4, param5, param6, param7, param8, param9]
        return parameters

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""

        # set the output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            bathyRas = parameters[0].valueAsText
            if bathyRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if bathyRas == lyr.name:
                            bathyRas = lyr.dataSource
            parameters[1].value = bathyRas + "_outFeats"
            
        # to provide a default value for the maximum area threshold parameter
        if parameters[8].value:  # if the maximum area threshold parameter has an existing value, do nothing
            return
        else:
            if parameters[0].value:
                bathyRas = parameters[0].valueAsText
                helper = helpers()
                # if the input bathymetry raster is selected from a drop-down list, the bathyRas does not contain the
                # full path
                # In this case, the full path needs to be obtained from the map layer
                if bathyRas.rfind("/") < 0:
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    m = aprx.activeMap
                    for lyr in m.listLayers():
                        if lyr.isRasterLayer:
                            if bathyRas == lyr.name:
                                bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

                minResult = arcpy.management.GetRasterProperties(bathyRas, "MINIMUM")
                minValue = minResult.getOutput(0)
                if minValue.find(",") > 0:
                    minValue = HelperFunctions.convertDecimalSeparator(minValue)
                outCon = Con(Raster(bathyRas) >= float(minValue), 1)
                tempTab = "tempTable"
                zonStat = ZonalStatisticsAsTable(outCon, "VALUE", outCon,
                                                 tempTab, "NODATA", "SUM")
                cursor = arcpy.SearchCursor(tempTab)
                row = cursor.next()
                area = row.getValue("AREA")
                # the default maximum area threshold is one-third of the total area, using SquareKilometers as unit
                area = int(round(area / 1000000 / 3, 0))
                arcpy.management.Delete(outCon)
                arcpy.management.Delete(tempTab)
                areaThreshold = str(area) + " SquareKilometers"
                parameters[8].value = areaThreshold

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        bathyRas = parameters[0].valueAsText
        outFeat = parameters[1].valueAsText
        sDepth = parameters[2].valueAsText
        dDepth = parameters[3].valueAsText
        cInterval = parameters[4].valueAsText
        depthFactor = float(parameters[5].valueAsText)
        depthMethod = parameters[6].valueAsText
        minAreaThreshold = parameters[7].valueAsText
        maxAreaThreshold = parameters[8].valueAsText
        method = parameters[9].valueAsText
        # enable helper function
        helper = helpers()

        if len(str(float(sDepth)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The shallowest contour depth value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(sDepth) > 0:
            messages.addErrorMessage(
                "The shallowest contour depth value must be negative!"
            )
            raise arcpy.ExecuteError

        if len(str(float(dDepth)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The deepest contour depth value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(dDepth) > 0:
            messages.addErrorMessage(
                "The deepest contour depth value must be negative!"
            )
            raise arcpy.ExecuteError

        if len(str(float(cInterval)).split('.')[1]) > 1:
            messages.addErrorMessage(
                "The contour interval value can only have up to one decimal place!"
            )
            raise arcpy.ExecuteError
        if float(cInterval) <= 0:
            messages.addErrorMessage(
                "The contour interval value must be greater than 0!"
            )
            raise arcpy.ExecuteError

        if float(dDepth) >= float(sDepth):
            messages.addErrorMessage(
                "The deepest contour depth value must be smaller than the shallowest contour depth value!"
            )
            raise arcpy.ExecuteError

        if ((float(dDepth) - float(sDepth)) % float(cInterval)) != 0:
            messages.addErrorMessage(
                "The difference between the deepest and the shallowest contour depths must be divisible to "
                + "the contour interval!"
            )
            raise arcpy.ExecuteError

        if depthFactor < 0:
            messages.addErrorMessage(
                "The depth difference factor must be greater than 0! "
            )
            raise arcpy.ExecuteError

        # if the input bathymetry raster is selected from a drop-down list, the bathyRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
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

        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output Bathymetric High featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0: bathyRas.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

        sDepth = float(sDepth)
        dDepth = float(dDepth)
        cInterval = float(cInterval)

        minAreaThresholdValue = minAreaThreshold.split(" ")[0]
        areaUnit = minAreaThreshold.split(" ")[1]
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        minAreaThresholdValue = converter * float(minAreaThresholdValue)
        # convert to "square meters"
        minAreaThresholdValue = minAreaThresholdValue * 1000000

        maxAreaThresholdValue = maxAreaThreshold.split(" ")[0]
        areaUnit = maxAreaThreshold.split(" ")[1]
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        maxAreaThresholdValue = converter * float(maxAreaThresholdValue)
        # convert to "square meters"
        maxAreaThresholdValue = maxAreaThresholdValue * 1000000

        depth = sDepth
        mergeList = []
        time1 = datetime.now()
        itemList = []
        # loop though each contour value
        while depth >= dDepth:
            arcpy.AddMessage("processing pseudo contour " + str(depth))
            # create  pseudo contours at a depth using the Raster Con function
            # the contours are in polygon format
            # Note that the contours created in this way are slightly different from using the Vector Contour function.
            # For example, they follow the edges (instead of the centres) of the cells
            # One important difference is that this approach will create pseudo contours for partial features
            # cut off by the boundary.
            tempString = str(abs(depth)) + "m"
            tempString = tempString.replace('.', 'p')
            contourPoly = "outContour_" + tempString + "_poly"
            itemList.append(contourPoly)
            outCon = Con(Raster(bathyRas) <= depth, 1)
            arcpy.conversion.RasterToPolygon(outCon, contourPoly, "NO_SIMPLIFY", "VALUE")
            arcpy.management.Delete(outCon)

            nuFeats = int(arcpy.management.GetCount(contourPoly)[0])
            if nuFeats > 0:
                # select only those contour polygons within the minimum and maximum area thresholds
                whereClause = (
                        "(Shape_Area >= "
                        + str(minAreaThresholdValue)
                        + ") And (Shape_Area <= "
                        + str(maxAreaThresholdValue)
                        + ")"
                )

                selectedFeat = contourPoly + "_selected"
                itemList.append(selectedFeat)
                arcpy.analysis.Select(contourPoly, selectedFeat, whereClause)
                nuFeats = int(arcpy.management.GetCount(selectedFeat)[0])
                if nuFeats > 0:
                    # eliminate all holes in the selected contour polygons
                    eliminatedFeat = selectedFeat + "1"
                    itemList.append(eliminatedFeat)
                    arcpy.management.EliminatePolygonPart(selectedFeat, eliminatedFeat, "AREA",
                                                          "1000 SquareKilometers", "", "CONTAINED_ONLY")
                    # eliminate a hole feature within a larger feature
                    overlapFeat = "temp1"
                    arcpy.analysis.CountOverlappingFeatures(eliminatedFeat, overlapFeat, 2)
                    nuFeats = int(arcpy.management.GetCount(overlapFeat)[0])
                    while nuFeats > 0:
                        layer1 = arcpy.management.SelectLayerByLocation(eliminatedFeat, "ARE_IDENTICAL_TO", overlapFeat)
                        arcpy.management.DeleteFeatures(layer1)
                        arcpy.analysis.CountOverlappingFeatures(eliminatedFeat, overlapFeat, 2)
                        nuFeats = int(arcpy.management.GetCount(overlapFeat)[0])
                    arcpy.management.Delete(overlapFeat)
                    arcpy.AddMessage("selected1 done")
                    # add and calculate a contour field
                    fieldType = "DOUBLE"
                    fieldPrecision = 15
                    fieldScale = 6
                    fieldName = "contour"
                    arcpy.management.AddField(eliminatedFeat, fieldName, fieldType, fieldPrecision, fieldScale)
                    expression = str(depth)
                    arcpy.management.CalculateField(eliminatedFeat, fieldName, expression)
                    # dissolve to obtain updated boundaries
                    dissolvedFeat = selectedFeat + "2"
                    itemList.append(dissolvedFeat)
                    arcpy.management.Dissolve(eliminatedFeat, dissolvedFeat, fieldName, "", "SINGLE_PART")
                    arcpy.AddMessage("selected2 done")
                    # calculate mean depth for each polygon
                    outTab = "outTab"
                    outZSat = ZonalStatisticsAsTable(dissolvedFeat, "OBJECTID", bathyRas, outTab, "DATA", "MEAN")
                    field = "mean_depth"
                    inID = "OBJECTID"
                    joinID = "OBJECTID_1"
                    expression = "!" + outTab + "." + "MEAN" + "!"
                    HelperFunctions.addField(dissolvedFeat, outTab, field, inID, joinID, expression)
                    arcpy.management.Delete(outTab)
                    # delete feature(s) with null mean_depth
                    tempLayer = "tempLayer"
                    expression = '"mean_depth" is NULL'
                    arcpy.management.MakeFeatureLayer(dissolvedFeat, tempLayer)
                    arcpy.management.SelectLayerByAttribute(tempLayer, "NEW_SELECTION",
                                                            expression)
                    if int(arcpy.management.GetCount(tempLayer)[0]) > 0:
                        arcpy.management.DeleteFeatures(tempLayer)
                    arcpy.management.Delete(tempLayer)

                    # for each polygon, calculate the depth difference between its mean depth and the contour
                    fieldType = "DOUBLE"
                    fieldPrecision = 15
                    fieldScale = 6
                    fields = arcpy.ListFields(dissolvedFeat)
                    field_names = [f.name for f in fields]
                    fieldName = "depth_diff"
                    if fieldName in field_names:
                        arcpy.AddMessage(fieldName + " exists and will be recalculated")
                    else:
                        arcpy.management.AddField(
                            dissolvedFeat, fieldName, fieldType, fieldPrecision, fieldScale
                        )

                    expression = (
                            "!"
                            + "mean_depth"
                            + "!"
                            + "-"
                            + "!"
                            + "contour"
                            + "!"
                    )
                    arcpy.management.CalculateField(
                        dissolvedFeat, fieldName, expression, "PYTHON3"
                    )
                    # further select only those features that have negative depth difference smaller than a negative
                    # threshold
                    # These selected features are thus bathymetric high features
                    # depthFactor = 0.07
                    if depthMethod == 'As Percentage of the Contour Value (%)':
                        depthThreshold = abs(depthFactor / 100 * depth) * -1.0
                    else:
                        depthThreshold = depthFactor * -1.0
                    whereClause = "depth_diff < " + str(depthThreshold)
                    arcpy.AddMessage("depth_diff " + str(depthThreshold))
                    selectedFeat = selectedFeat + "3"
                    itemList.append(selectedFeat)
                    arcpy.analysis.Select(dissolvedFeat, selectedFeat, whereClause)
                    arcpy.AddMessage("selected3 done")
                    mergeList.append(selectedFeat)

            depth = depth - cInterval

        # merge selected features for all contour values (e.g., -40m to -150m),
        # in the descending order (from -40m to -150m)
        outFeat1 = "contours_merged_BL_pseudo"
        arcpy.management.Merge(mergeList, outFeat1)
        arcpy.AddMessage("merge done")
        # add a temporary field for dissolve action
        fieldName = "temp"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 2)
        expression = "1"
        arcpy.management.CalculateField(outFeat1, fieldName, expression)
        # dissolve to obtain updated boundaries
        # this results in the out most boundary (e.g., the deepest contour) for each selected bathymetric high feature
        outFeat2 = outFeat1 + "_dissolved"
        arcpy.management.Dissolve(outFeat1, outFeat2, fieldName, "", "SINGLE_PART")
        arcpy.AddMessage("dissolve done")
        # spatial join to get attributes from outFeat1
        outFeat3 = outFeat2 + "_joined"
        arcpy.analysis.SpatialJoin(outFeat2, outFeat1, outFeat3, "JOIN_ONE_TO_MANY", "KEEP_ALL", "#", "CONTAINS")
        arcpy.AddMessage("spatial join done")
        # get a statistics for the relationship between each dissolved feature and merged feature(s)
        # each dissolved feature is associated with one to several merged features
        sumTab = "sumTable"
        caseField = "TARGET_FID"
        statField = [["JOIN_FID", "First"]]
        arcpy.analysis.Statistics(outFeat3, sumTab, statField, caseField)
        arcpy.AddMessage("summary statistic done")
        # select those records that indicate that there are one or two merged features being associated with a dissolved
        # feature
        view1 = "view1"
        arcpy.management.MakeTableView(sumTab, view1)
        whereClause = '"FREQUENCY" < 3'
        sumTab1 = "sumTable1"
        arcpy.management.SelectLayerByAttribute(view1, 'NEW_SELECTION', whereClause)
        arcpy.management.CopyRows(view1, sumTab1)
        # select those records that indicate that there are more than two merged features being associated
        # with a dissolved feature
        whereClause = '"FREQUENCY" > 2'
        sumTab2 = "sumTable2"
        arcpy.management.SelectLayerByAttribute(view1, 'NEW_SELECTION', whereClause)
        arcpy.management.CopyRows(view1, sumTab2)
        arcpy.management.Delete(view1)
        # first selection
        # If a dissolved feature has only one associated merged feature, select the merged feature
        # if a dissolved features has two associated merged features (e.g., -50m, -60m), select the merged feature with
        # a shallower contour (-50m in this case, represented by the FIRST_JOIN_FID).
        fieldName = "idV"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 10)
        layer1 = "layer1"
        arcpy.management.MakeFeatureLayer(outFeat1, layer1)
        arcpy.management.AddJoin(layer1, "OBJECTID", sumTab1, "FIRST_JOIN_FID")
        expression = "!sumTable1.FIRST_JOIN_FID!"
        arcpy.management.CalculateField(layer1, fieldName, expression)
        arcpy.management.RemoveJoin(layer1)
        arcpy.management.Delete(layer1)

        outFeat1_Selected1 = outFeat1 + "_selected1"
        whereClause = fieldName + ' > 0'
        arcpy.analysis.Select(outFeat1, outFeat1_Selected1, whereClause)
        arcpy.AddMessage("first selection done")

        arcpy.AddMessage("starting second section ...")
        arcpy.AddMessage("This could take a while, be patient")
        # second selection
        # If a dissolved feature has more than two associated merged features, we need to select the merged features
        # using the following process

        arcpy.management.AddField(outFeat2, fieldName, "LONG", 10)
        layer2 = "layer2"
        arcpy.management.MakeFeatureLayer(outFeat2, layer2)
        arcpy.management.AddJoin(layer2, "OBJECTID", sumTab2, "TARGET_FID")
        expression = "!sumTable2.TARGET_FID!"
        arcpy.management.CalculateField(layer2, fieldName, expression)
        arcpy.management.RemoveJoin(layer2)
        arcpy.management.Delete(layer2)
        arcpy.management.Delete(sumTab)
        arcpy.management.Delete(sumTab1)
        arcpy.management.Delete(sumTab2)

        # select the dissolved features that have more than two associated merged features
        outFeat2_Selected = outFeat2 + "_selected"
        arcpy.analysis.Select(outFeat2, outFeat2_Selected, whereClause)
        # get the feature count of outFeat2_Selected
        nuFeats = int(arcpy.management.GetCount(outFeat2_Selected)[0])
        arcpy.AddMessage("They are " + str(nuFeats) + " features for multiprocessing.")
        # set the maximum number of CPUs for the multiprocessing job equals to half of those available
        maxCPU = int(multiprocessing.cpu_count() / 2)
        if nuFeats > 0:
            # determine how many CPUs to use depending on the feature count of outFeat2_Selected
            if nuFeats % 5 > 0:
                x = int(nuFeats / 5) + 1
            else:
                x = int(nuFeats / 5)
            if x > maxCPU:
                nCPU = maxCPU
            else:
                nCPU = x

            # the name of the second selection
            outFeat1_Selected2 = outFeat1 + "_selected2"

            # now let us call the multiprocessing model to speed up the second selection process

            arcpy.AddMessage("Using " + str(nCPU) + " CPU processors for multiprocessing")
            workspaceName = env.workspace

            workspaceList, tempfolderList, outFeat2List, mergeFeatList, joinFeatList, outFeat1List = HelperFunctions.splitFeat(
                workspaceName,
                outFeat2_Selected,
                outFeat1,
                outFeat3,
                outFeat1_Selected2,
                nCPU)

            argList = []
            i = 0
            while i < len(workspaceList):
                argList.append(
                    [workspaceList[i], mergeFeatList[i], outFeat2List[i], joinFeatList[i], tempfolderList[i],
                     outFeat1List[i]])
                i += 1

            arcpy.AddMessage(argList)

            # important, need to set the python.exe within ArcGIS Pro as the python set_executable
            # this will make sure the multiprocessing opens multiple python windows for processing
            # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
            # which would not process the task as expected.
            arcpy.AddMessage(os.path.join(sys.exec_prefix, 'python.exe'))
            multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
            # important, need to reload the module so that we use the most up-to-date coding in the module
            reload(ContourToolsFunctions)

            arcpy.AddMessage('Starting multiprocessing...')
            # call the execute_contour_BL() from the ContourToolsFunctions module
            # the function is the entry point for the multiprocessing
            if method == 'First Derivative':
                arcpy.AddMessage("Using the First Derivative method!")
            else:
                arcpy.AddMessage("Using the Second Derivative method!")
            execute_contour_BL(argList, method, nCPU)
            arcpy.AddMessage('multiprocessing Done.')

            # merge the individual outputs from the multiprocessing as the second selection
            arcpy.management.Merge(outFeat1List, outFeat1_Selected2)
            # merge the first selection and second selection as the final selection from the merged features

            arcpy.management.Merge([outFeat1_Selected1, outFeat1_Selected2], outFeat)
            arcpy.AddMessage("final merged done")

            # delete all temporary workspaces and folders
            for workspace in workspaceList:
                arcpy.management.Delete(workspace)
            arcpy.AddMessage("All temporary workspaces are deleted")

            for folder in tempfolderList:
                arcpy.management.Delete(folder)
            arcpy.AddMessage("All temporary folders are deleted")
        else:  # no feature in the second selection, just copy the first selection
            arcpy.management.Copy(outFeat1_Selected1, outFeat)

        # delete intermediate datasets
        HelperFunctions.deleteDataItems(itemList)

        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to finish.")

        return



# helper functions are defined below
class helpers:
    
    # This function calculates convergence index (CI) from an Aspect grid
    def calculateCI(self, aspectRas, ciRas, tempFolder):
        # aspectRas: input Aspect grid
        # ciRas: output CI grid
        # tempFolder: temporary folder to store temporary files

        directionList = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        temRasList = []
        text1 = "0 0 0"
        text2 = "1 0 0"
        text3 = "0 1 0"
        text4 = "0 0 1"
        # for each direction, construct a kernel file and calculate focal statistic of the Aspect grid
        for direction in directionList:
            fileName = tempFolder + "/weight_" + direction + ".txt"
            f = open(fileName, "w")
            f.write("3 3\n")
            if direction == "N":
                f.write(text3 + "\n")
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 180
            elif direction == "NE":
                f.write(text4 + "\n")
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 225
            elif direction == "E":
                f.write(text1 + "\n")
                f.write(text4 + "\n")
                f.write(text1 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 270
            elif direction == "SE":
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.write(text4 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 315
            elif direction == "S":
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.write(text3 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 0
            elif direction == "SW":
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.write(text2 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 45
            elif direction == "W":
                f.write(text1 + "\n")
                f.write(text2 + "\n")
                f.write(text1 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 90
            elif direction == "NW":
                f.write(text2 + "\n")
                f.write(text1 + "\n")
                f.write(text1 + "\n")
                f.close()
                NbrWeight1 = NbrWeight(fileName)
                focal1 = FocalStatistics(aspectRas, NbrWeight1, "SUM", "DATA")
                angle1 = 135
            arcpy.AddMessage("focal statistics done " + direction)
            abs1 = Abs(focal1 - angle1)
            s1 = Con(abs1 > 180, Minus(360, abs1), abs1)
            temRas = "temRas_" + direction
            s1.save(temRas)
            temRasList.append(temRas)
        # combine the eight directional grids using cell statistic
        outCS = CellStatistics(temRasList, "MEAN", "DATA")
        ci = Minus(outCS, 90)
        ci.save(ciRas)
        arcpy.AddMessage("CI is done")
        # delete intermediate data
        HelperFunctions.deleteDataItems(temRasList)
        arcpy.AddMessage("delete done")
        return

    # This function calculates TPI and uses TPI threshold to identify Bathymetric Low features
    def TPI_Tool_Low(
        self,
        tempWS,
        bathyRas,
        tpiRas,
        outFeat,
        areaThreshold,
        areaUnit,
        tpiRadius,
        tpiSTDScale,
    ):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # tpiRas: output TPI grid
        # outFeat: output Bathymetric Low features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # tpiRadius: input radius value of a circular window used to calculated TPI
        # tpiSTDScale: input TPI threshold used to identify Bathymetric Low features

        arcpy.AddMessage("running TPI tool ...")

        tpiRasName = tpiRas[tpiRas.rfind("/") + 1 :]
        tpiRas1 = tempWS + "/" + tpiRasName
        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.management.Copy(tpiRas1, tpiRas)
            arcpy.AddMessage(tpiRas + " exists and will be used")
        elif tpiRadius == 0:  # you have to set a radius greater than 0
            arcpy.AddMessage(
                "You must provide a radius greater than 0 to calculate TPI"
            )
            return
        else:  # calling the helper function to calculate TPI
            arcpy.AddMessage("calculating TPI...")
            HelperFunctions.calculateTPI(bathyRas, tpiRadius, tpiRas)
        # copy the TPI raster to a backup directory
        arcpy.management.Copy(tpiRas, tpiRas1)

        # obtain spatial mean and spatial standard deviation of the TPI grid
        tpiSTDResult = arcpy.management.GetRasterProperties(tpiRas, "STD")
        stdText = tpiSTDResult.getOutput(0)
        if stdText.find(",") > 0:
            stdText = HelperFunctions.convertDecimalSeparator(stdText)
        tpiSTD = float(stdText)
        tpiMEANResult = arcpy.management.GetRasterProperties(tpiRas, "MEAN")
        meanText = tpiMEANResult.getOutput(0)
        if meanText.find(",") > 0:
            meanText = HelperFunctions.convertDecimalSeparator(meanText)
        tpiMean = float(meanText)
        # define the TPI threshold value for the subsequent mapping
        tpiThreshold = tpiMean - float(tpiSTDScale) * tpiSTD
        arcpy.AddMessage("using tpi threshold " + str(tpiThreshold))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        # select areas that satisfy the threshold condition
        HelperFunctions.selectRaster(tpiRas, tpiClassRas1, tpiThreshold, "<=")

        # convert selected areas to polygons
        tpiPoly1 = tempWS + "/" + "tpiC_poly"
        arcpy.conversion.RasterToPolygon(tpiClassRas1, tpiPoly1, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.management.AddGeometryAttributes(tpiPoly1, "AREA_GEODESIC", "", areaUnit1)
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)
        arcpy.AddMessage(str(areaThreshold))

        # further select areas based on the input area threshold
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.analysis.Select(tpiPoly1, outFeat, where_clause)
        arcpy.AddMessage("selection by area done")

        arcpy.management.Delete(tpiPoly1)
        arcpy.management.Delete(tpiClassRas1)
        HelperFunctions.deleteAllFields(outFeat)

        arcpy.AddMessage("TPI tool is done")
        return

    # This function calculates positive openness and uses it to identify Bathymetric Low features
    def opennessLow(
        self,
        tempWS,
        bathyRas,
        poRas,
        outFeat,
        areaThreshold,
        areaUnit,
        poRadius,
        poSTDScaleLarge,
        poSTDScaleSmall,
        messages,
    ):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # poRas: output positive openness grid
        # outFeat: output Bathymetric Low features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # poRadius: input radius value of a circular window used to calculated positive openness
        # poSTDScaleLarge: first input positive openness threshold used to identify Bathymetric Low features
        # poSTDScaleSmall: second input positive openness threshold used to identify Bathymetric Low features
        # messages: to handle error messages
        arcpy.AddMessage("runing openness Low tool ...")

        poRasName = poRas[poRas.rfind("/") + 1 :]

        poRas1 = tempWS + "/" + poRasName
        # If the positive openness raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate positive openness with a defined noRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(poRas1):
            arcpy.management.CopyRaster(poRas1, poRas)
            arcpy.AddMessage(poRas + " exists and will be used")
        elif poRadius == 0:  # you have to set the radius > 0
            arcpy.AddMessage(
                "You must provide a radius greater than 0 to calculate openness"
            )
            return
        else:  # call the helper function to calculate positive openness
            arcpy.AddMessage("calculating Positive Openness...")
            opennessParameter = "positiveOpenness"
            HelperFunctions.calculateOpenness(
                bathyRas, poRadius, opennessParameter, poRas, tempWS, messages
            )
        arcpy.management.CopyRaster(poRas, poRas1)

        interimDataList = []

        # The following codes are used to identify possible 'bottoms' (or 'pits') or Bathymetry Low features
        # The way doing that is to iidentify sinks

        # identify sinks
        fdRas = tempWS + "/" + "fdRas"
        interimDataList.append(fdRas)
        outFlowDirection = FlowDirection(bathyRas)
        outFlowDirection.save(fdRas)
        arcpy.AddMessage("flow direction done")

        sinkRas = tempWS + "/" + "sinkRas"
        interimDataList.append(sinkRas)
        outSink = Sink(fdRas)
        outSink.save(sinkRas)
        arcpy.AddMessage("sink done")

        # convert sinks to polygons
        sinksPoly = tempWS + "/" + "sinks_poly"
        interimDataList.append(sinksPoly)
        arcpy.conversion.RasterToPolygon(sinkRas, sinksPoly, "NO_SIMPLIFY")
        arcpy.AddMessage("convert sinks to polygon done")

        # select first set of areas (features) areas with po <= poThresholdLarge
        poSTDResult = arcpy.management.GetRasterProperties(poRas, "STD")
        stdText = poSTDResult.getOutput(0)
        if stdText.find(",") > 0:
            stdText = HelperFunctions.convertDecimalSeparator(stdText)
        poSTD = float(stdText)
        poMEANResult = arcpy.management.GetRasterProperties(poRas, "MEAN")
        meanText = poMEANResult.getOutput(0)
        if meanText.find(",") > 0:
            meanText = HelperFunctions.convertDecimalSeparator(meanText)
        poMean = float(meanText)
        poThresholdLarge = poMean - float(poSTDScaleLarge) * poSTD
        arcpy.AddMessage("using po threshold " + str(poThresholdLarge))
        poClassRas1 = tempWS + "/" + "po_C"
        HelperFunctions.selectRaster(poRas, poClassRas1, poThresholdLarge, "<=")
        interimDataList.append(poClassRas1)

        # select second set of areas (features) areas with po <= poThresholdSmall
        poThresholdSmall = poMean - float(poSTDScaleSmall) * poSTD
        arcpy.AddMessage("using po threshold " + str(poThresholdSmall))
        poClassRas2 = tempWS + "/" + "po_C1"
        HelperFunctions.selectRaster(poRas, poClassRas2, poThresholdSmall, "<=")
        interimDataList.append(poClassRas2)

        # convert selected areas to polygons
        poPoly1 = tempWS + "/" + "poC_poly"
        interimDataList.append(poPoly1)
        arcpy.conversion.RasterToPolygon(poClassRas1, poPoly1, "NO_SIMPLIFY")

        poPoly2 = tempWS + "/" + "poC1_poly"
        interimDataList.append(poPoly2)
        arcpy.conversion.RasterToPolygon(poClassRas2, poPoly2, "NO_SIMPLIFY", "VALUE")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.management.AddGeometryAttributes(poPoly1, "AREA_GEODESIC", "", areaUnit1)
        arcpy.management.AddGeometryAttributes(poPoly2, "AREA_GEODESIC", "", areaUnit1)

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)

        # further selection based on the input area threshold
        poPoly1_selected = tempWS + "/" + "poC_poly_selected"
        interimDataList.append(poPoly1_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.analysis.Select(poPoly1, poPoly1_selected, where_clause)

        poPoly2_selected = tempWS + "/" + "poC1_poly_selected"
        interimDataList.append(poPoly2_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.analysis.Select(poPoly2, poPoly2_selected, where_clause)

        # select based on location
        # select from the first set of features that contain 'pits'
        poPoly1_selected1 = tempWS + "/" + "poC_poly_selected1"
        interimDataList.append(poPoly1_selected1)
        layerName1 = "lyr1"
        arcpy.management.MakeFeatureLayer(poPoly1_selected, layerName1)
        arcpy.management.SelectLayerByLocation(layerName1, "intersect", sinksPoly)
        arcpy.management.CopyFeatures(layerName1, poPoly1_selected1)
        arcpy.AddMessage("select by location done")
        # select from the second set of features that contain 'pits'
        poPoly2_selected1 = tempWS + "/" + "poC1_poly_selected1"
        interimDataList.append(poPoly2_selected1)
        layerName2 = "lyr2"
        arcpy.management.MakeFeatureLayer(poPoly2_selected, layerName2)
        arcpy.management.SelectLayerByLocation(layerName2, "intersect", sinksPoly)
        arcpy.management.CopyFeatures(layerName2, poPoly2_selected1)
        arcpy.AddMessage("select by location done")

        # spatial join to join attributes
        joinedFeat = tempWS + "/" + "Feats_joined"
        interimDataList.append(joinedFeat)
        arcpy.analysis.SpatialJoin(
            poPoly2_selected1,
            poPoly1_selected1,
            joinedFeat,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "#",
            "INTERSECT",
        )
        arcpy.AddMessage("spatial join done")

        # select by attribute
        # If a feature from the second set intersects 2 or more features from the first set,
        # keep these features from the first set by using the select by location function
        joinedFeat_selected = tempWS + "/" + "Feats_joined_selected"
        interimDataList.append(joinedFeat_selected)
        where_clause = '"Join_Count" >= 2'
        arcpy.analysis.Select(joinedFeat, joinedFeat_selected, where_clause)
        # select based on location
        poPoly1_selected2 = tempWS + "/" + "poC_poly_selected2"
        interimDataList.append(poPoly1_selected2)
        layerName3 = "lyr3"
        arcpy.management.MakeFeatureLayer(poPoly1_selected1, layerName3)
        arcpy.management.SelectLayerByLocation(
            layerName3, "intersect", joinedFeat_selected
        )
        arcpy.management.CopyFeatures(layerName3, poPoly1_selected2)
        arcpy.AddMessage("select by location done")
        # If a feature from the second set intersects only one features from the first set, keep the feature from the second set
        joinedFeat_selected1 = tempWS + "/" + "Feats_joined_selected1"
        interimDataList.append(joinedFeat_selected1)
        where_clause = '"Join_Count" < 2'
        arcpy.analysis.Select(joinedFeat, joinedFeat_selected1, where_clause)
        arcpy.AddMessage("select by attribute done")

        # merge the two subsets of features to form the final set of Bathymetric Low features

        mergedFeat = tempWS + "/" + "Feats_merged"
        interimDataList.append(mergedFeat)
        arcpy.management.Merge([poPoly1_selected2, joinedFeat_selected1], mergedFeat)
        arcpy.AddMessage("merge done")
        arcpy.management.Copy(mergedFeat, outFeat)

        # delete intermediate results
        HelperFunctions.deleteDataItems(interimDataList)
        HelperFunctions.deleteAllFields(outFeat)

        arcpy.AddMessage("Openness Low tool is done")

    # This function calculates TPI and CI, and then use them to map the Bathymetric Low features
    def TPI_CI_Low(
        self,
        tempWS,
        bathyRas,
        tpiRas,
        ciRas,
        outFeat,
        areaThreshold,
        areaUnit,
        tpiRadius,
        tpiSTDScale,
        ciSTDScale,
        tempFolder,
    ):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # tpiRas: output TPI grid
        # ciRas: output CI grid
        # outFeat: output Bathymetric Low features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # tpiRadius: input radius value of a circular window used to calculated TPI
        # tpiSTDScale: input TPI threshold used to identify Bathymetric Low features
        # ciSTDScale: input CI threshold used to identify Bathymetric Low features
        # tempFolder: temporary folder to store temporary files

        arcpy.AddMessage("runing TPI CI Low tool ...")

        interimDataList = []
        descData = arcpy.Describe(bathyRas)
        cellsize = descData.meanCellHeight

        # calculate the convergence index (CI)
        ciRasName = ciRas[ciRas.rfind("/") + 1 :]
        ciRas1 = tempWS + "/" + ciRasName
        # If the CI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate CI only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(ciRas1):
            arcpy.management.CopyRaster(ciRas1, ciRas)
            arcpy.AddMessage(ciRas + " exists and will be used")
        else:
            arcpy.AddMessage("calculating CI...")
            # fill the sinks on the bathymetry data
            bathyRas1 = tempWS + "/" + "bathyFilled"
            interimDataList.append(bathyRas1)
            outFill = Fill(bathyRas)
            outFill.save(bathyRas1)
            arcpy.AddMessage("bathymetry filled done")

            # calculate aspect variable
            aspectRas = tempWS + "/" + "aspectRas"
            interimDataList.append(aspectRas)
            aspect = Aspect(bathyRas1)
            aspect.save(aspectRas)
            arcpy.AddMessage("Aspect Raster generated")

            # call the helper function to calculate CI
            self.calculateCI(aspectRas, ciRas, tempFolder)
        # copy the CI raster to a backup directory
        arcpy.management.CopyRaster(ciRas, ciRas1)

        # calculate the TPI
        tpiRasName = tpiRas[tpiRas.rfind("/") + 1 :]
        tpiRas1 = tempWS + "/" + tpiRasName
        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.management.CopyRaster(tpiRas1, tpiRas)
            arcpy.AddMessage(tpiRas + " exists and will be used")
        elif tpiRadius == 0:  # you have to set radius > 0
            arcpy.AddMessage(
                "You must provide a radius greater than 0 to calculate tpi"
            )
            return
        else:
            arcpy.AddMessage("calculating TPI...")
            HelperFunctions.calculateTPI(bathyRas1, tpiRadius, tpiRas)
        # copy the TPI raster to a backup directory
        arcpy.management.CopyRaster(tpiRas, tpiRas1)

        # obtain spatial mean and standard deviation of the CI grid
        # select CI based on the threshold
        ciSTDResult = arcpy.management.GetRasterProperties(ciRas, "STD")
        cistdText = ciSTDResult.getOutput(0)
        if cistdText.find(",") > 0:
            cistdText = HelperFunctions.convertDecimalSeparator(cistdText)
        ciSTD = float(cistdText)
        ciMEANResult = arcpy.management.GetRasterProperties(ciRas, "MEAN")
        cimeanText = ciMEANResult.getOutput(0)
        if cimeanText.find(",") > 0:
            cimeanText = HelperFunctions.convertDecimalSeparator(cimeanText)
        ciMean = float(cimeanText)
        ciThreshold = ciMean - float(ciSTDScale) * ciSTD
        arcpy.AddMessage("using ci threshold " + str(ciThreshold))
        ciClassRas1 = tempWS + "/" + "ciC"
        interimDataList.append(ciClassRas1)
        HelperFunctions.selectRaster(ciRas, ciClassRas1, ciThreshold, "<=")
        arcpy.AddMessage("CI selection done")

        # select TPI based on the threshold
        tpiSTDResult = arcpy.management.GetRasterProperties(tpiRas, "STD")
        tpistdText = tpiSTDResult.getOutput(0)
        if tpistdText.find(",") > 0:
            tpistdText = HelperFunctions.convertDecimalSeparator(tpistdText)
        tpiSTD = float(tpistdText)
        tpiMEANResult = arcpy.management.GetRasterProperties(tpiRas, "MEAN")
        tpimeanText = tpiMEANResult.getOutput(0)
        if tpimeanText.find(",") > 0:
            tpimeanText = HelperFunctions.convertDecimalSeparator(tpimeanText)
        tpiMean = float(tpimeanText)
        tpiThreshold = tpiMean - float(tpiSTDScale) * tpiSTD
        arcpy.AddMessage("using tpi threshold " + str(tpiThreshold))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        interimDataList.append(tpiClassRas1)
        HelperFunctions.selectRaster(tpiRas, tpiClassRas1, tpiThreshold, "<=")
        arcpy.AddMessage("TPI selection done")

        # mosaic ciC and tpiC
        mosaicRas = "em_ciC_tpiC"
        interimDataList.append(mosaicRas)
        inputRasters = [ciClassRas1, tpiClassRas1]
        arcpy.management.MosaicToNewRaster(
            inputRasters,
            tempWS,
            mosaicRas,
            tpiClassRas1,
            "8_BIT_UNSIGNED",
            cellsize,
            "1",
            "MEAN",
            "FIRST",
        )
        arcpy.AddMessage("mosaic done")

        # convert raster to polygon
        mosaicRas = tempWS + "/" + "em_ciC_tpiC"
        ci_tpiPoly = tempWS + "/" + "ci_tpiC_poly"
        interimDataList.append(ci_tpiPoly)
        arcpy.conversion.RasterToPolygon(mosaicRas, ci_tpiPoly, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.management.AddGeometryAttributes(
            ci_tpiPoly, "AREA_GEODESIC", "", areaUnit1
        )
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)

        # further selection based on the input area threshold
        ci_tpiPoly_selected = tempWS + "/" + "ci_tpiC_poly_selected"
        interimDataList.append(ci_tpiPoly_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.analysis.Select(ci_tpiPoly, ci_tpiPoly_selected, where_clause)
        arcpy.AddMessage("selection by area done")

        # eliminate holes in the polygons
        ci_tpiPoly_selected1 = tempWS + "/" + "ci_tpiC_poly_selected1"
        interimDataList.append(ci_tpiPoly_selected1)
        areaThreshold = areaThreshold / converter
        size = str(areaThreshold) + " " + areaUnit
        arcpy.management.EliminatePolygonPart(
            ci_tpiPoly_selected,
            ci_tpiPoly_selected1,
            "AREA",
            size,
            "",
            "CONTAINED_ONLY",
        )
        arcpy.AddMessage("elimination holes done")

        # copy featureclass
        arcpy.management.Copy(ci_tpiPoly_selected1, outFeat)

        # delete intermediate results
        HelperFunctions.deleteDataItems(interimDataList)
        HelperFunctions.deleteAllFields(outFeat)

        arcpy.AddMessage("TPI CI Low tool is done")

    
