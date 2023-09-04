#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: August 15, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from arcpy.sa import *
import os
import math
import numpy as np
import warnings
from datetime import datetime 


class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "BathymetricHigh"

        # List of tool classes associated with this toolbox
        # There are three tools in this toolset used to map Bathymetric High features.
        self.tools = [TPITool,TPI_LMITool,Openness_High_Tool]

# TPITool uses Topographic Position Index (TPI) technique to map Bathymetric High features
class TPITool(object):
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
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output TPI Raster",
            name="tpiRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input")
               
        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="TPI Circle Radius (unit: cell)",
            name="tpiRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4.value = 3
        
        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="TPI STD Scale",
            name="tpiSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param5.value = 1.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="required",
            direction="Input")        
        param6.defaultEnvironmentName = "workspace"
        
        parameters = [param0, param1, param2, param3, param4, param5,param6]
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
                                  
        bathyRas = helper.convert_backslach_forwardslach(bathyRas)
        tpiRas = helper.convert_backslach_forwardslach(tpiRas)
        outFeat = helper.convert_backslach_forwardslach(outFeat)
        tempWS = helper.convert_backslach_forwardslach(tempWS)
        # if the input bathyRas is selected from a drop-down list, the bathyRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = helper.convert_backslach_forwardslach(lyr.dataSource)
        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
        rasFormat = rasDesc.format
        if rasFormat != 'FGDBR':
            messages.addErrorMessage("The input bathymetry raster must be a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError
        # check that the input bathymetry grid is in a projected coordinate system
        spatialReference = rasDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage("Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required!")
            raise arcpy.ExecuteError
        
        # check that the output TPI grid must be in a correct format
        if tpiRas.rfind(".gdb") == -1:
            messages.addErrorMessage("The output TPI raster must be nominated as a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage("The temporary workspace must be nominated as a File GeoDatabase!")
            raise arcpy.ExecuteError
        
        workspaceName = bathyRas[0:bathyRas.rfind("/")]
        workspaceName1 = tpiRas[0:tpiRas.rfind("/")]
        workspaceName2 = outFeat[0:outFeat.rfind("/")]
        
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit =  areaThreshold.split(" ")[1]
        # waterproof some unusal errors       
        if tpiRas == outFeat:
            messages.addErrorMessage("The output TPI raster and output Featureclass cannot have the same name in the same workspace!")
            raise arcpy.ExecuteError
            
        if (tempWS == workspaceName) or (tempWS == workspaceName1) or (tempWS == workspaceName2):
            messages.addErrorMessage("The temporary workspace must be different from the input/output workspace(s).")
            raise arcpy.ExecuteError
        
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError
  

        arcpy.env.workspace=workspaceName
        
        # call the helper function to calculate TPI and generate output Bathymetric High features
        helper.TPI_Tool(tempWS,bathyRas,tpiRas,outFeat,areaThresholdValue,areaUnit,tpiRadius,tpiSTDScale)
        
        return


# TPI_LMITool uses Topographic Position Index (TPI) technique and Local Moran I (LMI) technique to map Bathymetric High features    
class TPI_LMITool(object):
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
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output TPI Raster",
            name="tpiRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input")       
        
        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="TPI Circle Radius (unit: cell)",
            name="tpiRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4.value = 3
        
        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="TPI STD Scale Large",
            name="tpiSTDScaleLarge",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param5.value = 1.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="TPI STD Scale Small",
            name="tpiSTDScaleSmall",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param6.value = 0.5

        # eighth parameter
        param7 = arcpy.Parameter(
            displayName="LMI Weight File",
            name="lmiWeightFile",
            datatype="DEFile",
            parameterType="Required",
            direction="Input")
        param7.filter.list = ['txt']

        # nineth parameter
        param8 = arcpy.Parameter(
            displayName="LMI STD Scale",
            name="lmiSTDScale",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param8.value = 1.0

        # tenth parameter
        param9 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="required",
            direction="Input")        
        param9.defaultEnvironmentName = "workspace"
 
        
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

        bathyRas = helper.convert_backslach_forwardslach(bathyRas)
        tpiRas = helper.convert_backslach_forwardslach(tpiRas)
        outFeat = helper.convert_backslach_forwardslach(outFeat)
        tempWS = helper.convert_backslach_forwardslach(tempWS)

        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = helper.convert_backslach_forwardslach(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
        rasFormat = rasDesc.format
        if rasFormat != 'FGDBR':
            messages.addErrorMessage("The input bathymetry raster must be a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the input bathymetry grid is in a projected coordinate system
        spatialReference = rasDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage("Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required!")
            raise arcpy.ExecuteError
        
        # check that the output TPI grid must be in a correct format
        if tpiRas.rfind(".gdb") == -1:
            messages.addErrorMessage("The output TPI raster must be nominated as a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage("The temporary workspace must be nominated as a File GeoDatabase!")
            raise arcpy.ExecuteError
        
        workspaceName = bathyRas[0:bathyRas.rfind("/")]
        workspaceName1 = tpiRas[0:tpiRas.rfind("/")]
        workspaceName2 = outFeat[0:outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit =  areaThreshold.split(" ")[1]
        # waterproof some unusal errors       
        if tpiRas == outFeat:
            messages.addErrorMessage("The output TPI raster and output Featureclass cannot have the same name in the same workspace!")
            raise arcpy.ExecuteError
        if (tempWS == workspaceName) or (tempWS == workspaceName1) or (tempWS == workspaceName2):
            messages.addErrorMessage("The temporary workspace must be different from the input/output workspace(s).")
            raise arcpy.ExecuteError
        
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError
  

        arcpy.env.workspace=workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to calculate TPI and LMI and generate Bathymetric High features
        helper.TPI_LMI_Tool(tempWS,bathyRas,tpiRas,outFeat,areaThresholdValue,areaUnit,tpiRadius,tpiSTDScaleLarge,tpiSTDScaleSmall,lmiWeightFile,lmiSTDScale)
        
        return
# Openness_High_Tool uses Openness technique to map Bathymetric High features
class Openness_High_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Openness Tool Bathymetric High"
        self.description = "Cacluate Negative Openness and generate an output Featureclass"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetry Raster",
            name="bathyRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Negative Openness Raster",
            name="noRas",
            datatype="DERasterDataset",
            parameterType="Required",
            direction="Output")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input")       
        
        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Openness Circle Radius (unit: cell)",
            name="noRadius",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4.value = 3
        
        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="NO STD Scale Large",
            name="noSTDScaleLarge",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param5.value = 2.0

        # seventh parameter
        param6 = arcpy.Parameter(
            displayName="NO STD Scale Small",
            name="noSTDScaleSmall",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param6.value = 1.0

        # eighth parameter
        param7 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="required",
            direction="Input")        
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
 
        bathyRas = helper.convert_backslach_forwardslach(bathyRas)
        noRas = helper.convert_backslach_forwardslach(noRas)
        outFeat = helper.convert_backslach_forwardslach(outFeat)
        tempWS = helper.convert_backslach_forwardslach(tempWS)

        if bathyRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if bathyRas == lyr.name:
                        bathyRas = helper.convert_backslach_forwardslach(lyr.dataSource)
      
        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(bathyRas)
        rasFormat = rasDesc.format
        if rasFormat != 'FGDBR':
            messages.addErrorMessage("The input bathymetry raster must be a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the input bathymetry grid is in a projected coordinate system
        spatialReference = rasDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage("Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required!")
            raise arcpy.ExecuteError
        
        # check that the output TPI grid must be in a correct format
        if noRas.rfind(".gdb") == -1:
            messages.addErrorMessage("The output NO raster must be nominated as a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass must be in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the temporary workspace must be in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage("The temporary workspace must be nominated as a File GeoDatabase!")
            raise arcpy.ExecuteError
        
        workspaceName = bathyRas[0:bathyRas.rfind("/")]
        workspaceName1 = noRas[0:noRas.rfind("/")]
        workspaceName2 = outFeat[0:outFeat.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit =  areaThreshold.split(" ")[1]
        # waterproof some unusal errors       
        if noRas == outFeat:
            messages.addErrorMessage("The output Negative Openness raster and output Featureclass cannot have the same name in the same workspace!")
            raise arcpy.ExecuteError
        if (tempWS == workspaceName) or (tempWS == workspaceName1) or (tempWS == workspaceName2):
            messages.addErrorMessage("The temporary workspace must be different from the input/output workspace(s).")
            raise arcpy.ExecuteError
        
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError  

        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to calculate openness and generate Bathymetric High features
        helper.opennessHigh(tempWS,bathyRas,noRas,outFeat,areaThresholdValue,areaUnit,noRadius,noSTDScaleLarge,noSTDScaleSmall,messages)
        
        return                              
        
# helper functions are defined below
class helpers(object):
    # This function converts comma decimal separator (e.g., European standard) to dot (e.g.,US, UK and Australian standard)
    def convertDecimalSeparator(self,inText):
        # inText: input string representing a decimal number
        textList = inText.split(',')
        inText1 = textList[0] + '.' + textList[1]
        return inText1

    
    # This function converts backslach (accepted through the ArcGIS tool) to forwardslach (needed in python script) in a path
    def convert_backslach_forwardslach(self,inText):
        # inText: input path
        
        inText = fr"{inText}"
        if inText.find('\t'):
            inText = inText.replace('\t', '\\t')
        elif inText.find('\n'):
            inText = inText.replace('\n', '\\n')
        elif inText.find('\r'):
            inText = inText.replace('\r', '\\r')

        inText = inText.replace('\\','/')
        return inText
    
    # This function calculate TPI values from a bathymetry grid
    def calculateTPI(self,bathy,radius,tpiRas):
        # bathy: input bathymetry grid
        # radius: the input radius value of a circle window
        # tpiRas: output TPI grid
        
        time1 = datetime.now()
        neighborhood = NbrCircle(radius,"CELL")
        outFocal = FocalStatistics(bathy,neighborhood,"MEAN","DATA")
        # TPI equals to the difference between the value of the centre cell and the mean value of its neighbourhood
        outMinus = Minus(bathy, outFocal)
        outMinus.save(tpiRas)
        arcpy.AddMessage("TPI is done")
        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took "+str(diff)+" to generate TPI.")
        return

    # This function selects part of the raster based on a threshold value
    def selectRaster(self,inRas,outRas,threshold,sign,value = 1):
        # inRas: input raster
        # outRas: output raster
        # threshold: input threshold value used to select the inRas
        # sign: sign as part of the selection condition
        # value: the new raster value assigned to the part of the raster that satisfies the condition
        
        if sign == ">=":
            conDo = Con((Raster(inRas) >= threshold),value)
        elif sign == "<=":
            conDo = Con((Raster(inRas) <= threshold),value)
        conDo.save(outRas)

    # This function calculates LMI values from the bathymetry grid
    def calculateLMI(self,bathy,weightFile,lmiRas):
        # bathy: input bathymetry grid
        # weightFile: the path to the weight kernal file defining a neighbourhood
        # lmiRas: output LMI grid

        # spatial mean of the bathymetry grid
        meanResult = arcpy.GetRasterProperties_management(bathy, "MEAN")
        meanText = meanResult.getOutput(0)
        if meanText.find(',') > 0:
            meanText = self.convertDecimalSeparator(meanText)
        # spatial standard deviation of the bathymetry grid
        stdResult = arcpy.GetRasterProperties_management(bathy, "STD")
        stdText = stdResult.getOutput(0)
        if stdText.find(',') > 0:
            stdText = self.convertDecimalSeparator(stdText)
        NbrWeight1 = NbrWeight(weightFile)
        # the LMI algorithm
        outFocal = FocalStatistics(Minus(bathy, float(meanText)), NbrWeight1, "SUM", "DATA")
        outRas = Times(Divide(Minus(bathy, float(meanText)),Square(float(stdText))),outFocal)
        outRas.save(lmiRas)
        arcpy.AddMessage("local moran i done")
        return
    # This function extract input features from the bathymetry grid
    def extractMask(self,tempWS,bathy,inFeat,STDScale = 0):
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
            arcpy.AddMessage(str(polyID) + ';' + str(idV))
            whereClause = '"OBJECTID" = ' + str(polyID)
            arcpy.Select_analysis(inFeat,temp1,whereClause)
            extractedRas = tempWS + "/" + "extract_" + str(polyID)
            if arcpy.Exists(extractedRas):
                arcpy.Delete_management(extractedRas)
            # extract bathymetry grid for the area covered by the input feature
            outMask1 = ExtractByMask(bathy,temp1)
            outMask1.save(extractedRas)
            # select proportion of the extracted raster with a condition (.= Threshold)
            extractedRas1 = tempWS + "/" + "extract_" + str(polyID) + "_1"
            if arcpy.Exists(extractedRas1):
                arcpy.Delete_management(extractedRas1)
            STDResult = arcpy.GetRasterProperties_management(extractedRas, "STD")
            stdText = STDResult.getOutput(0)
            if stdText.find(',') > 0:
                stdText = self.convertDecimalSeparator(stdText)
            STD = float(stdText)
            MEANResult = arcpy.GetRasterProperties_management(extractedRas, "MEAN")
            meanText = MEANResult.getOutput(0)
            if meanText.find(',') > 0:
                meanText = self.convertDecimalSeparator(meanText)
            Mean = float(meanText)
            MAXResult = arcpy.GetRasterProperties_management(extractedRas, "MAXIMUM")
            maxText = MAXResult.getOutput(0)
            if maxText.find(',') > 0:
                maxText = self.convertDecimalSeparator(maxText)
            Max = float(maxText)            

            Threshold = Mean + STDScale*STD
            if Threshold >= Max:
                arcpy.AddMessage("You must provide a threhold smaller than the maximum value, reset to the mean value")
                Threshold = Mean
            self.selectRaster(extractedRas,extractedRas1,Threshold,">=",idV) 
       
            # convert selected areas to polygons
            extractedFeat = extractedRas1 + "_poly"
            arcpy.RasterToPolygon_conversion(extractedRas1, extractedFeat, "NO_SIMPLIFY", "VALUE","MULTIPLE_OUTER_PART")
            inFeats.append(extractedFeat)
            arcpy.Delete_management(temp1)
            arcpy.Delete_management(extractedRas)
            arcpy.Delete_management(extractedRas1)
        del row, cursor    

        return inFeats

    # This function deletes all intermediate data items
    def deleteDataItems(self,inDataList):
        # inDataList: a list of data items to be deleted
        
        if len(inDataList) == 0:
            arcpy.AddMessage("no data item in the list")
            
        else:
            for item in inDataList:
                arcpy.AddMessage("Deleting " + item)
                arcpy.Delete_management(item)
        return

    # This function deletes all unnecessary fields from the input featureclass
    def deleteFields(self,inFeat):
        # inFeat: input featureclass
        fields = arcpy.ListFields(inFeat)        
        fieldList = []
        for field in fields:
            if not field.required:
                fieldList.append(field.name)
        arcpy.DeleteField_management(inFeat,fieldList)        
            
        
    
    # This function adds a featID field with unique ID values
    def addIDField(self,inFeat,fieldName):
        # inFeat: input featureclass (or table)       
        # fieldName: the field in the inFeat to be calculated from the joinFeat        
        
        fieldType = "LONG"
        fieldPrecision = 15
        

        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:
            arcpy.AddField_management(inFeat,fieldName,fieldType,fieldPrecision)

        expression = "!OBJECTID!"

        arcpy.CalculateField_management(inFeat, fieldName, expression, "PYTHON_9.3")
        
        arcpy.AddMessage(fieldName + " added and calculated")
        return

    # This function calculates a converter value for the input area unit. The base unit is "SquareKilometers".
    def areaUnitConverter(self,inAreaUnit):
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
    def calculateOpenness(self,bathyRas,radius,opennessParameter,outRas,tempWS,messages):
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
        radius1 = int(np.round(radius/np.sqrt(2)))

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
            messages.addErrorMessage('    *** Coordinate system of input bathymetry grid is Geographic. A projected coordinate system is required. ***')
            raise arcpy.ExecuteError
        pnt = arcpy.Point(xmin,ymin)

        # Load DEM into numpy float32 array
        rasterDEMArray = arcpy.RasterToNumPyArray(bathyRas)

        # Check window size
        if radius > rasterDEMArray.shape[-1]:
            messages.addErrorMessage('    *** Analysis window is too long. ***')
            raise arcpy.ExecuteError

        #   calculate elevation angles within roughly circular search window (clockwise from N=0º)
        outShape = rasterDEMArray.shape

        outArray = np.zeros(outShape, dtype=np.float32)
        # the new array extends the loaded DEM array with a width of the radius from all four borders, so that the border areas of the loaded DEM can be processed properly
        rasterDEMArray1 = np.arange((rasterDEMArray.shape[0]+2*radius)*(rasterDEMArray.shape[1]+2*radius)).reshape(rasterDEMArray.shape[0]+2*radius,rasterDEMArray.shape[1]+2*radius)
        rasterDEMArray1 = np.zeros_like(rasterDEMArray1,dtype=float)
        rasterDEMArray1[:] = np.nan
        rasterDEMArray1[radius:rasterDEMArray.shape[0]+radius,radius:rasterDEMArray.shape[1]+radius]=rasterDEMArray
        del(rasterDEMArray) # to release memory
        #   set temporal arrays
        tempArray = np.zeros_like(outArray)
        # arrayList holds the temporal arrays, so that we can calculate np.nanmean() 
        arrayList = []
        shiftsList = [(x,y) for x in range(-radius,radius+1) for y in range(-radius,radius+1)]
        #   calculate elevation angles within roughly circular search window (clockwise from N=0º)
        for direction in range(0, 360, 45):
            if direction == 0:
                shiftsListD = filter (lambda arr: arr[0] < 0 and arr[1] == 0, shiftsList)
            elif direction == 45:
                shiftsListD = filter (lambda arr: arr[1] < radius1+1 and arr[0] == -arr[1] and arr[1] > 0, shiftsList)
            elif direction == 90:
                shiftsListD = filter (lambda arr: arr[0] == 0 and arr[1] > 0, shiftsList)
            elif direction == 135:
                shiftsListD = filter (lambda arr: arr[1] < radius1+1 and arr[0] == arr[1] and arr[0] > 0, shiftsList)
            elif direction == 180:
                shiftsListD = filter (lambda arr: arr[0] > 0 and arr[1] == 0, shiftsList)
            elif direction == 225:
                shiftsListD = filter (lambda arr: arr[0] < radius1+1 and arr[0] == -arr[1] and arr[0] > 0, shiftsList)
            elif direction == 270:
                shiftsListD = filter (lambda arr: arr[0] == 0 and arr[1] < 0, shiftsList)
            elif direction == 315:
                shiftsListD = filter (lambda arr: -arr[1] < radius1+1 and arr[0] == arr[1] and arr[0] < 0, shiftsList)

            if opennessParameter == 'positiveOpenness': # calculate positive openness
                tempArray.fill(-9999.9)
                for dx,dy in shiftsListD:           
                    xstop = -radius+dx or None
                    ystop = -radius+dy or None
                    angleArray = (rasterDEMArray1[radius+dx:xstop, radius+dy:ystop] - rasterDEMArray1[radius:-radius, radius:-radius]) / (math.hypot(dx, dy) * cellSize)
                    angleArray[np.isnan(angleArray)] = -999999.9
                    tempArray = np.maximum(tempArray, angleArray)
                tempArray = np.where(tempArray < -9999,np.nan,tempArray)
                arrayList.append(90 - np.degrees(np.arctan(tempArray)))
            elif opennessParameter == 'negativeOpenness': # calculate negative openness
                tempArray.fill(9999.9)
                for dx,dy in shiftsListD:
                    xstop = -radius+dx or None
                    ystop = -radius+dy or None
                    angleArray = (rasterDEMArray1[radius+dx:xstop, radius+dy:ystop] - rasterDEMArray1[radius:-radius, radius:-radius]) / (math.hypot(dx, dy) * cellSize)
                    angleArray[np.isnan(angleArray)] = -999999.9
                    tempArray = np.minimum(tempArray, angleArray)
                tempArray = np.where(tempArray < -9999,np.nan,tempArray)
                arrayList.append(90 + np.degrees(np.arctan(tempArray)))
        del(rasterDEMArray1) # to release memory
        del(tempArray) # to release memory
        
        # np.stack() requires numpy version 1.10.0 or higher
        stacked_array = np.stack(arrayList)
        with warnings.catch_warnings():
            # ignore runtime warning
            warnings.simplefilter("ignore",category=RuntimeWarning)
            outArray = np.nanmean(stacked_array,axis=0)
        
        # Create new output calculated raster, set spatial coordinates and save
        # if the raster is more than 5000 cells in either X or Y directions, split the raster into blocks
        blocksize = 5000
        if (width <= blocksize) and (height <= blocksize):
            newRaster = arcpy.NumPyArrayToRaster(outArray,pnt,cellSize,cellSize,-9999)
            if spatialReference.name != 'Unknown':
                arcpy.DefineProjection_management(newRaster, spatialReference)
            # Set nodata where nodata in the input DEM
            newRaster = SetNull(IsNull(bathyRas),newRaster)
            newRaster.save(outRas)
            del(outArray)
        else:            
            itemList = []
            xList = []
            yList = []
            for x in range(0,width,blocksize):
                xList.append(x)
            for y in range(0,height,blocksize):
                yList.append(y)
            xList.append(width)
            yList.append(height)

            i = 0
            j = len(yList)-1
            k = 0
            while i < len(xList)-1:
                while j > 0:
                    arr = outArray[yList[j-1]:yList[j],xList[i]:xList[i+1]]
                    hh = arr.shape[0]
                    ww = arr.shape[1]
                    pnt = arcpy.Point(xmin,ymin)
                    newRaster = arcpy.NumPyArrayToRaster(arr,pnt,cellSize,cellSize,-9999)
                    ras = tempWS + '/' + 'tempRas' + str(k)
                    itemList.append(ras)
                    newRaster.save(ras)
                    if spatialReference.name != 'Unknown':
                        arcpy.DefineProjection_management(ras, spatialReference)
                    ymin = ymin+hh*cellSize

                    j -= 1
                    k += 1
                xmin = xmin+ww*cellSize
                i += 1
                j = len(yList)-1
                ymin = extent.YMin

            del(outArray) # release memory
            tempRaster =  'tempRaster'
            
            arcpy.MosaicToNewRaster_management(itemList,tempWS, tempRaster, bathyRas, "32_BIT_FLOAT", "#", "1", "FIRST","FIRST")
            itemList.append(tempWS + '/' + tempRaster)
            
            # Set nodata where nodata in the input DEM
            newRaster = SetNull(IsNull(bathyRas),tempWS + '/' + tempRaster)
            newRaster.save(outRas)
            self.deleteDataItems(itemList)
            

        time2 = datetime.now()
        diff = time2 - time1
        arcpy.AddMessage("took "+str(diff)+" to generate openness.")
        return

    # This function calculates TPI and uses TPI threshold to identify Bathymetric High features
    def TPI_Tool(self,tempWS,bathyRas,tpiRas,outFeat,areaThreshold,areaUnit,tpiRadius,tpiSTDScale):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # tpiRas: output TPI grid
        # outFeat: output Bathymetric High features
        # areaThreshold: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # tpiRadius: input radius value of a circular window used to calculated TPI
        # tpiSTDScale: input TPI threshold used to identify Bathymetric High features
        
        arcpy.AddMessage("running TPI tool ...")

        tpiRasName = tpiRas[tpiRas.rfind("/")+1:]
        tpiRas1 = tempWS + "/" + tpiRasName
        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.Copy_management(tpiRas1,tpiRas)
            arcpy.AddMessage(tpiRas+' exists and will be used')
        elif tpiRadius == 0: # you have to set a radius greater than 0
            arcpy.AddMessage("You must provide a radius greater than 0 to calculate TPI")
            return
        else: # calling the helper function to calculate TPI
            arcpy.AddMessage("calculating TPI...")        
            self.calculateTPI(bathyRas,tpiRadius,tpiRas)
        # copy the TPI raster to a backup directory
        arcpy.Copy_management(tpiRas,tpiRas1)

        # obtain spatial mean and spatial standard deviation of the TPI grid
        tpiSTDResult = arcpy.GetRasterProperties_management(tpiRas, "STD")
        stdText = tpiSTDResult.getOutput(0) 
        if stdText.find(',') > 0:            
            stdText = self.convertDecimalSeparator(stdText)
            
        tpiSTD = float(stdText)
        tpiMEANResult = arcpy.GetRasterProperties_management(tpiRas, "MEAN")
        meanText = tpiMEANResult.getOutput(0)
        if meanText.find(',') > 0:
            meanText = self.convertDecimalSeparator(stdText)
        tpiMean = float(meanText)
        # define the TPI threshold value for the subsequent mapping
        tpiThreshold = tpiMean + float(tpiSTDScale)*tpiSTD        
        arcpy.AddMessage("using tpi threshold "+str(tpiThreshold))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        # select areas that satisfy the threshold condition
        self.selectRaster(tpiRas,tpiClassRas1,tpiThreshold,">=")
        
        # convert selected areas to polygons
        tpiPoly1 = tempWS + "/" + "tpiC_poly"
        arcpy.RasterToPolygon_conversion(tpiClassRas1, tpiPoly1, "NO_SIMPLIFY")
        arcpy.AddMessage("convert raster to polygon done")

        # add the "AREA_GEO" field to the polygons
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(tpiPoly1,"AREA_GEODESIC","",areaUnit1)
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = self.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThreshold)
        arcpy.AddMessage(str(areaThreshold))
        
        # further select areas based on the input area threshold       
        where_clause = '"AREA_GEO" >= ' + str(areaThreshold)
        arcpy.Select_analysis(tpiPoly1, outFeat, where_clause)
        arcpy.AddMessage("selection by area done")
        
        arcpy.Delete_management(tpiPoly1)
        arcpy.Delete_management(tpiClassRas1)  
        self.deleteFields(outFeat)
        arcpy.AddMessage("TPI tool is done")
        return

    # This function calculates TPI and LMI and uses them to identify Bathymetric High features
    def TPI_LMI_Tool(self,tempWS,bathyRas,tpiRas,outFeat,areaThreshold,areaUnit,tpiRadius,tpiSTDScaleLarge,tpiSTDScaleSmall,lmiWeightFile,lmiSTDScale):
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
        
        tpiRasName = tpiRas[tpiRas.rfind("/")+1:]
        tpiRas1 = tempWS + "/" + tpiRasName
        
        # If the TPI raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate TPI with a defined tpiRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(tpiRas1):
            arcpy.Copy_management(tpiRas1,tpiRas)
            arcpy.AddMessage(tpiRas+' exists and will be used')
        elif tpiRadius == 0: # you have to set a radius greater than 0
            arcpy.AddMessage("You must provide a radius greater than 0 to calculate TPI")
            return
        else: # calling the helper function to calculate TPI
            arcpy.AddMessage("calculating TPI...")        
            self.calculateTPI(bathyRas,tpiRadius,tpiRas)
        # copy the TPI raster to a backup directory
        arcpy.Copy_management(tpiRas,tpiRas1)
        
        interimDataList = []

        # obtain spatial mean and standard deviation of the TPI raster
        # select first set of areas (features) with TPI >= tpiThresholdLarge       
        # obtain spatial mean and spatial standard deviation of the TPI grid
        tpiSTDResult = arcpy.GetRasterProperties_management(tpiRas, "STD")
        stdText = tpiSTDResult.getOutput(0)
        if stdText.find(',') > 0:
            stdText = self.convertDecimalSeparator(stdText)
        tpiSTD = float(stdText)
        tpiMEANResult = arcpy.GetRasterProperties_management(tpiRas, "MEAN")
        meanText = tpiMEANResult.getOutput(0)
        if meanText.find(',') > 0:
            meanText = self.convertDecimalSeparator(stdText)
        tpiMean = float(meanText)
        tpiThresholdLarge = tpiMean + float(tpiSTDScaleLarge)*tpiSTD        
        arcpy.AddMessage("using tpi threshold " + str(tpiThresholdLarge))
        tpiClassRas1 = tempWS + "/" + "tpiC"
        interimDataList.append(tpiClassRas1)
        self.selectRaster(tpiRas,tpiClassRas1,tpiThresholdLarge,">=")
        
        # select second set of areas (features) with TPI >= tpiThresholdSmall           
        tpiThresholdSmall = tpiMean + float(tpiSTDScaleSmall)*tpiSTD        
        arcpy.AddMessage("using tpi threshold " + str(tpiThresholdSmall))
        tpiClassRas2 = tempWS + "/" + "tpiC1"
        interimDataList.append(tpiClassRas2)
        self.selectRaster(tpiRas,tpiClassRas2,tpiThresholdSmall,">=")
        
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
        arcpy.AddGeometryAttributes_management(tpiPoly1,"AREA_GEODESIC","",areaUnit1)
        arcpy.AddGeometryAttributes_management(tpiPoly2,"AREA_GEODESIC","",areaUnit1)
        
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = self.areaUnitConverter(areaUnit)
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
        arcpy.SelectLayerByLocation_management(layerName1, "intersect", tpiPoly1_selected)
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
        if count > 50: # If more than 50 features in the second set, we will only work on the 50 largest features to save time
            arcpy.AddMessage("there are " + str(count) + " features in " + tpiPoly2_selected1 + "; only 50 largest polygons will be processed for the next several steps")
            sortFeat = tempWS + "/" + "tpiC1_poly_selected1_sorted"
            interimDataList.append(sortFeat)
            sort_field = [["AREA_GEO", "DESCENDING"]]
            arcpy.Sort_management(tpiPoly2_selected1,sortFeat,sort_field)
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
            extractedFeats = self.extractMask(tempWS,bathyRas,tpiPoly2_selected1_1)
        else: # if less than 50 features in total
            # calling the helper function to extract rasters from the bathymetry data one by one based on the selected polygons above
            # for each extracted raster, select area with value >= threshold
            extractedFeats = self.extractMask(tempWS,bathyRas,tpiPoly2_selected1)


        arcpy.AddMessage("extract done")
        # merge inFeats resulted from the extractMask function
        extractPoly = tempWS + "/" + "extracted_merged"
        interimDataList.append(extractPoly)
        arcpy.Merge_management(extractedFeats,extractPoly)
        arcpy.AddGeometryAttributes_management(extractPoly,"AREA_GEODESIC","",areaUnit1)
        arcpy.AddMessage("merging done")

        # mosaic extracted rasters into a new raster
        mosaicRas = tempWS + "/" + "extracted_mosaic"
        interimDataList.append(mosaicRas)
        # setting up raster properties
        pixType = "8_BIT_UNSIGNED"
        descData = arcpy.Describe(bathyRas)

        extent = descData.Extent
        env.extent = extent


        outExtract = ExtractByMask(bathyRas,extractPoly)
        outExtract.save(mosaicRas)
        arcpy.AddMessage("mosaic done")

        # substract the mosaic from the input bathymetric grid
        bathyRas1 = bathyRas + "_1"
        interimDataList.append(bathyRas1)
        conDo = Con(IsNull(Raster(mosaicRas)),bathyRas)
        conDo.save(bathyRas1)
        arcpy.AddMessage("substract done")

        # calling the helper function to calculate LMI from the new bathy
        lmiRas = tempWS + "/" + "LMI_1"
        interimDataList.append(lmiRas)
        self.calculateLMI(bathyRas1,lmiWeightFile,lmiRas)

        # select areas with LMI >= lmiThreshold            
        lmiSTDResult = arcpy.GetRasterProperties_management(lmiRas, "STD")
        lmiSTDText = lmiSTDResult.getOutput(0)
        if lmiSTDText.find(',') > 0:
            lmiSTDText = self.convertDecimalSeparator(lmiSTDText)
        lmiSTD = float(lmiSTDText)
        lmiMEANResult = arcpy.GetRasterProperties_management(lmiRas, "MEAN")
        lmiMeanText = lmiMEANResult.getOutput(0)
        if lmiMeanText.find(',') > 0:
            lmiMeanText = self.convertDecimalSeparator(lmiMeanText)
        lmiMean = float(lmiMeanText)
        lmiThreshold = lmiMean + float(lmiSTDScale)*lmiSTD
        arcpy.AddMessage("using LMI threshold " + str(lmiThreshold))
        lmiClassRas = tempWS + "/" + "LMI_1C"
        interimDataList.append(lmiClassRas)
        self.selectRaster(lmiRas,lmiClassRas,lmiThreshold,">=")
        arcpy.AddMessage("LMI selection done")

        # convert selected areas to polygons
        lmiPoly = tempWS + "/" + "LMI_1C_poly"
        interimDataList.append(lmiPoly)
        arcpy.RasterToPolygon_conversion(lmiClassRas, lmiPoly, "NO_SIMPLIFY")
        arcpy.AddGeometryAttributes_management(lmiPoly,"AREA_GEODESIC","",areaUnit1)
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
        arcpy.Union_analysis(inFeats,unionFeat,"ALL","#","GAPS") 
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
        arcpy.SpatialJoin_analysis(unionFeat,extractPoly_selected,joinedFeat,"JOIN_ONE_TO_ONE","KEEP_ALL","#","INTERSECT")
        arcpy.AddMessage("spatial join done")

        # dissolve the unioned features
        dissolvedFeat = tempWS + "/" + "unionFeat_joined_dissolved"
        interimDataList.append(dissolvedFeat)
        dissolveField = "gridcode_12"
        arcpy.Dissolve_management(joinedFeat,dissolvedFeat,dissolveField,"#","SINGLE_PART")
        arcpy.AddGeometryAttributes_management(dissolvedFeat,"AREA_GEODESIC","",areaUnit1)
        arcpy.AddMessage("dissolve done")
        # The follwing codes are only needed for the second set that contains > 50 features
        if count > 50:
            # select based on location
            # only select the first set of features (from the TPI method) that donot overlap with the dissolved (second set) features
            tpiPoly1_selected1 = tempWS + "/" + "tpiC_poly_selected1"
            interimDataList.append(tpiPoly1_selected1)
            newLayerName = "lyrNew"
            arcpy.MakeFeatureLayer_management(tpiPoly1_selected, newLayerName)
            arcpy.SelectLayerByLocation_management(newLayerName, "intersect", dissolvedFeat, "#", "NEW_SELECTION", "INVERT")
            arcpy.CopyFeatures_management(newLayerName, tpiPoly1_selected1)
            arcpy.AddMessage("select by location done")
            # merge
            mergedFeat = tempWS + "/" + "unionFeat_joined_dissolved_merged"
            interimDataList.append(mergedFeat)
            arcpy.Merge_management([tpiPoly1_selected1,dissolvedFeat],mergedFeat)
            
            mergedFeat1 = tempWS + "/" + "unionFeat_joined_dissolved_merged1"
            interimDataList.append(mergedFeat1)
            arcpy.MultipartToSinglepart_management(mergedFeat,mergedFeat1)
            arcpy.AddGeometryAttributes_management(mergedFeat1,"AREA_GEODESIC","",areaUnit1)
            

        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/" + "unionFeat_joined_dissolved_eliminated"
        interimDataList.append(eliminatedFeat)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        layerName3 = "lyr3"
        if count > 50: # if more than 50 features, uses the merged features
            arcpy.MakeFeatureLayer_management(mergedFeat1, layerName3)
        else: # otherwise, uses the dissolved features
            arcpy.MakeFeatureLayer_management(dissolvedFeat, layerName3)
        arcpy.SelectLayerByAttribute_management(layerName3, "NEW_SELECTION", where_clause)
        arcpy.Eliminate_management(layerName3,eliminatedFeat,"AREA")
        arcpy.AddMessage("eliminate by area done")

        # delete features based on the area attribute
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        layerName4 = "lyr4"
        arcpy.MakeFeatureLayer_management(eliminatedFeat, layerName4)
        arcpy.SelectLayerByAttribute_management(layerName4, "NEW_SELECTION", where_clause)
        if int(arcpy.GetCount_management(layerName4)[0]) > 0:
            arcpy.DeleteFeatures_management(layerName4)
        arcpy.AddMessage("delete features by area done")

        # copy the resulted features to the output featureclass
        arcpy.Copy_management(eliminatedFeat,outFeat)

        # delete intermediate results
        if len(extractedFeats) > 0:
            for item in extractedFeats:
                interimDataList.append(item)
        self.deleteDataItems(interimDataList)
        self.deleteFields(outFeat)
        arcpy.AddMessage("TPI_LMI tool is done")

        return

    # This function calculates negative openness and uses it to identify Bathymetric High features
    def opennessHigh(self,tempWS,bathyRas,noRas,outFeat,areaThreshold,areaUnit,noRadius,noSTDScaleLarge,noSTDScaleSmall,messages):
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

        noRasName = noRas[noRas.rfind("/")+1:]
        
        noRas1 = tempWS + "/" + noRasName
        # If the negative openness raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate negative openness with a defined noRadius only once,
        # as the calculation may takes a long time depending on the radius value and the size of the bathymetric grid.
        if arcpy.Exists(noRas1):
            arcpy.CopyRaster_management(noRas1,noRas)
            arcpy.AddMessage(noRas+' exists and will be used')
        elif noRadius == 0: # you have to set the radius > 0
            arcpy.AddMessage("You must provide a radius greater than 0 to calculate openness")
            return
        else: # call the helper function to calculate negative openness
            arcpy.AddMessage("calculating Negative Openness...")
            opennessParameter = 'negativeOpenness'
            self.calculateOpenness(bathyRas, noRadius, opennessParameter, noRas, tempWS,messages)
        # copy the negative openness grid to a backup directory
        arcpy.CopyRaster_management(noRas,noRas1)
        
        interimDataList = []

        # The following codes are used to identify possible 'tops' (or 'peaks') or Bathymetry High features
        # The way doing that is to invert the bathymetry grid and then identify 'sink'
        
        bathyRas1 = tempWS + "/" + "tempBathy"
        interimDataList.append(bathyRas1)
        # invert the input bathymetry grid
        outM = Times(bathyRas,-1.0)
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
        if noSTDText.find(',') > 0:
            noSTDText = self.convertDecimalSeparator(noSTDText)
        noSTD = float(noSTDText)
        noMEANResult = arcpy.GetRasterProperties_management(noRas, "MEAN")
        noMeanText = noMEANResult.getOutput(0)
        if noMeanText.find(',') > 0:
            noMeanText = self.convertDecimalSeparator(noMeanText)
        noMean = float(noMeanText)
        noThresholdLarge = noMean - float(noSTDScaleLarge)*noSTD        
        arcpy.AddMessage("using no threshold " + str(noThresholdLarge))
        noClassRas1 = tempWS + "/" + "no_C"
        self.selectRaster(noRas,noClassRas1,noThresholdLarge,"<=")
        interimDataList.append(noClassRas1)

        # select second set of areas (features) with no <= noThresholdSmall
           
        noThresholdSmall = noMean - float(noSTDScaleSmall)*noSTD        
        arcpy.AddMessage("using no threshold " + str(noThresholdSmall))
        noClassRas2 = tempWS + "/" + "no_C1"
        self.selectRaster(noRas,noClassRas2,noThresholdSmall,"<=")
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
        arcpy.AddGeometryAttributes_management(noPoly1,"AREA_GEODESIC","",areaUnit1)
        arcpy.AddGeometryAttributes_management(noPoly2,"AREA_GEODESIC","",areaUnit1)

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = self.areaUnitConverter(areaUnit)
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
        arcpy.SpatialJoin_analysis(noPoly2_selected1,noPoly1_selected1,joinedFeat,"JOIN_ONE_TO_ONE","KEEP_ALL","#","INTERSECT")
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
        arcpy.SelectLayerByLocation_management(layerName3, "intersect", joinedFeat_selected)
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
        arcpy.Merge_management([noPoly1_selected2,joinedFeat_selected1],mergedFeat)
        arcpy.AddMessage("merge done")
        arcpy.Copy_management(mergedFeat,outFeat)

        # delete intermediate results
        self.deleteDataItems(interimDataList)
        self.deleteFields(outFeat)
        arcpy.AddMessage("Openness High tool is done")
                    
                    
