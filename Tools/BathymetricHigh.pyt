#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: November 21, 2024
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import math
import warnings

import arcpy
import numpy as np
from arcpy import env
from arcpy.sa import *
import os
import sys
import multiprocessing
from importlib import reload
from datetime import datetime
import ContourToolsFunctions
from ContourToolsFunctions import execute_contour_BH
import HelperFunctions

arcpy.CheckOutExtension("Spatial")

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "BathymetricHigh"

        # List of tool classes associated with this toolbox
        # There are three tools in this toolset used to map Bathymetric High features.
        self.tools = [TPITool, TPI_LMITool, Openness_High_Tool, ContourBH_Tool, PseudoContourBH_Tool]


# TPITool uses Topographic Position Index (TPI) technique to map Bathymetric High features
class TPITool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "TPI Tool Bathymetric High"
        self.description = "Calculate TPI and Generate Bathymetric High features"
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

        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.env.overwriteOutput = True
        bathyRas = parameters[0].valueAsText
        tpiRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tpiRadius = parameters[4].valueAsText
        tpiSTDScale = parameters[5].valueAsText
        tempWS = parameters[6].valueAsText
        # enable the helper functions
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

        # call the helper function to calculate TPI and generate output Bathymetric High features
        helper.TPI_Tool_High(
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


# TPI_LMITool uses Topographic Position Index (TPI) technique and Local Moran I (LMI) technique to map Bathymetric High features
class TPI_LMITool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "TPI LMI Tool Bathymetric High"
        self.description = "Calculate TPI/LMI and Generate Bathymetric High features"
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
            displayName="TPI STD Scale Large",
            name="tpiSTDScaleLarge",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 1.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="TPI STD Scale Small",
            name="tpiSTDScaleSmall",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param6.value = 0.5

        # eighth parameter
        param7 = arcpy.Parameter(
            displayName="LMI Weight File",
            name="lmiWeightFile",
            datatype="DEFile",
            parameterType="Required",
            direction="Input",
        )
        param7.filter.list = ["txt"]

        # nineth parameter
        param8 = arcpy.Parameter(
            displayName="LMI STD Scale",
            name="lmiSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param8.value = 1.0

        # tenth parameter
        param9 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
        param9.defaultEnvironmentName = "workspace"

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

        bathyRas = parameters[0].valueAsText
        tpiRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        tpiRadius = parameters[4].valueAsText
        tpiSTDScaleLarge = parameters[5].valueAsText
        tpiSTDScaleSmall = parameters[6].valueAsText
        lmiWeightFile = parameters[7].valueAsText
        lmiSTDScale = parameters[8].valueAsText
        tempWS = parameters[9].valueAsText
        # enable the helper functions
        helper = helpers()

        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        tpiRas = HelperFunctions.convert_backslash_forwardslash(tpiRas)
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
        # call the helper function to calculate TPI and LMI and generate Bathymetric High features
        helper.TPI_LMI_Tool(
            tempWS,
            bathyRas,
            tpiRas,
            outFeat,
            areaThresholdValue,
            areaUnit,
            tpiRadius,
            tpiSTDScaleLarge,
            tpiSTDScaleSmall,
            lmiWeightFile,
            lmiSTDScale,
        )

        return


# Openness_High_Tool uses Openness technique to map Bathymetric High features
class Openness_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Openness Tool Bathymetric High"
        self.description = (
            "Cacluate Negative Openness and generate an output Featureclass"
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
            displayName="Output Negative Openness Raster",
            name="noRas",
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
            name="noRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 3

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="NO STD Scale Large",
            name="noSTDScaleLarge",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input",
        )
        param5.value = 2.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="NO STD Scale Small",
            name="noSTDScaleSmall",
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
        noRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        noRadius = parameters[4].valueAsText
        noSTDScaleLarge = parameters[5].valueAsText
        noSTDScaleSmall = parameters[6].valueAsText
        tempWS = parameters[7].valueAsText

        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        noRas = HelperFunctions.convert_backslash_forwardslash(noRas)
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
        if noRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output NO raster must be nominated as a raster dataset in a File GeoDatabase!"
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
        workspaceName1 = noRas[0 : noRas.rfind("/")]
        workspaceName2 = outFeat[0 : outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]
        # waterproof some unusal errors
        if noRas == outFeat:
            messages.addErrorMessage(
                "The output Negative Openness raster and output Featureclass cannot have the same name in the same workspace!"
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
        # call the helper function to calculate openness and generate Bathymetric High features
        helper.opennessHigh(
            tempWS,
            bathyRas,
            noRas,
            outFeat,
            areaThresholdValue,
            areaUnit,
            noRadius,
            noSTDScaleLarge,
            noSTDScaleSmall,
            messages,
        )

        return



# This tool is used to map bathymetric high features using the contour-based methods
class ContourBH_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Contour Tool Bathymetric High"
        self.description = "Use contour method to generate Bathymetric High features"
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
            displayName="Output Bathymetric High Featureclass",
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
                "The shallowest contour depth value must be negative or zero!"
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
        arcpy.CalculateField_management(
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
                        arcpy.AddField_management(
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
                    arcpy.CalculateField_management(
                        dissolvedFeat, fieldName, expression, "PYTHON3"
                    )
                    # further select only those features that have positive depth difference greater than a positive
                    # threshold
                    # These selected features are thus bathymetric high features
                    # depthFactor = 0.07
                    if depthMethod == 'As Percentage of the Contour Value (%)':
                        depthThreshold = abs(depthFactor / 100 * depth)
                    else:
                        depthThreshold = depthFactor
                    whereClause = "depth_diff > " + str(depthThreshold)
                    arcpy.AddMessage("depth_diff " + str(depthThreshold))
                    selectedFeat = selectedFeat + "3"
                    itemList.append(selectedFeat)
                    arcpy.analysis.Select(dissolvedFeat, selectedFeat, whereClause)
                    arcpy.AddMessage("selected3 done")
                    mergeList.append(selectedFeat)

            depth = depth - cInterval

        # merge selected features for all contour values (e.g., -40m to -150m),
        # in the descending order (from -40m to -150m)
        outFeat1 = "contours_merged_BH"
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
        statField = [["JOIN_FID", "Last"]]
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
        # a deeper contour (-60m in this case, represented by the LAST_JOIN_FID).
        fieldName = "idV"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 10)
        layer1 = "layer1"
        arcpy.management.MakeFeatureLayer(outFeat1, layer1)
        arcpy.management.AddJoin(layer1, "OBJECTID", sumTab1, "LAST_JOIN_FID")
        expression = "!sumTable1.LAST_JOIN_FID!"
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
            # call the execute_contour_BH() from the ContourToolsFunctions module
            # the function is the entry point for the multiprocessing
            if method == 'First Derivative':
                arcpy.AddMessage("Using the First Derivative method!")
            else:
                arcpy.AddMessage("Using the Second Derivative method!")
            execute_contour_BH(argList, method, nCPU)
            arcpy.AddMessage('multiprocessing Done.')

            # merge the individual outputs from the multiprocessing as the second selection
            arcpy.management.Merge(outFeat1List, outFeat1_Selected2)
            # merge the first selection and second selection as the final selection from the merged features

            arcpy.management.Merge([outFeat1_Selected1, outFeat1_Selected2], outFeat)
            arcpy.AddMessage("final merged done")

            # delete all temporary workspaces and folders
            for workspace in workspaceList:
                arcpy.Delete_management(workspace)
            arcpy.AddMessage("All temporary workspaces are deleted")

            for folder in tempfolderList:
                arcpy.Delete_management(folder)
            arcpy.AddMessage("All temporary folders are deleted")
        else:  # no feature in the second selection, just copy the first selection
            arcpy.management.Copy(outFeat1_Selected1, outFeat)

        # delete intermediate datasets
        HelperFunctions.deleteDataItems(itemList)

        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took " + str(diff) + " to finish.")

        return


class PseudoContourBH_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Pseudo Contour Tool Bathymetric High"
        self.description = "Use pseudo contour method to generate Bathymetric High features"
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
            displayName="Output Bathymetric High Featureclass",
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
        # to provide a default value for the maximum area threshold parameter
        if parameters[8].value:  # if the maximum area threshold parameter has an existing value, do nothing
            return
        else:
            if parameters[0].value:
                bathyRas = parameters[0].valueAsText
                helper = helpers()
                # if the input bathymetry raster is selected from a drop-down list, the bathyRas does not contain
                # the full path
                # In this case, the full path needs to be obtained from the map layer
                if bathyRas.rfind("/") < 0:
                    aprx = arcpy.mp.ArcGISProject("CURRENT")
                    m = aprx.activeMap
                    for lyr in m.listLayers():
                        if lyr.isRasterLayer:
                            if bathyRas == lyr.name:
                                bathyRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

                minResult = arcpy.GetRasterProperties_management(bathyRas, "MINIMUM")
                minValue = minResult.getOutput(0)
                outCon = Con(Raster(bathyRas) >= float(minValue), 1)
                tempTab = "tempTable"
                zonStat = ZonalStatisticsAsTable(outCon, "VALUE", outCon,
                                                 tempTab, "NODATA", "SUM")
                cursor = arcpy.SearchCursor(tempTab)
                row = cursor.next()
                area = row.getValue("AREA")
                # the default maximum area threshold is one-third of the total area, using SquareKilometers as unit
                area = int(round(area / 1000000 / 3, 0))
                arcpy.Delete_management(outCon)
                arcpy.Delete_management(tempTab)
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
            # For example, they follow the outer edges instead of the centres of raster cells.
            # One important difference is that this approach will create pseudo contours for partial features
            # cut off by the boundary.
            tempString = str(abs(depth)) + "m"
            tempString = tempString.replace('.', 'p')
            contourPoly = "outContour_" + tempString + "_poly"
            itemList.append(contourPoly)
            outCon = Con(Raster(bathyRas) >= depth, 1)
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
                        arcpy.AddField_management(
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
                    arcpy.CalculateField_management(
                        dissolvedFeat, fieldName, expression, "PYTHON3"
                    )
                    # further select only those features that have positive depth difference greater than a positve
                    # threshold
                    # These selected features are thus bathymetric high features
                    # depthFactor = 0.07
                    if depthMethod == 'As Percentage of the Contour Value (%)':
                        depthThreshold = abs(depthFactor / 100 * depth)
                    else:
                        depthThreshold = depthFactor
                    whereClause = "depth_diff > " + str(depthThreshold)
                    arcpy.AddMessage("depth_diff " + str(depthThreshold))
                    selectedFeat = selectedFeat + "3"
                    itemList.append(selectedFeat)
                    arcpy.analysis.Select(dissolvedFeat, selectedFeat, whereClause)
                    arcpy.AddMessage("selected3 done")
                    mergeList.append(selectedFeat)

            depth = depth - cInterval

        # merge selected features for all contour values (e.g., -40m to -150m),
        # in the descending order (from -40m to -150m)
        outFeat1 = "contours_merged_BH_pseudo"
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
        statField = [["JOIN_FID", "Last"]]
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
        # a deeper contour (-60m in this case, represented by the LAST_JOIN_FID).
        fieldName = "idV"
        arcpy.management.AddField(outFeat1, fieldName, "LONG", 10)
        layer1 = "layer1"
        arcpy.management.MakeFeatureLayer(outFeat1, layer1)
        arcpy.management.AddJoin(layer1, "OBJECTID", sumTab1, "LAST_JOIN_FID")
        expression = "!sumTable1.LAST_JOIN_FID!"
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
            # call the execute_contour_BH() from the ContourToolsFunctions module
            # the function is the entry point for the multiprocessing
            if method == 'First Derivative':
                arcpy.AddMessage("Using the First Derivative method!")
            else:
                arcpy.AddMessage("Using the Second Derivative method!")
            execute_contour_BH(argList, method, nCPU)
            arcpy.AddMessage('multiprocessing Done.')

            # merge the individual outputs from the multiprocessing as the second selection
            arcpy.management.Merge(outFeat1List, outFeat1_Selected2)
            # merge the first selection and second selection as the final selection from the merged features

            arcpy.management.Merge([outFeat1_Selected1, outFeat1_Selected2], outFeat)
            arcpy.AddMessage("final merged done")

            # delete all temporary workspaces and folders
            for workspace in workspaceList:
                arcpy.Delete_management(workspace)
            arcpy.AddMessage("All temporary workspaces are deleted")

            for folder in tempfolderList:
                arcpy.Delete_management(folder)
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
    
    # This function calculates LMI values from the bathymetry grid
    def calculateLMI(self, bathy, weightFile, lmiRas):
        # bathy: input bathymetry grid
        # weightFile: the path to the weight kernal file defining a neighbourhood
        # lmiRas: output LMI grid

        # spatial mean of the bathymetry grid
        meanResult = arcpy.GetRasterProperties_management(bathy, "MEAN")
        meanText = meanResult.getOutput(0)
        if meanText.find(",") > 0:
            meanText = HelperFunctions.convertDecimalSeparator(meanText)
        # spatial standard deviation of the bathymetry grid
        stdResult = arcpy.GetRasterProperties_management(bathy, "STD")
        stdText = stdResult.getOutput(0)
        if stdText.find(",") > 0:
            stdText = HelperFunctions.convertDecimalSeparator(stdText)
        NbrWeight1 = NbrWeight(weightFile)
        # the LMI algorithm
        outFocal = FocalStatistics(
            Minus(bathy, float(meanText)), NbrWeight1, "SUM", "DATA"
        )
        outRas = Times(
            Divide(Minus(bathy, float(meanText)), Square(float(stdText))), outFocal
        )
        outRas.save(lmiRas)
        arcpy.AddMessage("local moran i done")
        return

    # This function extract input features from the bathymetry grid
    def extractMask(self, tempWS, bathy, inFeat, STDScale=0):
        # tempWS: temporary workspace to store temporary data
        # bathy: input bathymetry grid
        # inFeat: input features
        # STDScale: threshold value

        cursor = arcpy.SearchCursor(inFeat)
        # all extracted areas are to be appended and merged later
        inFeats = []
        temp1 = tempWS + "/" + "temp1"
        # loop through each input feature
        for row in cursor:
            polyID = row.getValue("OBJECTID")
            idV = row.getValue("Id")
            arcpy.AddMessage(str(polyID) + ";" + str(idV))
            whereClause = '"OBJECTID" = ' + str(polyID)
            arcpy.Select_analysis(inFeat, temp1, whereClause)
            extractedRas = tempWS + "/" + "extract_" + str(polyID)
            if arcpy.Exists(extractedRas):
                arcpy.Delete_management(extractedRas)
            # extract bathymetry grid for the area covered by the input feature
            outMask1 = ExtractByMask(bathy, temp1)
            outMask1.save(extractedRas)
            # select proportion of the extracted raster with a condition (.= Threshold)
            extractedRas1 = tempWS + "/" + "extract_" + str(polyID) + "_1"
            if arcpy.Exists(extractedRas1):
                arcpy.Delete_management(extractedRas1)
            STDResult = arcpy.GetRasterProperties_management(extractedRas, "STD")
            stdText = STDResult.getOutput(0)
            if stdText.find(",") > 0:
                stdText = HelperFunctions.convertDecimalSeparator(stdText)
            STD = float(stdText)
            MEANResult = arcpy.GetRasterProperties_management(extractedRas, "MEAN")
            meanText = MEANResult.getOutput(0)
            if meanText.find(",") > 0:
                meanText = HelperFunctions.convertDecimalSeparator(meanText)
            Mean = float(meanText)
            MAXResult = arcpy.GetRasterProperties_management(extractedRas, "MAXIMUM")
            maxText = MAXResult.getOutput(0)
            if maxText.find(",") > 0:
                maxText = HelperFunctions.convertDecimalSeparator(maxText)
            Max = float(maxText)

            Threshold = Mean + STDScale * STD
            if Threshold >= Max:
                arcpy.AddMessage(
                    "You must provide a threhold smaller than the maximum value, reset to the mean value"
                )
                Threshold = Mean
            HelperFunctions.selectRaster(extractedRas, extractedRas1, Threshold, ">=", idV)

            # convert selected areas to polygons
            extractedFeat = extractedRas1 + "_poly"
            arcpy.RasterToPolygon_conversion(
                extractedRas1,
                extractedFeat,
                "NO_SIMPLIFY",
                "VALUE",
                "MULTIPLE_OUTER_PART",
            )
            inFeats.append(extractedFeat)
            arcpy.Delete_management(temp1)
            arcpy.Delete_management(extractedRas)
            arcpy.Delete_management(extractedRas1)
        del row, cursor

        return inFeats

    
    # This function calculates TPI and uses TPI threshold to identify Bathymetric High features
    def TPI_Tool_High(
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
        # outFeat: output Bathymetric High features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # tpiRadius: input radius value of a circular window used to calculated TPI
        # tpiSTDScale: input TPI threshold used to identify Bathymetric High features

        arcpy.AddMessage("running TPI tool ...")

        tpiRasName = tpiRas[tpiRas.rfind("/") + 1 :]
        tpiRas1 = tempWS + "/" + tpiRasName
        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.Copy_management(tpiRas1, tpiRas)
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
        arcpy.Copy_management(tpiRas, tpiRas1)

        # obtain spatial mean and spatial standard deviation of the TPI grid
        tpiSTDResult = arcpy.GetRasterProperties_management(tpiRas, "STD")
        stdText = tpiSTDResult.getOutput(0)
        if stdText.find(",") > 0:
            stdText = HelperFunctions.convertDecimalSeparator(stdText)

        tpiSTD = float(stdText)
        tpiMEANResult = arcpy.GetRasterProperties_management(tpiRas, "MEAN")
        meanText = tpiMEANResult.getOutput(0)
        if meanText.find(",") > 0:
            meanText = HelperFunctions.convertDecimalSeparator(stdText)
        tpiMean = float(meanText)
        # define the TPI threshold value for the subsequent mapping
        tpiThreshold = tpiMean + float(tpiSTDScale) * tpiSTD
        arcpy.AddMessage("using tpi threshold " + str(tpiThreshold))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        # select areas that satisfy the threshold condition
        HelperFunctions.selectRaster(tpiRas, tpiClassRas1, tpiThreshold, ">=")

        # convert selected areas to polygons
        tpiPoly1 = tempWS + "/" + "tpiC_poly"
        arcpy.RasterToPolygon_conversion(tpiClassRas1, tpiPoly1, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(tpiPoly1, "AREA_GEODESIC", "", areaUnit1)
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)
        arcpy.AddMessage(str(areaThreshold))

        # further select areas based on the input area threshold
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(tpiPoly1, outFeat, where_clause)
        arcpy.AddMessage("selection by area done")

        arcpy.Delete_management(tpiPoly1)
        arcpy.Delete_management(tpiClassRas1)
        HelperFunctions.deleteAllFields(outFeat)
        arcpy.AddMessage("TPI tool is done")
        return

    # This function calculates TPI and LMI and uses them to identify Bathymetric High features
    def TPI_LMI_Tool(
        self,
        tempWS,
        bathyRas,
        tpiRas,
        outFeat,
        areaThreshold,
        areaUnit,
        tpiRadius,
        tpiSTDScaleLarge,
        tpiSTDScaleSmall,
        lmiWeightFile,
        lmiSTDScale,
    ):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # tpiRas: output TPI grid
        # outFeat: output Bathymetric High features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # tpiRadius: input radius value of a circular window used to calculated TPI
        # tpiSTDScaleLarge: first input TPI threshold used to identify Bathymetric High features
        # tpiSTDScaleSmall: second input TPI threshold used to identify Bathymetric High features
        # lmiWeightFile: input weight kernel file for the calculaion of LMI
        # lmiSTDScale: input LMI threshold used to identify Bathymetric High features

        arcpy.AddMessage("runing TPI_LMI tool ...")

        tpiRasName = tpiRas[tpiRas.rfind("/") + 1 :]
        tpiRas1 = tempWS + "/" + tpiRasName

        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.Copy_management(tpiRas1, tpiRas)
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
        arcpy.Copy_management(tpiRas, tpiRas1)

        interimDataList = []

        # obtain spatial mean and standard deviation of the TPI raster
        # select first set of areas (features) with TPI >= tpiThresholdLarge
        # obtain spatial mean and spatial standard deviation of the TPI grid
        tpiSTDResult = arcpy.GetRasterProperties_management(tpiRas, "STD")
        stdText = tpiSTDResult.getOutput(0)
        if stdText.find(",") > 0:
            stdText = HelperFunctions.convertDecimalSeparator(stdText)
        tpiSTD = float(stdText)
        tpiMEANResult = arcpy.GetRasterProperties_management(tpiRas, "MEAN")
        meanText = tpiMEANResult.getOutput(0)
        if meanText.find(",") > 0:
            meanText = HelperFunctions.convertDecimalSeparator(stdText)
        tpiMean = float(meanText)
        tpiThresholdLarge = tpiMean + float(tpiSTDScaleLarge) * tpiSTD
        arcpy.AddMessage("using tpi threshold " + str(tpiThresholdLarge))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        interimDataList.append(tpiClassRas1)
        HelperFunctions.selectRaster(tpiRas, tpiClassRas1, tpiThresholdLarge, ">=")

        # select second set of areas (features) with TPI >= tpiThresholdSmall
        tpiThresholdSmall = tpiMean + float(tpiSTDScaleSmall) * tpiSTD
        arcpy.AddMessage("using tpi threshold " + str(tpiThresholdSmall))
        tpiClassRas2 = tempWS + "/" + "tpiC1"
        interimDataList.append(tpiClassRas2)
        HelperFunctions.selectRaster(tpiRas, tpiClassRas2, tpiThresholdSmall, ">=")

        # convert selected areas to polygons
        tpiPoly1 = tempWS + "/" + "tpiC_poly"
        interimDataList.append(tpiPoly1)
        arcpy.RasterToPolygon_conversion(tpiClassRas1, tpiPoly1, "NO_SIMPLIFY")

        tpiPoly2 = tempWS + "/" + "tpiC1_poly"
        interimDataList.append(tpiPoly2)
        arcpy.RasterToPolygon_conversion(tpiClassRas2, tpiPoly2, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(tpiPoly1, "AREA_GEODESIC", "", areaUnit1)
        arcpy.AddGeometryAttributes_management(tpiPoly2, "AREA_GEODESIC", "", areaUnit1)

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)

        # further select areas based on the input area threshold
        tpiPoly1_selected = tempWS + "/" + "tpiC_poly_selected"
        interimDataList.append(tpiPoly1_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(tpiPoly1, tpiPoly1_selected, where_clause)
        arcpy.AddMessage("selection by area done")

        # select based on location
        # only select the second set of features if they interset the first set
        tpiPoly2_selected = tempWS + "/" + "tpiC1_poly_selected"
        interimDataList.append(tpiPoly2_selected)
        layerName1 = "lyr1"
        arcpy.MakeFeatureLayer_management(tpiPoly2, layerName1)
        arcpy.SelectLayerByLocation_management(
            layerName1, "intersect", tpiPoly1_selected
        )
        arcpy.CopyFeatures_management(layerName1, tpiPoly2_selected)
        arcpy.AddMessage("select by location done")

        # further select areas based on the input area threshold
        tpiPoly2_selected1 = tempWS + "/" + "tpiC1_poly_selected1"
        interimDataList.append(tpiPoly2_selected1)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(tpiPoly2_selected, tpiPoly2_selected1, where_clause)
        arcpy.AddMessage("selection by area done")

        # The follwing bits are key diferences from the TPI tool.
        # The general idea is to use TPI method to identify the first group of Bathymetric High features (codes above).
        # The areas of identified features are then removed (substracted) from the bathymetric grid.
        # We then apply LMI method on the remaining bathymetric grid and identify additional Bathymetric High features.
        count = int(arcpy.GetCount_management(tpiPoly2_selected1)[0])
        if (
            count > 50
        ):  # If more than 50 features in the second set, we will only work on the 50 largest features to save time
            arcpy.AddMessage(
                "there are "
                + str(count)
                + " features in "
                + tpiPoly2_selected1
                + "; only 50 largest polygons will be processed for the next several steps"
            )
            sortFeat = tempWS + "/" + "tpiC1_poly_selected1_sorted"
            interimDataList.append(sortFeat)
            sort_field = [["AREA_GEO", "DESCENDING"]]
            arcpy.Sort_management(tpiPoly2_selected1, sortFeat, sort_field)
            # select the largest 50 features and extractMask for these features
            tpiPoly2_selected1_1 = tempWS + "/" + "tpiC1_poly_selected1_1"
            interimDataList.append(tpiPoly2_selected1_1)
            where_clause = '"OBJECTID" <= 50'
            arcpy.Select_analysis(sortFeat, tpiPoly2_selected1_1, where_clause)
            # select the remaining features
            tpiPoly2_selected1_2 = tempWS + "/" + "tpiC1_poly_selected1_2"
            interimDataList.append(tpiPoly2_selected1_2)
            where_clause = '"OBJECTID" > 50'
            arcpy.Select_analysis(sortFeat, tpiPoly2_selected1_2, where_clause)

            # calling the helper function to extract rasters from the bathymetry data one by one based on the selected polygons above
            # for each extracted raster, select area with value >= threshold
            extractedFeats = self.extractMask(tempWS, bathyRas, tpiPoly2_selected1_1)
        else:  # if less than 50 features in total
            # calling the helper function to extract rasters from the bathymetry data one by one based on the selected polygons above
            # for each extracted raster, select area with value >= threshold
            extractedFeats = self.extractMask(tempWS, bathyRas, tpiPoly2_selected1)

        arcpy.AddMessage("extract done")
        # merge inFeats resulted from the extractMask function
        extractPoly = tempWS + "/" + "extracted_merged"
        interimDataList.append(extractPoly)
        arcpy.Merge_management(extractedFeats, extractPoly)
        arcpy.AddGeometryAttributes_management(
            extractPoly, "AREA_GEODESIC", "", areaUnit1
        )
        arcpy.AddMessage("merging done")

        # mosaic extracted rasters into a new raster
        mosaicRas = tempWS + "/" + "extracted_mosaic"
        interimDataList.append(mosaicRas)
        # setting up raster properties
        pixType = "8_BIT_UNSIGNED"
        descData = arcpy.Describe(bathyRas)

        extent = descData.Extent
        env.extent = extent

        outExtract = ExtractByMask(bathyRas, extractPoly)
        outExtract.save(mosaicRas)
        arcpy.AddMessage("mosaic done")

        # substract the mosaic from the input bathymetric grid
        bathyRas1 = bathyRas + "_1"
        interimDataList.append(bathyRas1)
        conDo = Con(IsNull(Raster(mosaicRas)), bathyRas)
        conDo.save(bathyRas1)
        arcpy.AddMessage("substract done")

        # calling the helper function to calculate LMI from the new bathy
        lmiRas = tempWS + "/" + "LMI_1"
        interimDataList.append(lmiRas)
        self.calculateLMI(bathyRas1, lmiWeightFile, lmiRas)

        # select areas with LMI >= lmiThreshold
        lmiSTDResult = arcpy.GetRasterProperties_management(lmiRas, "STD")
        lmiSTDText = lmiSTDResult.getOutput(0)
        if lmiSTDText.find(",") > 0:
            lmiSTDText = HelperFunctions.convertDecimalSeparator(lmiSTDText)
        lmiSTD = float(lmiSTDText)
        lmiMEANResult = arcpy.GetRasterProperties_management(lmiRas, "MEAN")
        lmiMeanText = lmiMEANResult.getOutput(0)
        if lmiMeanText.find(",") > 0:
            lmiMeanText = HelperFunctions.convertDecimalSeparator(lmiMeanText)
        lmiMean = float(lmiMeanText)
        lmiThreshold = lmiMean + float(lmiSTDScale) * lmiSTD
        arcpy.AddMessage("using LMI threshold " + str(lmiThreshold))
        lmiClassRas = tempWS + "/" + "LMI_1C"
        interimDataList.append(lmiClassRas)
        HelperFunctions.selectRaster(lmiRas, lmiClassRas, lmiThreshold, ">=")
        arcpy.AddMessage("LMI selection done")

        # convert selected areas to polygons
        lmiPoly = tempWS + "/" + "LMI_1C_poly"
        interimDataList.append(lmiPoly)
        arcpy.RasterToPolygon_conversion(lmiClassRas, lmiPoly, "NO_SIMPLIFY")
        arcpy.AddGeometryAttributes_management(lmiPoly, "AREA_GEODESIC", "", areaUnit1)
        arcpy.AddMessage("convert raster to polygon done")

        # select based on location
        # only select the features from the LMI methods if they interset with the second set of features from the TPI method
        lmiPoly_selected = tempWS + "/" + "LMI_1C_poly_selected"
        interimDataList.append(lmiPoly_selected)
        layerName2 = "lyr2"
        arcpy.MakeFeatureLayer_management(lmiPoly, layerName2)
        arcpy.SelectLayerByLocation_management(layerName2, "intersect", extractPoly)
        arcpy.CopyFeatures_management(layerName2, lmiPoly_selected)
        arcpy.AddMessage("select by location done")

        # use union analysis to merge the second set of features identified by the TPI methods and the features identified by the LMI method
        # This effectively expand the second set of features from the TPI method in their spatial dimensions
        inFeats = []
        inFeats.append(lmiPoly_selected)
        inFeats.append(extractPoly)
        unionFeat = tempWS + "/" + "unionFeat"
        interimDataList.append(unionFeat)
        # note that using "NO_GAPS" option is able to fill holes. This would be good to fill small holes. But it also would potentially fill data gaps that should be kept.
        # We therefore decide to use "GAPS" option
        arcpy.Union_analysis(inFeats, unionFeat, "ALL", "#", "GAPS")
        arcpy.AddMessage("union done")

        # further select areas based on the input area threshold
        extractPoly_selected = tempWS + "/" + "extracted_mosaic_poly_selected"
        interimDataList.append(extractPoly_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(extractPoly, extractPoly_selected, where_clause)
        arcpy.AddMessage("selection by area done")

        # use spatial join to join the attributes
        joinedFeat = tempWS + "/" + "unionFeat_joined"
        interimDataList.append(joinedFeat)
        arcpy.SpatialJoin_analysis(
            unionFeat,
            extractPoly_selected,
            joinedFeat,
            "JOIN_ONE_TO_ONE",
            "KEEP_ALL",
            "#",
            "INTERSECT",
        )
        arcpy.AddMessage("spatial join done")

        # dissolve the unioned features
        dissolvedFeat = tempWS + "/" + "unionFeat_joined_dissolved"
        interimDataList.append(dissolvedFeat)
        dissolveField = "gridcode_12"
        arcpy.Dissolve_management(
            joinedFeat, dissolvedFeat, dissolveField, "#", "SINGLE_PART"
        )
        arcpy.AddGeometryAttributes_management(
            dissolvedFeat, "AREA_GEODESIC", "", areaUnit1
        )
        arcpy.AddMessage("dissolve done")
        # The follwing codes are only needed for the second set that contains > 50 features
        if count > 50:
            # select based on location
            # only select the first set of features (from the TPI method) that donot overlap with the dissolved (second set) features
            tpiPoly1_selected1 = tempWS + "/" + "tpiC_poly_selected1"
            interimDataList.append(tpiPoly1_selected1)
            newLayerName = "lyrNew"
            arcpy.MakeFeatureLayer_management(tpiPoly1_selected, newLayerName)
            arcpy.SelectLayerByLocation_management(
                newLayerName, "intersect", dissolvedFeat, "#", "NEW_SELECTION", "INVERT"
            )
            arcpy.CopyFeatures_management(newLayerName, tpiPoly1_selected1)
            arcpy.AddMessage("select by location done")
            # merge
            mergedFeat = tempWS + "/" + "unionFeat_joined_dissolved_merged"
            interimDataList.append(mergedFeat)
            arcpy.Merge_management([tpiPoly1_selected1, dissolvedFeat], mergedFeat)

            mergedFeat1 = tempWS + "/" + "unionFeat_joined_dissolved_merged1"
            interimDataList.append(mergedFeat1)
            arcpy.MultipartToSinglepart_management(mergedFeat, mergedFeat1)
            arcpy.AddGeometryAttributes_management(
                mergedFeat1, "AREA_GEODESIC", "", areaUnit1
            )

        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/" + "unionFeat_joined_dissolved_eliminated"
        interimDataList.append(eliminatedFeat)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        layerName3 = "lyr3"
        if count > 50:  # if more than 50 features, uses the merged features
            arcpy.MakeFeatureLayer_management(mergedFeat1, layerName3)
        else:  # otherwise, uses the dissolved features
            arcpy.MakeFeatureLayer_management(dissolvedFeat, layerName3)
        arcpy.SelectLayerByAttribute_management(
            layerName3, "NEW_SELECTION", where_clause
        )
        arcpy.Eliminate_management(layerName3, eliminatedFeat, "AREA")
        arcpy.AddMessage("eliminate by area done")

        # delete features based on the area attribute
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        layerName4 = "lyr4"
        arcpy.MakeFeatureLayer_management(eliminatedFeat, layerName4)
        arcpy.SelectLayerByAttribute_management(
            layerName4, "NEW_SELECTION", where_clause
        )
        if int(arcpy.GetCount_management(layerName4)[0]) > 0:
            arcpy.DeleteFeatures_management(layerName4)
        arcpy.AddMessage("delete features by area done")

        # copy the resulted features to the output featureclass
        arcpy.Copy_management(eliminatedFeat, outFeat)

        # delete intermediate results
        if len(extractedFeats) > 0:
            for item in extractedFeats:
                interimDataList.append(item)
        HelperFunctions.deleteDataItems(interimDataList)
        HelperFunctions.deleteAllFields(outFeat)
        arcpy.AddMessage("TPI_LMI tool is done")

        return

    # This function calculates negative openness and uses it to identify Bathymetric High features
    def opennessHigh(
        self,
        tempWS,
        bathyRas,
        noRas,
        outFeat,
        areaThreshold,
        areaUnit,
        noRadius,
        noSTDScaleLarge,
        noSTDScaleSmall,
        messages,
    ):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # noRas: output negative openness grid
        # outFeat: output Bathymetric High features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # noRadius: input radius value of a circular window used to calculated negative openness
        # noSTDScaleLarge: first input negative openness threshold used to identify Bathymetric High features
        # noSTDScaleSmall: second input negative openness threshold used to identify Bathymetric High features
        # messages: to handle error messages
        arcpy.AddMessage("runing openness High tool ...")

        noRasName = noRas[noRas.rfind("/") + 1 :]

        noRas1 = tempWS + "/" + noRasName
        # If the negative openness raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate negative openness with a defined noRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(noRas1):
            arcpy.CopyRaster_management(noRas1, noRas)
            arcpy.AddMessage(noRas + " exists and will be used")
        elif noRadius == 0:  # you have to set the radius > 0
            arcpy.AddMessage(
                "You must provide a radius greater than 0 to calculate openness"
            )
            return
        else:  # call the helper function to calculate negative openness
            arcpy.AddMessage("calculating Negative Openness...")
            opennessParameter = "negativeOpenness"
            HelperFunctions.calculateOpenness(
                bathyRas, noRadius, opennessParameter, noRas, tempWS, messages
            )
        # copy the negative openness grid to a backup directory
        arcpy.CopyRaster_management(noRas, noRas1)

        interimDataList = []

        # The following codes are used to identify possible 'tops' (or 'peaks') or Bathymetry High features
        # The way doing that is to invert the bathymetry grid and then identify 'sink'

        bathyRas1 = tempWS + "/" + "tempBathy"
        interimDataList.append(bathyRas1)
        # invert the input bathymetry grid
        outM = Times(bathyRas, -1.0)
        outM.save(bathyRas1)
        # identify sinks
        fdRas = tempWS + "/" + "fdRas"
        interimDataList.append(fdRas)
        outFlowDirection = FlowDirection(bathyRas1)
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
        arcpy.RasterToPolygon_conversion(sinkRas, sinksPoly, "NO_SIMPLIFY")
        arcpy.AddMessage("convert sinks to polygon done")

        # select first set of areas (features) with no <= noThresholdLarge

        noSTDResult = arcpy.GetRasterProperties_management(noRas, "STD")
        noSTDText = noSTDResult.getOutput(0)
        if noSTDText.find(",") > 0:
            noSTDText = HelperFunctions.convertDecimalSeparator(noSTDText)
        noSTD = float(noSTDText)
        noMEANResult = arcpy.GetRasterProperties_management(noRas, "MEAN")
        noMeanText = noMEANResult.getOutput(0)
        if noMeanText.find(",") > 0:
            noMeanText = HelperFunctions.convertDecimalSeparator(noMeanText)
        noMean = float(noMeanText)
        noThresholdLarge = noMean - float(noSTDScaleLarge) * noSTD
        arcpy.AddMessage("using no threshold " + str(noThresholdLarge))
        noClassRas1 = tempWS + "/" + "no_C"
        HelperFunctions.selectRaster(noRas, noClassRas1, noThresholdLarge, "<=")
        interimDataList.append(noClassRas1)

        # select second set of areas (features) with no <= noThresholdSmall

        noThresholdSmall = noMean - float(noSTDScaleSmall) * noSTD
        arcpy.AddMessage("using no threshold " + str(noThresholdSmall))
        noClassRas2 = tempWS + "/" + "no_C1"
        HelperFunctions.selectRaster(noRas, noClassRas2, noThresholdSmall, "<=")
        interimDataList.append(noClassRas2)

        # convert selected areas to polygons
        noPoly1 = tempWS + "/" + "noC_poly"
        interimDataList.append(noPoly1)
        arcpy.RasterToPolygon_conversion(noClassRas1, noPoly1, "NO_SIMPLIFY")

        noPoly2 = tempWS + "/" + "noC1_poly"
        interimDataList.append(noPoly2)
        arcpy.RasterToPolygon_conversion(noClassRas2, noPoly2, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(noPoly1, "AREA_GEODESIC", "", areaUnit1)
        arcpy.AddGeometryAttributes_management(noPoly2, "AREA_GEODESIC", "", areaUnit1)

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)

        # further selection based on the input area threshold
        noPoly1_selected = tempWS + "/" + "noC_poly_selected"
        interimDataList.append(noPoly1_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(noPoly1, noPoly1_selected, where_clause)

        noPoly2_selected = tempWS + "/" + "noC1_poly_selected"
        interimDataList.append(noPoly2_selected)
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(noPoly2, noPoly2_selected, where_clause)

        # select based on location
        # select from the first set of features that contain 'tops'
        noPoly1_selected1 = tempWS + "/" + "noC_poly_selected1"
        interimDataList.append(noPoly1_selected1)
        layerName1 = "lyr1"
        arcpy.MakeFeatureLayer_management(noPoly1_selected, layerName1)
        arcpy.SelectLayerByLocation_management(layerName1, "contains", sinksPoly)
        arcpy.CopyFeatures_management(layerName1, noPoly1_selected1)
        arcpy.AddMessage("select by location done")
        # select from the second set of features that contain 'tops'
        noPoly2_selected1 = tempWS + "/" + "noC1_poly_selected1"
        interimDataList.append(noPoly2_selected1)
        layerName2 = "lyr2"
        arcpy.MakeFeatureLayer_management(noPoly2_selected, layerName2)
        arcpy.SelectLayerByLocation_management(layerName2, "contains", sinksPoly)
        arcpy.CopyFeatures_management(layerName2, noPoly2_selected1)
        arcpy.AddMessage("select by location done")

        # spatial join to join attributes

        joinedFeat = tempWS + "/" + "Feats_joined"
        interimDataList.append(joinedFeat)
        arcpy.SpatialJoin_analysis(
            noPoly2_selected1,
            noPoly1_selected1,
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
        arcpy.Select_analysis(joinedFeat, joinedFeat_selected, where_clause)
        arcpy.AddMessage("select by attribute done")
        # select based on location
        noPoly1_selected2 = tempWS + "/" + "noC_poly_selected2"
        interimDataList.append(noPoly1_selected2)
        layerName3 = "lyr3"
        arcpy.MakeFeatureLayer_management(noPoly1_selected1, layerName3)
        arcpy.SelectLayerByLocation_management(
            layerName3, "intersect", joinedFeat_selected
        )
        arcpy.CopyFeatures_management(layerName3, noPoly1_selected2)
        arcpy.AddMessage("select by location done")
        arcpy.AddMessage("first subset selection done")

        # If a feature from the second set intersects only one features from the first set, keep the feature from the second set
        joinedFeat_selected1 = tempWS + "/" + "Feats_joined_selected1"
        interimDataList.append(joinedFeat_selected1)
        where_clause = '"Join_Count" < 2'
        arcpy.Select_analysis(joinedFeat, joinedFeat_selected1, where_clause)
        arcpy.AddMessage("select by attribute done")
        arcpy.AddMessage("second subset selection done")

        # merge the two subsets of features to form the final set of Bathymetric High features
        mergedFeat = tempWS + "/" + "Feats_merged"
        interimDataList.append(mergedFeat)
        arcpy.Merge_management([noPoly1_selected2, joinedFeat_selected1], mergedFeat)
        arcpy.AddMessage("merge done")
        arcpy.Copy_management(mergedFeat, outFeat)

        # delete intermediate results
        HelperFunctions.deleteDataItems(interimDataList)
        HelperFunctions.deleteAllFields(outFeat)
        arcpy.AddMessage("Openness High tool is done")

    