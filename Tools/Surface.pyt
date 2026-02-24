#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: July 1, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above


import arcpy
from arcpy.sa import MajorityFilter, Reclassify, RemapRange, Slope
import HelperFunctions


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "Surface"

        # List of tool classes associated with this toolbox
        # There are two tools. One tool is used to generate three-class morphological surface from a bathymetry grid. The other is used to generate three-class morphological surface from a slope grid.
        self.tools = [SurfaceToolBathy, SurfaceToolSlope]


# This tool is used to generate three-class morphological surface from a bathymetry grid.
class SurfaceToolBathy:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Morphological Surface Tool Bathymetry"
        self.description = (
            "Generate three morphological surface classes from bathymetry"
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
            displayName="Output Slope Raster",
            name="slopeRas",
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
            displayName="Number of times to apply Majority Filter",
            name="nuMF",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param4.value = 3

        # sixth parameter
        param5 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
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

        # set the output slope raster and output featureclass to be at the
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
            parameters[1].value = bathyRas + "_slope"
            parameters[2].value = bathyRas + "_surface"  

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
        bathyRas = HelperFunctions.convert_backslash_forwardslash(bathyRas)
        slopeRas = HelperFunctions.convert_backslash_forwardslash(slopeRas)
        outFeat = HelperFunctions.convert_backslash_forwardslash(outFeat)
        tempWS = HelperFunctions.convert_backslash_forwardslash(tempWS)

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

        # check that the output slope grid is in a correct format
        if slopeRas.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output slope raster must be nominated as a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the temporary workspace is in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The temporary workspace must be nominated as a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        workspaceName = bathyRas[0 : bathyRas.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        # Check out the ArcGIS Spatial Analyst extension license
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to generate morphological surface classes
        helper.Surface_Tool_bathy(
            tempWS, bathyRas, slopeRas, outFeat, areaThresholdValue, areaUnit, nuMF
        )
        return


# This tool is used to generate three-class morphological surface from a slope grid.
class SurfaceToolSlope:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Morphological Surface Tool Slope"
        self.description = (
            "Generate three morphological surface classes from slope grid"
        )
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Slope Raster",
            name="slopeRas",
            datatype="GPRasterLayer",
            parameterType="Required",
            direction="Input",
        )

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Feature",
            name="outFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output",
        )

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Area Threshold",
            name="areaThreshold",
            datatype="GPArealUnit",
            parameterType="Required",
            direction="Input",
        )

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Number of times to apply Majority Filter",
            name="nuMF",
            datatype="GPLong",
            parameterType="Required",
            direction="Input",
        )
        param3.value = 3

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Temporary Workspace",
            name="tempWS",
            datatype="DEWorkspace",
            parameterType="Required",
            direction="Input",
        )
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

        # set the output slope raster and output featureclass to be at the
        # same FileGeodatabase as the input bathymetry grid
        if parameters[0].value:
            slopeRas = parameters[0].valueAsText
            if slopeRas.rfind("/") < 0:
                aprx = arcpy.mp.ArcGISProject("CURRENT")
                m = aprx.activeMap
                for lyr in m.listLayers():
                    if lyr.isRasterLayer:
                        if slopeRas == lyr.name:
                            slopeRas = lyr.dataSource
            parameters[1].value = slopeRas + "_surface"  

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
        slopeRas = HelperFunctions.convert_backslash_forwardslash(slopeRas)
        outFeat = HelperFunctions.convert_backslash_forwardslash(outFeat)
        tempWS = HelperFunctions.convert_backslash_forwardslash(tempWS)

        # if the input slope raster is selected from a drop-down list, the slopeRas does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if slopeRas.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap
            for lyr in m.listLayers():
                if lyr.isRasterLayer:
                    if slopeRas == lyr.name:
                        slopeRas = HelperFunctions.convert_backslash_forwardslash(lyr.dataSource)

        # check that the input bathymetry grid is in a correct format
        rasDesc = arcpy.Describe(slopeRas)
        rasFormat = rasDesc.format
        if rasFormat != "FGDBR":
            messages.addErrorMessage(
                "The input slope raster must be a raster dataset in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if outFeat.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The output featureclass must be nominated as a feature class in a File GeoDatabase!"
            )
            raise arcpy.ExecuteError

        # check that the temporary workspace is in a correct format
        if tempWS.rfind(".gdb") == -1:
            messages.addErrorMessage(
                "The temporary workspace must be nominated as a File GeoDatabase!"
            )
            raise arcpy.ExecuteError
        workspaceName = slopeRas[0 : slopeRas.rfind("/")]
        areaThresholdValue = areaThreshold.split(" ")[0]
        areaUnit = areaThreshold.split(" ")[1]

        if areaUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown area unit.")
            raise arcpy.ExecuteError

        # Check out the ArcGIS Spatial Analyst extension license
        arcpy.CheckOutExtension("Spatial")
        arcpy.env.workspace = workspaceName
        arcpy.env.overwriteOutput = True
        # call the helper function to generate morphological surface classes
        helper.Surface_Tool_slope(
            tempWS, slopeRas, outFeat, areaThresholdValue, areaUnit, nuMF
        )
        return


