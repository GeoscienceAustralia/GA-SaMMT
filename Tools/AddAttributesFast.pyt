"""
Author: Zhi Huang
Organisation: Geoscience Australia
Email: Zhi.Huang@ga.gov.au
Last update: June 04, 2024
Python version: 3+
ArcGIS Pro: 2.6.4 and above
"""

import math
import os
import sys
import arcpy
import pandas as pd
from arcpy import env
from arcpy.sa import *

import multiprocessing
from importlib import reload
import AddAttributesFunctions
from AddAttributesFunctions import execute_shape_BH
from AddAttributesFunctions import execute_shape_BL
from AddAttributesFunctions import execute_profile_BH
from AddAttributesFunctions import execute_profile_BL
import HelperFunctions

arcpy.CheckOutExtension("Spatial")


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "AddAttributesFast"

        # List of tool classes associated with this toolbox
        # There are four tools. Two for generating attributes for Bathymetric High features.
        # The other two for Bathymetric Low features.
        # The two tools are used to add two sets of attributes: shape attributes and profile attributes, in that order.
        self.tools = [
            Add_Shape_Attributes_High_Tool,
            Add_Shape_Attributes_Low_Tool,
            Add_Profile_Attributes_High_Tool,
            Add_Profile_Attributes_Low_Tool,
        ]


class Add_Shape_Attributes_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Shape Attributes High Tool Fast"
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

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Number of CPU processors used for multiprocessing",
            name="nCPU",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        # the default value is the total number of logical processors available in the computer
        param3.value = multiprocessing.cpu_count()

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
        nCPU = int(parameters[3].valueAsText)

        # calling the helper functions
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

        # check that the number of CPU processors must be greater than 1 and less than the maximum (default)
        if nCPU < 2:
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must be at least 2!"
            )
            raise arcpy.ExecuteError
        elif nCPU > multiprocessing.cpu_count():
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must not be greater than the maximum " +
                "that is available: " + str(multiprocessing.cpu_count()) + "!"
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

        # important, need to set the python.exe within ArcGIS Pro as the python set_executable
        # this will make sure the multiprocessing opens multiple python windows for processing
        # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
        # which would not process the task as expected.
        multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
        # call the splitFeat() to split the input featureclass into nCPU subsets, and create separate geodatabases and
        # temporary folders for multiprocessing
        workspaceList, tempfolderList, featList, bathyList = helper.splitFeat_BH(
            workspaceName, inFeatClass, inBathy, nCPU)
        # generate the argument list
        argList = []
        i = 0
        while i < len(featList):
            argList.append([workspaceList[i], tempfolderList[i], featList[i], bathyList[i]])
            i += 1

        # important, need to reload the module so that we use the most up-to-date coding in the module
        reload(AddAttributesFunctions)

        arcpy.AddMessage('Starting multiprocessing...')
        # call the execute() from the AddAttributesFunctions module
        # the function is the entry point for the multiprocessing
        execute_shape_BH(argList, nCPU)
        arcpy.AddMessage('multiprocessing Done.')
        # merge individual featureclass
        outFeatClass = "mergedFeat"
        arcpy.management.Merge(featList, outFeatClass)
        arcpy.AddMessage('merged done')
        # copy the merged features and replace the input featureclass
        arcpy.management.Copy(outFeatClass, inFeatClass)
        arcpy.management.Delete(outFeatClass)

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        # delete all temporary workspaces and folders
        for workspace in workspaceList:
            arcpy.management.Delete(workspace)
        arcpy.AddMessage("All temporary workspaces are deleted")

        for folder in tempfolderList:
            arcpy.management.Delete(folder)
        arcpy.AddMessage("All temporary folders are deleted")

        return


