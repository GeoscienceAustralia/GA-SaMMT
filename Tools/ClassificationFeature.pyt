#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: August 15, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
arcpy.CheckOutExtension("Spatial")

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "ClassifyFeatures"

        # List of tool classes associated with this toolbox
        # There are two tools. One tool is used to classify Bathymetric High features. The other is used to classify Bathymetric Low features.
        self.tools = [Classify_Bathymetric_High_Features_Tool,Classify_Bathymetric_Low_Features_Tool]


# This tool is used to classify Bathymetric Low features based on their attributes.
class Classify_Bathymetric_Low_Features_Tool(object):
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
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output")
        param1.parameterDependencies = [param0.name]
        
        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Length_to_Width Ratio Threshold",
            name="lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param2.value = 8.0

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Head Depth Threshold (m)",
            name="headDepthT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param3.value = 4000.0

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Mean Segment Slope Threshold Large (degree)",
            name="meanSegmentSlopeT1",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param4.value = 7.0

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Head_to_Foot Depth Range Threshold (m)",
            name="hfdepthRangeT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param5.value = 600.0

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Mean Segment Slope Threshold Small (degree)",
            name="meanSegmentSlopeT2",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param6.value = 2.0

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Shape Circularity Threshold",
            name="circularityT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
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
            messages.addErrorMessage('Mean Segment Slope Threshold Small must be smaller than Mean Segment Slope Threshold Large!')
            raise arcpy.ExecuteError
        
        # enable helper 
        helper = helpers()
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)        

        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(lyr.dataSource)
                        
       # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (inFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage("The input featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the input feature class is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage("Coordinate system of input featureclass is Geographic. A projected coordinate system is required!")
            raise arcpy.ExecuteError
        
        workspaceName = inFeatClass[0:inFeatClass.rfind("/")] 
        env.workspace=workspaceName
        env.overwriteOutput = True

        
        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # make sure all the required attributes exist in the input featureclass
        attributeList = ['featID','LengthWidthRatio','head_foot_depthRange','mean_width','profileSymmetry',
                         'profile_bottom_SlopeClass','profile_side_SlopeClass','headDepth',
                         'mean_segment_slope','mean_width_thickness_ratio','mean_thickness',
                         'width_distance_slope','width_distance_correlation','thick_distance_slope',
                         'thick_distance_correlation','Circularity']

        attributeList = ['featID','LengthWidthRatio','head_foot_depthRange','mean_width','profileSymmetry',
                         'profile_bottom_SlopeClass','profile_side_SlopeClass','headDepth',
                         'mean_segment_slope','Circularity']
        for attribute in attributeList:
            if attribute not in field_names:
                messages.addErrorMessage('The input featureclass does not have ' + attribute + ' attribute. You have to calculate the attribute using the Attributes Tool!')
                raise arcpy.ExecuteError

        # check the 'Morphological_Feature' field exists    
        field = "Morphological_Feature"
        fieldType = "TEXT"
        fieldLength = 200
        if field in field_names:
            arcpy.AddMessage(field + " exists and will be recalculated.")
        else:            
            arcpy.AddField_management(inFeatClass,field,fieldType,field_length=fieldLength)
        
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
            profileSymmetryL = profileSymmetry.split(',')
            profileBottomClass = row.getValue("profile_bottom_SlopeClass")
            profileBottomClassL = profileBottomClass.split(',')
            profileSideClass = row.getValue("profile_side_SlopeClass")
            profileSideClassL = profileSideClass.split(',')
            headDepth = float(row.getValue("headDepth"))
            meanSegmentSlope = float(row.getValue("mean_segment_slope"))
            circularity = float(row.getValue("Circularity"))

            # the bottom slope list combines profile's bottom slope and side slope (only when the profile is triangle)
            slopeL = []
            j = 0
            while j < len(profileBottomClassL):
                bottomSlope = profileBottomClassL[j]
                sideSlope = profileSideClassL[j]
                if bottomSlope == 'no bottom': # triangle profile
                    slopeL.append(sideSlope)
                else:
                    slopeL.append(bottomSlope)
                j += 1
            arcpy.AddMessage('slopeL: ' + str(slopeL))            
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
            SymmCount = profileSymmetryL.count('Symmetric')
            AsymmCount = profileSymmetryL.count('Asymmetric')          

            # classification of Bathymetric Low features starts here
            # The classification rules are based on the morphological classification scheme. Please see the metadata of the tool for detailed description of the rules.
            feature = 'unclassified'
            if lwRatio >= lwRatioT:
                if abs(headDepth) >= headDepthT:
                    if (AsymmCount >= SymmCount) and (steepSlopeCount + moderateSlopeCount >= flatSlopeCount + gentleSlopeCount):
                        feature = 'Trench'
                    else:
                        feature = 'Trough'
                else:
                    if (meanSegmentSlope > meanSegmentSlopeT1 ) and (sSteepCount + sModerateCount >= sFlatCount + sGentleCount):                
                        feature = 'Gully'               
                    else: 
                        if (hfdepthRange >= hfdepthRangeT) and (meanSegmentSlope >= meanSegmentSlopeT2):
                            feature = 'Canyon'
                        else:
                            feature = 'Valley/Channel' 
            else:        
                sCount = sSteepCount + sModerateCount + sGentleCount + sFlatCount
                if (sCount == 0):
                    feature = 'Depression'
                elif (circularity >= circularityT) and (sSteepCount >= sModerateCount) and (sSteepCount >= sGentleCount) and (sSteepCount >= sFlatCount):
                    feature = 'Hole'
                else:
                    feature = 'Depression'

            row.setValue(field,feature)
            cursor.updateRow(row)
            arcpy.AddMessage(feature)
        del cursor,row

        return