# helper functions are defined here
class helpers:     

    # This function generate three-class morphological surface from a bathymetry grid
    def Surface_Tool_bathy(
        self, tempWS, bathyRas, slopeRas, outFeat, areaThresholdValue, areaUnit, nuMF
    ):
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
        slopeRasName = slopeRas[slopeRas.rfind("/") + 1 :]
        slopeRas1 = tempWS + "/" + slopeRasName
        # If the slope raster already exists in a backup directory, just copied the raster to the workspace.
        # The intension is to calculate slope raster only once,
        # as the calculation may takes a long time depending on the size of the bathymetric grid.
        if arcpy.Exists(slopeRas1):
            arcpy.management.Copy(slopeRas1, slopeRas)
            arcpy.AddMessage(slopeRas + " exists and will be used")
        else:
            arcpy.AddMessage("calculating slope...")
            outSlope = Slope(bathyRas)
            outSlope.save(slopeRas)
        # copy the slope raster to a backup directory
        arcpy.management.Copy(slopeRas, slopeRas1)

        # reclassify the slope raster based on the folowing conditions
        arcpy.AddMessage("Reclassifing ...")
        rcRas = tempWS + "/rcRas"
        interimDataList.append(rcRas)
        reclassField = "Value"
        # 0-2 degree: Plane; 2-10 degree: Slope; >10 degree: Escarpment
        remap = RemapRange([[0, 2, 1], [2, 10, 2], [10, 90, 3]])
        outReclassify = Reclassify(slopeRas, reclassField, remap, "NODATA")
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
            MFRasName = tempWS + "/MFRas" + str(i + 1)
            interimDataList.append(MFRasName)
            arcpy.AddMessage(MFRasName)
            outMF.save(MFRasName)
            i += 1

        # convert raster to polygon
        arcpy.AddMessage("Converting raster to polygon ...")
        outFeat1 = tempWS + "/outFeat_temp1"
        interimDataList.append(outFeat1)
        arcpy.conversion.RasterToPolygon(MFRasName, outFeat1, "NO_SIMPLIFY", "VALUE")
        # add and calculate an Area field
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.management.AddGeometryAttributes(outFeat1, "AREA_GEODESIC", "", areaUnit1)
        result = arcpy.management.GetCount(outFeat1)
        count = int(result[0])

        # eliminate small polygons

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)

        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
        interimDataList.append(eliminatedFeat)

        layerName = "lyr1"
        arcpy.management.MakeFeatureLayer(outFeat1, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        result = arcpy.management.GetCount(layerName)
        if int(result[0]) > 0:
            eliminatedFeat = tempWS + "/eliminatedFeat1"
            interimDataList.append(eliminatedFeat)
            arcpy.management.Eliminate(layerName, eliminatedFeat, "AREA")
            result = arcpy.management.GetCount(eliminatedFeat)
            countNew = int(result[0])
            if countNew == count:  # nothing to eliminate
                arcpy.management.Copy(eliminatedFeat, outFeat)
                arcpy.AddMessage("Eliminate done. Final features generated.")
            else:
                count = countNew
                i = 2
                while i < 1000:  # continue loop until nothing to eliminate
                    layerName = "lyr" + str(i)
                    arcpy.management.MakeFeatureLayer(eliminatedFeat, layerName)
                    arcpy.management.SelectLayerByAttribute(
                        layerName, "NEW_SELECTION", where_clause
                    )
                    result = arcpy.management.GetCount(layerName)
                    if int(result[0]) > 0:
                        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
                        interimDataList.append(eliminatedFeat)
                        arcpy.management.Eliminate(layerName, eliminatedFeat, "AREA")
                        result = arcpy.management.GetCount(eliminatedFeat)
                        countNew = int(result[0])
                        if countNew == count:
                            arcpy.management.Copy(eliminatedFeat, outFeat)
                            arcpy.AddMessage(
                                "Eliminate done. Final features generated."
                            )
                            break
                        else:
                            count = countNew
                            arcpy.AddMessage(str(count))
                            i += 1
                    else:
                        arcpy.management.Copy(eliminatedFeat, outFeat)
                        arcpy.AddMessage("Eliminate done. Final features generated.")
                        break
        else:
            arcpy.management.Copy(outFeat1, outFeat)
            arcpy.AddMessage(
                "Nothing to eliminate. All polygons have area greater than the threshold. Final features generated."
            )

        # add and calculate surface field
        fieldName = "surface"
        fieldType = "TEXT"
        fieldLength = 255
        arcpy.management.AddField(
            outFeat, fieldName, fieldType, field_length=fieldLength
        )

        where_clause = '"gridcode" = 1'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Plane'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        where_clause = '"gridcode" = 2'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Slope'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        where_clause = '"gridcode" = 3'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Escarpment'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        HelperFunctions.deleteDataItems(interimDataList)

    # This function generate three-class morphological surface from a bathymetry grid
    def Surface_Tool_slope(
        self, tempWS, slopeRas, outFeat, areaThresholdValue, areaUnit, nuMF
    ):
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
        remap = RemapRange([[0, 2, 1], [2, 10, 2], [10, 90, 3]])
        outReclassify = Reclassify(slopeRas, reclassField, remap, "NODATA")
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
            MFRasName = tempWS + "/MFRas" + str(i + 1)
            interimDataList.append(MFRasName)
            arcpy.AddMessage(MFRasName)
            outMF.save(MFRasName)
            i += 1

        # convert raster to polygon

        arcpy.AddMessage("Converting raster to polygon ...")
        outFeat1 = tempWS + "/outFeat_temp1"
        interimDataList.append(outFeat1)
        arcpy.conversion.RasterToPolygon(MFRasName, outFeat1, "NO_SIMPLIFY", "VALUE")
        # add and calculate an Area field
        areaUnit1 = "SQUARE_KILOMETERS"
        arcpy.management.AddGeometryAttributes(outFeat1, "AREA_GEODESIC", "", areaUnit1)
        result = arcpy.management.GetCount(outFeat1)
        count = int(result[0])

        # eliminate small polygons

        # convert the input area unit to "SQUARE_KILOMETERS"
        converter = HelperFunctions.areaUnitConverter(areaUnit)
        areaThreshold = converter * float(areaThresholdValue)
        where_clause = '"AREA_GEO" < ' + str(areaThreshold)

        # eliminate based on the area attribute
        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
        interimDataList.append(eliminatedFeat)

        layerName = "lyr1"
        arcpy.management.MakeFeatureLayer(outFeat1, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        result = arcpy.management.GetCount(layerName)
        if int(result[0]) > 0:
            eliminatedFeat = tempWS + "/eliminatedFeat1"
            interimDataList.append(eliminatedFeat)
            arcpy.management.Eliminate(layerName, eliminatedFeat, "AREA")
            result = arcpy.management.GetCount(eliminatedFeat)
            countNew = int(result[0])
            if countNew == count:  # nothing to eliminate
                arcpy.management.Copy(eliminatedFeat, outFeat)
                arcpy.AddMessage("Eliminate done. Final features generated.")
            else:
                count = countNew
                i = 2
                while i < 1000:  # continue loop until nothing to eliminate
                    layerName = "lyr" + str(i)
                    arcpy.management.MakeFeatureLayer(eliminatedFeat, layerName)
                    arcpy.management.SelectLayerByAttribute(
                        layerName, "NEW_SELECTION", where_clause
                    )
                    result = arcpy.management.GetCount(layerName)
                    if int(result[0]) > 0:
                        eliminatedFeat = tempWS + "/eliminatedFeat" + str(i)
                        interimDataList.append(eliminatedFeat)
                        arcpy.management.Eliminate(layerName, eliminatedFeat, "AREA")
                        result = arcpy.management.GetCount(eliminatedFeat)
                        countNew = int(result[0])
                        if countNew == count:
                            arcpy.management.Copy(eliminatedFeat, outFeat)
                            arcpy.AddMessage(
                                "Eliminate done. Final features generated."
                            )
                            break
                        else:
                            count = countNew
                            arcpy.AddMessage(str(count))
                            i += 1
                    else:
                        arcpy.management.Copy(eliminatedFeat, outFeat)
                        arcpy.AddMessage("Eliminate done. Final features generated.")
                        break
        else:
            arcpy.management.Copy(outFeat1, outFeat)
            arcpy.AddMessage(
                "Nothing to eliminate. All polygons have area greater than the threshold. Final features generated."
            )

        # add and calculate surface field
        fieldName = "surface"
        fieldType = "TEXT"
        fieldLength = 255
        arcpy.management.AddField(
            outFeat, fieldName, fieldType, field_length=fieldLength
        )

        where_clause = '"gridcode" = 1'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Plane'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        where_clause = '"gridcode" = 2'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Slope'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        where_clause = '"gridcode" = 3'
        layerName = "tempLyr"
        arcpy.management.MakeFeatureLayer(outFeat, layerName)
        arcpy.management.SelectLayerByAttribute(
            layerName, "NEW_SELECTION", where_clause
        )
        expression = "'Escarpment'"
        arcpy.management.CalculateField(layerName, fieldName, expression, "PYTHON3")
        arcpy.management.Delete(layerName)

        HelperFunctions.deleteDataItems(interimDataList)