class Add_Shape_Attributes_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Shape Attributes Low Tool Fast"
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
            displayName="Output Head Features",
            name="headFeatClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Output Foot Features",
            name="footFeatClass",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Number of CPU processors used for multiprocessing",
            name="nCPU",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        # the default value is the total number of logical processors available in the computer
        param5.value = multiprocessing.cpu_count()

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
        headFeatClass = parameters[3].valueAsText
        footFeatClass = parameters[4].valueAsText
        nCPU = int(parameters[5].valueAsText)
        additionalOption = parameters[6].valueAsText

        # calling the helper functions
        helper = helpers()
        inFeatClass = HelperFunctions.convert_backslash_forwardslash(inFeatClass)
        inBathy = HelperFunctions.convert_backslash_forwardslash(inBathy)
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

        # check that the number of CPU processors must be greater than 1 and less than the maximum (default)
        if nCPU < 2:
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must be at least 2!"
            )
            raise arcpy.ExecuteError
        elif nCPU > multiprocessing.cpu_count():
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must not be greater than the maximum " +
                "that is available: " + str(multiprocessing.cpu_count()) + "!"
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

        # important, need to set the python.exe within ArcGIS Pro as the python set_executable
        # this will make sure the multiprocessing opens multiple python windows for processing
        # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
        # which would not process the task as expected.
        multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))

        # call the splitFeat() to split the input featureclass into nCPU subsets, and create separate geodatabases and
        # temporary folders for multiprocessing
        workspaceList, tempfolderList, featList, headFeatList, footFeatList, bathyList = helper.splitFeat_BL(
            workspaceName, inFeatClass, inBathy, nCPU)
        # generate the argument list
        argList = []
        i = 0
        while i < len(featList):
            argList.append([workspaceList[i], tempfolderList[i], featList[i], headFeatList[i],
                            footFeatList[i], bathyList[i], additionalOption])
            i += 1

        # important, need to reload the module so that we use the most up-to-date coding in the module
        reload(AddAttributesFunctions)

        arcpy.AddMessage('Starting multiprocessing...')
        # call the execute() from the AddAttributesFunctions module
        # the function is the entry point for the multiprocessing
        execute_shape_BL(argList, nCPU)
        arcpy.AddMessage('multiprocessing Done.')

        # merge individual featureclass
        outFeatClass = "mergedFeat"
        arcpy.management.Merge(featList, outFeatClass)
        outFeatClass1 = "mergedFeat1"
        arcpy.management.Merge(headFeatList, outFeatClass1)
        outFeatClass2 = "mergedFeat2"
        arcpy.management.Merge(footFeatList, outFeatClass2)
        arcpy.AddMessage('final merged done')
        # copy the merged features and replace the input featureclass
        arcpy.management.Copy(outFeatClass, inFeatClass)
        arcpy.management.Copy(outFeatClass1, headFeatClass)
        arcpy.management.Copy(outFeatClass2, footFeatClass)
        arcpy.AddMessage('final copied done')
        arcpy.management.Delete(outFeatClass)
        arcpy.management.Delete(outFeatClass1)
        arcpy.management.Delete(outFeatClass2)

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        # delete all temporary workspaces and folders
        for workspace in workspaceList:
            arcpy.management.Delete(workspace)
        arcpy.AddMessage("All temporary workspaces are deleted")

        for folder in tempfolderList:
            arcpy.management.Delete(folder)
        arcpy.AddMessage("All temporary folders are deleted")

        return


class Add_Profile_Attributes_High_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Profile Attributes High Tool Fast"
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

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Number of CPU processors used for multiprocessing",
            name="nCPU",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        # the default value is the total number of logical processors available in the computer
        param4.value = multiprocessing.cpu_count()

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
        nCPU = int(parameters[4].valueAsText)

        # calling the helper functions
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

        # check that the number of CPU processors must be greater than 1 and less than the maximum (default)
        if nCPU < 2:
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must be at least 2!"
            )
            raise arcpy.ExecuteError
        elif nCPU > multiprocessing.cpu_count():
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must not be greater than the maximum " +
                "that is available: " + str(multiprocessing.cpu_count()) + "!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0: inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True
        # areaThreshold input has two components: the threshold value and the area unit
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
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can run. "
                + "Please use Add Shape Attribute Tool to calculate the attribute"
            )
            raise arcpy.ExecuteError

        # important, need to set the python.exe within ArcGIS Pro as the python set_executable
        # this will make sure the multiprocessing opens multiple python windows for processing
        # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
        # which would not process the task as expected.
        multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
        # call the splitFeat() to split the input featureclass into nCPU subsets, and create separate geodatabases and
        # temporary folders for multiprocessing
        workspaceList, tempfolderList, featList, bathyList = helper.splitFeat_BH(workspaceName, inFeatClass, inBathy,
                                                                                 nCPU)
        # generate the argument list
        argList = []
        i = 0
        while i < len(featList):
            argList.append([workspaceList[i], tempfolderList[i], featList[i], bathyList[i], areaThreshold])
            i += 1

        # important, need to reload the module so that we use the most up-to-date coding in the module
        reload(AddAttributesFunctions)

        arcpy.AddMessage('Starting multiprocessing...')
        # call the execute() from the AddAttributesFunctions module
        # the function is the entry point for the multiprocessing
        execute_profile_BH(argList, nCPU)
        arcpy.AddMessage('multiprocessing Done.')
        # merge individual featureclass
        outFeatClass = "mergedFeat"
        arcpy.management.Merge(featList, outFeatClass)
        arcpy.AddMessage('merged done')
        # copy the merged features and replace the input featureclass
        arcpy.management.Copy(outFeatClass, inFeatClass)
        arcpy.management.Delete(outFeatClass)

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        # delete all temporary workspaces and folders
        for workspace in workspaceList:
            arcpy.management.Delete(workspace)
        arcpy.AddMessage("All temporary workspaces are deleted")

        for folder in tempfolderList:
            arcpy.management.Delete(folder)
        arcpy.AddMessage("All temporary folders are deleted")

        failedIDList = []
        cursor = arcpy.SearchCursor(inFeatClass)
        for row in cursor:
            profileShape = row.getValue("profileShape")
            featID = row.getValue("featID")
            if profileShape is None:
                failedIDList.append(featID)
        del row, cursor
        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        return