# This tool is used to classify Bathymetric High features based on their attributes
class Classify_Bathymetric_High_Features_Tool(object):
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
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Features",
            name="outFeatClass",
            datatype="DEFeatureClass",
            parameterType="Derived",
            direction="Output")
        param1.parameterDependencies = [param0.name]
        
        # 3rd parameter
        param2 = arcpy.Parameter(
            displayName="Ridge Length_to_Width Ratio Threshold",
            name="ridge_lwRatioT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param2.value = 5.0

        # 4th parameter
        param3 = arcpy.Parameter(
            displayName="Bank Minimum Depth Threshold (m)",
            name="bank_minDepthT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param3.value = 200.0

        # 5th parameter
        param4 = arcpy.Parameter(
            displayName="Bank Area Threshold (km^2)",
            name="bank_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param4.value = 1.0

        # 6th parameter
        param5 = arcpy.Parameter(
            displayName="Plateau Area Threshold (km^2)",
            name="plateau_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param5.value = 100.0

        # 7th parameter
        param6 = arcpy.Parameter(
            displayName="Hummock Depth Range Threshold (m)",
            name="hummock_depthRangeT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param6.value = 10.0

        # 8th parameter
        param7 = arcpy.Parameter(
            displayName="Hummock Area Threshold (m^2)",
            name="hummock_areaT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param7.value = 1000.0

        # 9th parameter
        param8 = arcpy.Parameter(
            displayName="Cone Circularity Threshold",
            name="cone_circularityT",
            datatype="GPDouble",
            parameterType="Optional",
            direction="Input")
        param8.value = 0.75   
        
        parameters = [param0, param1, param2, param3, param4, param5, param6, param7, param8]
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
        inFeatClass = helper.convert_backslach_forwardslach(inFeatClass)        
        # if the input feature class is selected from a drop-down list, the inFeatClass does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeatClass.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeatClass == lyr.name:
                        inFeatClass = helper.convert_backslach_forwardslach(lyr.dataSource)
       # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeatClass)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (inFeatClass.rfind(".gdb") == -1):
            messages.addErrorMessage("The input featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError


        # check that the input feature class is in a projected coordinate system
        spatialReference = vecDesc.spatialReference
        if spatialReference.type == "Geographic":
            messages.addErrorMessage("Coordinate system of input featureclass is Geographic. A projected coordinate system is required!")
            raise arcpy.ExecuteError
        
        workspaceName = inFeatClass[0:inFeatClass.rfind("/")] 
        env.workspace=workspaceName
        env.overwriteOutput = True

        
        fields = arcpy.ListFields(inFeatClass)
        field_names = [f.name for f in fields]
        # make sure all the required attributes exist in the input featureclass
        attributeList = ['featID','LengthWidthRatio','depthRange','profileShape',
                         'profile_top_SlopeClass','profile_side_SlopeClass','minDepth',
                         'mean_width','Circularity']
        for attribute in attributeList:
            if attribute not in field_names:
                messages.addErrorMessage('The input featureclass does not have ' + attribute + ' attribute. You have to calculate the attribute using the Attributes Tool!')
                raise arcpy.ExecuteError
        # check the 'Morphological_Feature' field exists    
        field = "Morphological_Feature"
        fieldType = "TEXT"
        fieldLength = 200
        if field in field_names:
            arcpy.AddMessage(field + " exists and will be recalculated.")
        else:            
            arcpy.AddField_management(inFeatClass,field,fieldType,field_length=fieldLength)
        
        
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
            profileShapeL = profileShape.split(',')
            profileTopClass = row.getValue("profile_top_SlopeClass")
            profileTopClassL = profileTopClass.split(',')
            profileSideClass = row.getValue("profile_side_SlopeClass")
            profileSideClassL = profileSideClass.split(',')
            minDepth = float(row.getValue("minDepth")) 
            meanWidth = float(row.getValue("mean_width"))
            area = float(row.getValue("Shape_Area"))
            circularity = float(row.getValue("Circularity"))
            # get profile shape class count
            RegularCount = profileShapeL.count('Regular')
            IrregularCount = profileShapeL.count('Irregular')
            TriangleCount = profileShapeL.count('Triangle')
            FlatCount = profileShapeL.count('Flat')
            
            # if profile shape is a triangle, add its profile side slope class
            triangle_sideSlopeL = []
            k = 0
            while k < len(profileShapeL):
                pShape = profileShapeL[k]
                sideSlope = profileSideClassL[k]
                if pShape == 'Triangle':
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
                if topSlope == 'no top': #triangle profile
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
            elif (TriangleCount >= RegularCount) and (TriangleCount >= IrregularCount) and (TriangleCount >= FlatCount) and (moderateSlopeCountTriangle + steepSlopeCountTriangle >= 1) and (circularity >= cone_circularityT):
                feature = "Cone"
            elif (flatSlopeCount >=  gentleSlopeCount + moderateSlopeCount + steepSlopeCount) and (abs(minDepth) <= bank_minDepthT) and (area > bank_areaT * 1000000):
                feature = "Bank"
            elif (flatSlopeCount >=  gentleSlopeCount + moderateSlopeCount + steepSlopeCount) and (moderateSlopeCountSide + steepSlopeCountSide >= 1) and (area > plateau_areaT * 1000000):
                feature = "Plateau" 
            elif depthRange >= 500:
                if (RegularCount >= IrregularCount) and (RegularCount >= TriangleCount) and (RegularCount >= FlatCount):
                    feature = "Knoll"
                else:
                    feature = "Hill"
            elif (depthRange < hummock_depthRangeT) and (area < hummock_areaT):
                feature = "Hummock"
            else:
                feature = "Mound"
            row.setValue(field,feature)
            cursor.updateRow(row)
            arcpy.AddMessage(feature)
            i += 1
        del cursor,row

        return

# define helper functions here
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
