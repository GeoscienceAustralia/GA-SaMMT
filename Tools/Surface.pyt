#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: July 1, 2022
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
        self.alias = "Surface"

        # List of tool classes associated with this toolbox
        # There are two tools. One tool is used to generate three-class morphological surface from a bathymetry grid. The other is used to generate three-class morphological surface from a slope grid.
        self.tools = [SurfaceToolBathy,SurfaceToolSlope]

# This tool is used to generate three-class morphological surface from a bathymetry grid.
class SurfaceToolBathy(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Morphological Surface Tool Bathymetry"
        self.description = "Generate three morphological surface classes from bathymetry"
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
            displayName="Output Slope Raster",
            name="slopeRas",
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
            displayName="Number of times to apply Majority Filter",
            name="nuMF",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param4.value = 3        
        
        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="required",
            direction="Input")        
        param5.defaultEnvironmentName = "workspace"
        
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
        
        bathyRas = parameters[0].valueAsText
        slopeRas = parameters[1].valueAsText
        outFeat = parameters[2].valueAsText
        areaThreshold = parameters[3].valueAsText
        nuMF = parameters[4].valueAsText
        tempWS = parameters[5].valueAsText
        # enable helper function
        helper = helpers()
        bathyRas = helper.convert_backslach_forwardslach(bathyRas)
        slopeRas = helper.convert_backslach_forwardslach(slopeRas)
        outFeat = helper.convert_backslach_forwardslach(outFeat)
        tempWS = helper.convert_backslach_forwardslach(tempWS)

        # if the input bathymetry raster is selected from a drop-down list, the bathyRas does not contain the full path
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
        
        # check that the output slope grid is in a correct format
        if slopeRas.rfind(".gdb") == -1:
            messages.addErrorMessage("The output slope raster must be nominated as a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the temporary workspace is in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage("The temporary workspace must be nominated as a File GeoDatabase!")
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0:bathyRas.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit =  areaThreshold.split(" ")[1]
        
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError
  
        # Check out the ArcGIS Spatial Analyst extension license
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.workspace=workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to generate morphological surface classes
        helper.Surface_Tool_bathy(tempWS,bathyRas,slopeRas,outFeat,areaThresholdValue,areaUnit,nuMF)
        return

# This tool is used to generate three-class morphological surface from a slope grid.
class SurfaceToolSlope(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Morphological Surface Tool Slope"
        self.description = "Generate three morphological surface classes from slope grid"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""


        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Slope Raster",
            name="slopeRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input")
       
        
        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Number of times to apply Majority Filter",
            name="nuMF",
            datatype="GPLong",
            parameterType="Required",
            direction="Input")
        param3.value = 3
        
        
        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="required",
            direction="Input")        
        param4.defaultEnvironmentName = "workspace"
        
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
   
        slopeRas = parameters[0].valueAsText
        outFeat = parameters[1].valueAsText
        areaThreshold = parameters[2].valueAsText
        nuMF = parameters[3].valueAsText
        tempWS = parameters[4].valueAsText
        # enable helper function
        helper = helpers()
        slopeRas = helper.convert_backslach_forwardslach(slopeRas)
        outFeat = helper.convert_backslach_forwardslach(outFeat)
        tempWS = helper.convert_backslach_forwardslach(tempWS)

        # if the input slope raster is selected from a drop-down list, the slopeRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if slopeRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if slopeRas == lyr.name:
                        slopeRas = helper.convert_backslach_forwardslach(lyr.dataSource)
        

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(slopeRas)
        rasFormat = rasDesc.format
        if rasFormat != 'FGDBR':
            messages.addErrorMessage("The input slope raster must be a raster dataset in a File GeoDatabase!")
            raise arcpy.ExecuteError        

        # check that the output featureclass is in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the temporary workspace is in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage("The temporary workspace must be nominated as a File GeoDatabase!")
            raise arcpy.ExecuteError
        workspaceName = slopeRas[0:slopeRas.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit =  areaThreshold.split(" ")[1]
        
        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError
  
        # Check out the ArcGIS Spatial Analyst extension license
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.workspace=workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to generate morphological surface classes
        helper.Surface_Tool_slope(tempWS,slopeRas,outFeat,areaThresholdValue,areaUnit,nuMF)
        return
# helper functions are defined here
class helpers(object):
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

    # This function generate three-class morphological surface from a bathymetry grid
    def Surface_Tool_bathy(self,tempWS,bathyRas,slopeRas,outFeat,areaThresholdValue,areaUnit,nuMF):
        # tempWS: temporary workspace to store temporary data
        # bathyRas: input bathymetry grid
        # slopeRas: output slope grid
        # outFeat: output morphological surface
        # areaThresholdValue: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # nuMF: number of times applying Majority Filter
        
        arcpy.AddMessage("running generate surface from bathmetry tool ...")
        interimDataList = []
        # calculate slope raster
        slopeRasName = slopeRas[slopeRas.rfind("/")+1:]
        slopeRas1 = tempWS + "/" + slopeRasName        
        # If the slope raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate slope raster only once,
        # as the calculation may takes a long time depending on the size of the bathymetric grid.
        if arcpy.Exists(slopeRas1):
            arcpy.Copy_management(slopeRas1,slopeRas)
            arcpy.AddMessage(slopeRas+' exists and will be used')        
        else:
            arcpy.AddMessage("calculating slope...")        
            outSlope = Slope(bathyRas)
            outSlope.save(slopeRas)
        # copy the slope raster to a backup directory
        arcpy.Copy_management(slopeRas,slopeRas1)

        # reclassify the slope raster based on the folowing conditions
        arcpy.AddMessage("Reclassifing ...")
        rcRas = tempWS + "/rcRas"
        interimDataList.append(rcRas)
        reclassField = "Value"
        # 0-2 degree: Plane; 2-10 degree: Slope; >10 degree: Escarpment
        remap = RemapRange([[0,2,1],[2,10,2],[10,90,3]])
        outReclassify = Reclassify(slopeRas,reclassField,remap,"NODATA")
        outReclassify.save(rcRas)

        # apply majority filter a number of times to smooth th reclassified grid
        arcpy.AddMessage("Applying Majority Filter ...")

        outMF = MajorityFilter(rcRas, "EIGHT", "HALF")
        MFRasName = tempWS + "/MFRas1"
        interimDataList.append(MFRasName)
        outMF.save(MFRasName)
        i = 1
        while i < int(nuMF):
            outMF = MajorityFilter(MFRasName, "EIGHT", "HALF")
            MFRasName = tempWS + "/MFRas" + str(i+1)
            interimDataList.append(MFRasName)
            arcpy.AddMessage(MFRasName)
            outMF.save(MFRasName)
            i += 1

        # convert raster to polygon
        arcpy.AddMessage("Converting raster to polygon ...")
        outFeat1 = tempWS + "/outFeat_temp1"
        interimDataList.append(outFeat1)
        arcpy.RasterToPolygon_conversion(MFRasName,outFeat1,"NO_SIMPLIFY","VALUE")
        # add and calculate an Area field 
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(outFeat1,"AREA_GEODESIC","",areaUnit1)
        result = arcpy.GetCount_management(outFeat1)
        count = int(result[0])
        
        # eliminate small polygons 
   
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = self.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        
        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
        interimDataList.append(eliminatedFeat)
        
        layerName = "lyr1"      
        arcpy.MakeFeatureLayer_management(outFeat1, layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        result = arcpy.GetCount_management(layerName)
        if int(result[0]) > 0:        
            eliminatedFeat = tempWS + "/eliminatedFeat1"
            interimDataList.append(eliminatedFeat)
            arcpy.Eliminate_management(layerName,eliminatedFeat,"AREA")
            result = arcpy.GetCount_management(eliminatedFeat)
            countNew = int(result[0])
            if countNew == count: # nothing to eliminate
                arcpy.Copy_management(eliminatedFeat,outFeat)
                arcpy.AddMessage("Eliminate done. Final features generated.")
            else:
                count = countNew                
                i = 2
                while i < 1000: # continue loop until nothing to eliminate
                    layerName = "lyr" + str(i)      
                    arcpy.MakeFeatureLayer_management(eliminatedFeat, layerName)
                    arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
                    result = arcpy.GetCount_management(layerName)
                    if int(result[0]) > 0:
                        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
                        interimDataList.append(eliminatedFeat)
                        arcpy.Eliminate_management(layerName,eliminatedFeat,"AREA")
                        result = arcpy.GetCount_management(eliminatedFeat)
                        countNew = int(result[0])
                        if countNew == count:
                            arcpy.Copy_management(eliminatedFeat,outFeat)
                            arcpy.AddMessage("Eliminate done. Final features generated.")
                            break;
                        else:
                            count = countNew
                            arcpy.AddMessage(str(count))
                            i += 1
                    else:
                        arcpy.Copy_management(eliminatedFeat,outFeat)
                        arcpy.AddMessage("Eliminate done. Final features generated.")
                        break;
        else:
            arcpy.Copy_management(outFeat1,outFeat)
            arcpy.AddMessage("Nothing to eliminate. All polygons have area greater than the threshold. Final features generated.")

        # add and calculate surface field
        fieldName = "surface"
        fieldType = "TEXT"
        fieldLength = 255
        arcpy.AddField_management(outFeat,fieldName,fieldType,field_length=fieldLength)
        
        where_clause = '"gridcode" = 1'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Plane'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)

        where_clause = '"gridcode" = 2'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Slope'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)

        where_clause = '"gridcode" = 3'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Escarpment'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)
        
        self.deleteDataItems(interimDataList)
        
    # This function generate three-class morphological surface from a bathymetry grid    
    def Surface_Tool_slope(self,tempWS,slopeRas,outFeat,areaThresholdValue,areaUnit,nuMF):
        # tempWS: temporary workspace to store temporary data
        # slopeRas: input slope grid
        # outFeat: output morphological surface
        # areaThresholdValue: input area threshold value
        # areaUnit: input area unit of the areaThreshold
        # nuMF: number of times applying Majority Filter
                
        arcpy.AddMessage("running generate surface from slope tool ...")
        interimDataList = []
 
        # reclassify the slope raster based on the folowing conditions
        arcpy.AddMessage("Reclassifing ...")
        rcRas = tempWS + "/rcRas"
        interimDataList.append(rcRas)
        reclassField = "Value"
        # 0-2 degree: Plane; 2-10 degree: Slope; >10 degree: Escarpment
        remap = RemapRange([[0,2,1],[2,10,2],[10,90,3]])
        outReclassify = Reclassify(slopeRas,reclassField,remap,"NODATA")
        outReclassify.save(rcRas)

        # apply majority filter a number of times to smooth th reclassified grid
        arcpy.AddMessage("Applying Majority Filter ...")

        outMF = MajorityFilter(rcRas, "EIGHT", "HALF")
        MFRasName = tempWS + "/MFRas1"
        interimDataList.append(MFRasName)
        outMF.save(MFRasName)
        i = 1
        while i < int(nuMF):
            outMF = MajorityFilter(MFRasName, "EIGHT", "HALF")
            MFRasName = tempWS + "/MFRas" + str(i+1)
            interimDataList.append(MFRasName)
            arcpy.AddMessage(MFRasName)
            outMF.save(MFRasName)
            i += 1

        # convert raster to polygon

        arcpy.AddMessage("Converting raster to polygon ...")
        outFeat1 = tempWS + "/outFeat_temp1"
        interimDataList.append(outFeat1)
        arcpy.RasterToPolygon_conversion(MFRasName,outFeat1,"NO_SIMPLIFY","VALUE")
        # add and calculate an Area field 
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.AddGeometryAttributes_management(outFeat1,"AREA_GEODESIC","",areaUnit1)
        result = arcpy.GetCount_management(outFeat1)
        count = int(result[0])
        
        # eliminate small polygons 
   
        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = self.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)
        
        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
        interimDataList.append(eliminatedFeat)
        
        layerName = "lyr1"      
        arcpy.MakeFeatureLayer_management(outFeat1, layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        result = arcpy.GetCount_management(layerName)
        if int(result[0]) > 0:        
            eliminatedFeat = tempWS + "/eliminatedFeat1"
            interimDataList.append(eliminatedFeat)
            arcpy.Eliminate_management(layerName,eliminatedFeat,"AREA")
            result = arcpy.GetCount_management(eliminatedFeat)
            countNew = int(result[0])
            if countNew == count: # nothing to eliminate
                arcpy.Copy_management(eliminatedFeat,outFeat)
                arcpy.AddMessage("Eliminate done. Final features generated.")
            else:
                count = countNew                
                i = 2
                while i < 1000:   # continue loop until nothing to eliminate
                    layerName = "lyr" + str(i)      
                    arcpy.MakeFeatureLayer_management(eliminatedFeat, layerName)
                    arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
                    result = arcpy.GetCount_management(layerName)
                    if int(result[0]) > 0:
                        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
                        interimDataList.append(eliminatedFeat)
                        arcpy.Eliminate_management(layerName,eliminatedFeat,"AREA")
                        result = arcpy.GetCount_management(eliminatedFeat)
                        countNew = int(result[0])
                        if countNew == count:
                            arcpy.Copy_management(eliminatedFeat,outFeat)
                            arcpy.AddMessage("Eliminate done. Final features generated.")
                            break;
                        else:
                            count = countNew
                            arcpy.AddMessage(str(count))
                            i += 1
                    else:
                        arcpy.Copy_management(eliminatedFeat,outFeat)
                        arcpy.AddMessage("Eliminate done. Final features generated.")
                        break;
        else:
            arcpy.Copy_management(outFeat1,outFeat)
            arcpy.AddMessage("Nothing to eliminate. All polygons have area greater than the threshold. Final features generated.")

        # add and calculate surface field
        fieldName = "surface"
        fieldType = "TEXT"
        fieldLength = 255
        arcpy.AddField_management(outFeat,fieldName,fieldType,field_length=fieldLength)
        
        where_clause = '"gridcode" = 1'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Plane'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)

        where_clause = '"gridcode" = 2'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Slope'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)

        where_clause = '"gridcode" = 3'
        layerName = "tempLyr"
        arcpy.MakeFeatureLayer_management(outFeat,layerName)
        arcpy.SelectLayerByAttribute_management(layerName, "NEW_SELECTION", where_clause)
        expression = "'Escarpment'" 
        arcpy.CalculateField_management(layerName, fieldName, expression, "PYTHON_9.3")
        arcpy.Delete_management(layerName)

        self.deleteDataItems(interimDataList)
        
                
        

        
        