class Add_Profile_Attributes_Low_Tool:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Add Profile Attributes Low Tool Fast"
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

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Number of CPU processors used for multiprocessing",
            name="nCPU",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        # the default value is the total number of logical processors available in the computer
        param4.value = multiprocessing.cpu_count()

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
        nCPU = int(parameters[4].valueAsText)

        # calling the helper functions
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

        # check that the number of CPU processors must be greater than 1 and less than the maximum (default)
        if nCPU < 2:
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must be at least 2!"
            )
            raise arcpy.ExecuteError
        elif nCPU > multiprocessing.cpu_count():
            messages.addErrorMessage(
                "The number of CPU processors used for multiprocessing must not be greater than the maximum " +
                "that is available: " + str(multiprocessing.cpu_count()) + "!"
            )
            raise arcpy.ExecuteError

        workspaceName = inFeatClass[0: inFeatClass.rfind("/")]
        env.workspace = workspaceName
        env.overwriteOutput = True

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
                "Error! The input features need to have the LengthWidthRatio attribute before the tool can be run. "
                + "Please use Add Shape Attribute Tool to calculate the attribute"
            )
            raise arcpy.ExecuteError

        # important, need to set the python.exe within ArcGIS Pro as the python set_executable
        # this will make sure the multiprocessing opens multiple python windows for processing
        # without this line of code, the tool will open ArcGIS Pro applications (e.g., ArcGISPro.exe),
        # which would not process the task as expected.
        multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'python.exe'))
        # call the splitFeat() to split the input featureclass into nCPU subsets, and create separate geodatabases and
        # temporary folders for multiprocessing
        workspaceList, tempfolderList, featList, headFeatList, footFeatList, bathyList = helper.splitFeat_BL(
            workspaceName, inFeatClass, inBathy, nCPU)
        # generate the argument list
        argList = []
        i = 0
        while i < len(featList):
            argList.append([workspaceList[i], tempfolderList[i], featList[i], bathyList[i], areaThreshold])
            i += 1

        # important, need to reload the module so that we use the most up-to-date coding in the module
        reload(AddAttributesFunctions)

        arcpy.AddMessage('Starting multiprocessing...')
        # call the execute() from the AddAttributesFunctions module
        # the function is the entry point for the multiprocessing
        execute_profile_BL(argList, nCPU)
        arcpy.AddMessage('multiprocessing Done.')
        # merge individual featureclass
        outFeatClass = "mergedFeat"
        arcpy.management.Merge(featList, outFeatClass)
        arcpy.AddMessage('merged done')
        # copy the merged features and replace the input featureclass
        arcpy.management.Copy(outFeatClass, inFeatClass)
        arcpy.management.Delete(outFeatClass)

        # compact the geodatabase to reduce its size
        arcpy.management.Compact(workspaceName)
        arcpy.AddMessage("Compacted the geodatabase")

        # delete all temporary workspaces and folders
        for workspace in workspaceList:
            arcpy.management.Delete(workspace)
        arcpy.AddMessage("All temporary workspaces are deleted")

        for folder in tempfolderList:
            arcpy.management.Delete(folder)
        arcpy.AddMessage("All temporary folders are deleted")

        failedIDList = []
        cursor = arcpy.SearchCursor(inFeatClass)
        for row in cursor:
            profileShape = row.getValue("profileShape")
            featID = row.getValue("featID")
            if profileShape is None:
                failedIDList.append(featID)
        del row, cursor
        if len(failedIDList) > 0:
            arcpy.AddMessage("Failed on the following featID(s):" + str(failedIDList))
            arcpy.AddMessage("You may want to re-run only these features")

        return


# All the helper functions are defined here
class helpers:
   
    # This function creates temporary workspaces and folders,
    # splits the input bathymetric high featureclass into subsets,
    # and copies a subset and input bathymetry grid into each workspace
    def splitFeat_BH(self, workspace, inFeat, inBathy, noSplit):
        # workspace: input workspace
        # inFeat: input Bathymetric High feature
        # inBathy: input bathymetry grid
        # noSplit: the number of subsets to split the inFeat into

        noFeat = int(arcpy.management.GetCount(inFeat).getOutput(0))
        featCount = int(noFeat / noSplit)
        featList = []
        bathyList = []
        tempfolderList = []
        workspaceList = []
        path = workspace.rstrip(workspace.split('/')[-1])
        path = path.rstrip('/')
        baseName = workspace.split('/')[-1]
        baseName = baseName.split('.')[0]
		# modified on 20250522 to fix the issue when inBathy and inFeat are not in the same FileGeodatabase 
        inBathy1 = inBathy.split('/')[-1]
        inFeat = inFeat.split('/')[-1]
        arcpy.AddMessage(inBathy)

        i = 1
        while i <= noSplit:
            # create a File Geodatabase
            gdbName = baseName + str(i) + '.gdb'
            arcpy.management.CreateFileGDB(path, gdbName)
            arcpy.AddMessage(gdbName + ' created')

            workspace = path + '/' + gdbName
            workspaceList.append(workspace)

            # copy inBathy
			# modified on 20250522; inBathy is not neccessary from the same FileGeodatabase of the inFeat
            data1 = path + '/' + gdbName + '/' + inBathy1
            bathyList.append(data1)
            arcpy.management.Copy(inBathy, data1)
            arcpy.AddMessage(inBathy + ' copied')

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

            # create temp folder
            folderName = 'temp' + str(i)
            arcpy.management.CreateFolder(path, folderName)
            arcpy.AddMessage(folderName + ' created')
            tempFolder = path + '/' + folderName
            tempfolderList.append(tempFolder)
            i += 1
        return workspaceList, tempfolderList, featList, bathyList

    # This function creates temporary workspaces and folders,
    # splits the input bathymetric low featureclass into subsets,
    # copies a subset and input bathymetry grid into each workspace,
    # and specifies temporary head and foot featureclasses
    def splitFeat_BL(self, workspace, inFeat, inBathy, noSplit):
        # workspace: input workspace
        # inFeat: input bathymetric low featureclass
        # inBathy: input bathymetry grid
        # noSplit: the number of subsets to split the inFeat into

        noFeat = int(arcpy.management.GetCount(inFeat).getOutput(0))
        featCount = int(noFeat / noSplit)

        featList = []
        headFeatList = []
        footFeatList = []
        bathyList = []
        tempfolderList = []
        workspaceList = []

        path = workspace.rstrip(workspace.split('/')[-1])
        path = path.rstrip('/')
        baseName = workspace.split('/')[-1]
        baseName = baseName.split('.')[0]
		# modified on 20250522 to fix the issue when inBathy and inFeat are not in the same FileGeodatabase
        inBathy1 = inBathy.split('/')[-1]
        inFeat = inFeat.split('/')[-1]

        # loop through subsets
        i = 1
        while i <= noSplit:
            # create a File Geodatabase
            gdbName = baseName + str(i) + '.gdb'
            arcpy.management.CreateFileGDB(path, gdbName)
            arcpy.AddMessage(gdbName + ' created')

            workspace = path + '/' + gdbName
            workspaceList.append(workspace)

            # copy inBathy
			# modified on 20250522; inBathy is not neccessary from the same FileGeodatabase of the inFeat
            data1 = path + '/' + gdbName + '/' + inBathy1
            bathyList.append(data1)
            arcpy.management.Copy(inBathy, data1)
            arcpy.AddMessage(inBathy + ' copied')

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

            # create temp folder
            folderName = 'temp' + str(i)
            arcpy.management.CreateFolder(path, folderName)
            arcpy.AddMessage(folderName + ' created')
            tempFolder = path + '/' + folderName
            tempfolderList.append(tempFolder)
            # specify head and foot featureclass variables
            headFeat = outFeat + '_head'
            headFeatList.append(headFeat)
            footFeat = outFeat + '_foot'
            footFeatList.append(footFeat)

            i += 1
        return workspaceList, tempfolderList, featList, headFeatList, footFeatList, bathyList
