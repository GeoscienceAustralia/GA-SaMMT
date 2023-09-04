#### Author: Zhi Huang
#### Organisation: Geoscience Australia
#### Email: Zhi.Huang@ga.gov.au
#### Date: July 1, 2022
#### Python version: 3+
#### ArcGIS Pro: 2.6.4 and above

import arcpy
from arcpy import env
from arcpy.sa import *
import numpy as np
from pandas.core.common import flatten
arcpy.CheckOutExtension("Spatial")

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "AccessoryTools"

        # List of tool classes associated with this toolbox
        # There are two tools. Merge Connected Features Tool merges polygon features that are connected through shared points or borders.
        # Connect Nearby Linear Features Tool connects nearby linear bathymetric low features.
        self.tools = [Merge_Connected_Features_Tool,Connect_Nearby_Linear_Features_Tool]


# This tool merges polygon features that are connected through shared points or borders.
class Merge_Connected_Features_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Merge Connected Features Tool"
        self.description = "Merge/dissolve polygon features that are connected by shared point and/or border"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Polygon Features",
            name="inFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Output Features After Merging All Connected Features",
            name="dissolveFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Output Features After Merging Only Features Connected by Shared Border",
            name="dissolveFeat1",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Output Features After Merging Only Features Connected by Shared Point",
            name="dissolveFeat2",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")        

        
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
        
        inFeat = parameters[0].valueAsText
        dissolveFeat = parameters[1].valueAsText
        dissolveFeat1 = parameters[2].valueAsText
        dissolveFeat2 = parameters[3].valueAsText           
        
        # enable the helper functions
        helper = helpers()
        inFeat = helper.convert_backslach_forwardslach(inFeat)
        dissolveFeat = helper.convert_backslach_forwardslach(dissolveFeat)
        dissolveFeat1 = helper.convert_backslach_forwardslach(dissolveFeat1)
        dissolveFeat2 = helper.convert_backslach_forwardslach(dissolveFeat2)

        # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeat == lyr.name:
                        inFeat = helper.convert_backslach_forwardslach(lyr.dataSource)
        
       # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeat)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (inFeat.rfind(".gdb") == -1):
            messages.addErrorMessage("The input featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass after merging all connected features must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat1.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass after merging only features connected by shared border must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat2.rfind(".gdb") == -1:
            messages.addErrorMessage("The output featureclass after merging only features connected by shared point must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError
        
        workspaceName = inFeat[0:inFeat.rfind("/")] 
        env.workspace=workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if 'featID' not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeat,'featID')

        # Generate near table between individual input poygon features
        itemList = []
        outTable = 'nearTable'
        itemList.append(outTable)
        location = 'NO_LOCATION'
        angle = 'NO_ANGLE'
        closest = 'ALL'
        searchRadius = '100 Meters'
        arcpy.GenerateNearTable_analysis(inFeat,inFeat,outTable,search_radius=searchRadius,location=location,angle=angle,closest=closest)

        cursor = arcpy.SearchCursor(outTable)
        inIDList = []
        nearIDList = []
        
        # obtain idLists for connected features which have nearest distance = 0
        # for each input feature, identify its nearest feature with near_dist = 0 (e.g., connected features),
        # inIDList: list of ids of individual input features that have connected features
        # nearIDList:  this list contains the ids of their nearest features
        for row in cursor:
            inID = row.getValue("IN_FID")
            nearID = row.getValue("NEAR_FID") 
            nearDist = row.getValue("NEAR_DIST")    
            if nearDist == 0:    
                inIDList.append(inID)
                nearIDList.append(nearID)
                
        del cursor,row
        # obtain the number of features that are connected
        size = np.unique(np.asarray(inIDList)).size

        if size == 0: # if no features are connected, simply copy the input featureclass to the outputs
            arcpy.AddMessage('There are not connected features')
            arcpy.Copy_management(inFeat,dissolveFeat)
            arcpy.Copy_management(inFeat,dissolveFeat1)
            arcpy.Copy_management(inFeat,dissolveFeat2)
        else: # if there are connected features, do the followings
            arcpy.AddMessage(str(size) + ' total features are connected')

            # call the helper function to generate a new list of featID
            # the connected features will be assigned the same featID
            featIDNewList = helper.findNewFeatIDs(inFeat,inIDList,nearIDList)
            # update the featID field with the new ids
            cursor = arcpy.UpdateCursor(inFeat)
            i = 0
            for row in cursor:
                featIDNew = featIDNewList[i]
                row.setValue('featID',featIDNew)
                cursor.updateRow(row)
                i += 1
            del cursor,row

            # dissolve all connected features that have same featIDs
            arcpy.Dissolve_management(inFeat,dissolveFeat,'featID')
            helper.calculateFeatID(dissolveFeat)

            # after converting dissolved features (multipart) to single-part features, the features connected
            # by shared point(s) will be un-dissolved

            # multipart to single-part
            singlepartFeat = 'dissolve_singlepart'
            itemList.append(singlepartFeat)
            arcpy.MultipartToSinglepart_management(dissolveFeat,singlepartFeat)
            
            # get the feature counts of the input features, the multipart dissolved features, and the single-part dissolved features
            inFeatCount = int(arcpy.GetCount_management(inFeat).getOutput(0))
            dissolveFeatCount = int(arcpy.GetCount_management(dissolveFeat).getOutput(0))
            singlepartFeatCount = int(arcpy.GetCount_management(singlepartFeat).getOutput(0))
            if inFeatCount == singlepartFeatCount: # if all connected features are connected by shared points, copy the multipart dissolved features to outputs
                arcpy.AddMessage('All ' + str(size) + ' features connected by shared point(s)')
                arcpy.Copy_management(dissolveFeat,dissolveFeat1)
                arcpy.Copy_management(dissolveFeat,dissolveFeat2)
            elif dissolveFeatCount == singlepartFeatCount: # if all connected features are connected by shared borders, copy the multipart dissolved features to outputs
                arcpy.AddMessage('All ' + str(size) + ' features connected by shared border(s)')
                arcpy.Copy_management(dissolveFeat,dissolveFeat1)
                arcpy.Copy_management(dissolveFeat,dissolveFeat2)
            else: # if some features are connected by shared points and others are connected by shared borders,
                # 1. copy the single-part dissolved features as the output featureclass after merging features shared by borders
                # 2. call the helper function get a count of features sharing borders and generate output featureclass after merging sharing points
                arcpy.Copy_management(singlepartFeat,dissolveFeat1)
                count = helper.mergeFeatures(inFeat,dissolveFeat,dissolveFeat1,dissolveFeat2)
                count1 = size - count
                arcpy.AddMessage(str(count) + ' features connected by shared border(s)')
                arcpy.AddMessage(str(count1) + ' features connected by shared point(s)')
            helper.calculateFeatID(dissolveFeat1)
            helper.calculateFeatID(dissolveFeat2)
            helper.deleteDataItems(itemList)

        return

# This tool connects nearby linear bathymetric low features.
# The features to be connected satitify the following conditions: 1. the distance between the head of one feature and the foot of another feature is less than a user-defined threshold,
# 2.the two nearby features align in orientation with the intersecting angle < 45 degree. 
class Connect_Nearby_Linear_Features_Tool(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Connect Nearby Linear Features Tool"
        self.description = "Connect nearby linear features that are certain distance apart and align at a similar orientation"
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""

        # first parameter
        param0 = arcpy.Parameter(
            displayName="Input Bathymetric Low Features",
            name="inFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # second parameter
        param1 = arcpy.Parameter(
            displayName="Input Head Features",
            name="headFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # third parameter
        param2 = arcpy.Parameter(
            displayName="Input Foot Features",
            name="footFeat",
            datatype="GPFeatureLayer",
            parameterType="Required",
            direction="Input")

        # fourth parameter
        param3 = arcpy.Parameter(
            displayName="Distance Threshold",
            name="distThreshold",
            datatype="GPLinearUnit",
            parameterType="Required",
            direction="Input")

        # fifth parameter
        param4 = arcpy.Parameter(
            displayName="Output Connected Features",
            name="dissolveFeat",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")        
        
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
        
        inFeat = parameters[0].valueAsText
        headFeat = parameters[1].valueAsText
        footFeat = parameters[2].valueAsText
        distThreshold = parameters[3].valueAsText
        dissolveFeat = parameters[4].valueAsText
                
        # enable helper function
        helper = helpers()
        inFeat = helper.convert_backslach_forwardslach(inFeat)
        headFeat = helper.convert_backslach_forwardslach(headFeat)
        footFeat = helper.convert_backslach_forwardslach(footFeat)
        dissolveFeat = helper.convert_backslach_forwardslach(dissolveFeat)

        # if the input feature class is selected from a drop-down list, the inFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if inFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if inFeat == lyr.name:
                        inFeat = helper.convert_backslach_forwardslach(lyr.dataSource)

        # if the input head feature class is selected from a drop-down list, the headFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if headFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if headFeat == lyr.name:
                        headFeat = helper.convert_backslach_forwardslach(lyr.dataSource)

        # if the input foot feature class is selected from a drop-down list, the footFeat does not contain the full path
        # In this case, the full path needs to be obtained from the map layer
        if footFeat.rfind("/") < 0:
            aprx = arcpy.mp.ArcGISProject("CURRENT")
            m = aprx.activeMap            
            for lyr in m.listLayers():
                if lyr.isFeatureLayer:
                    if footFeat == lyr.name:
                        footFeat = helper.convert_backslach_forwardslach(lyr.dataSource)
                        
       # check that the input feature class is in a correct format
        vecDesc = arcpy.Describe(inFeat)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (inFeat.rfind(".gdb") == -1):
            messages.addErrorMessage("The input featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

       # check that the input head feature class is in a correct format
        vecDesc = arcpy.Describe(headFeat)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (headFeat.rfind(".gdb") == -1):
            messages.addErrorMessage("The input head featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

       # check that the input foot feature class is in a correct format
        vecDesc = arcpy.Describe(footFeat)
        vecType = vecDesc.dataType        
        if (vecType != 'FeatureClass') or (footFeat.rfind(".gdb") == -1):
            messages.addErrorMessage("The input foot featureclass must be a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError

        # check that the output featureclass is in a correct format
        if dissolveFeat.rfind(".gdb") == -1:
            messages.addErrorMessage("The output connected featureclass must be nominated as a feature class in a File GeoDatabase!")
            raise arcpy.ExecuteError
        
        linearUnit =  distThreshold.split(" ")[1]        
        if linearUnit == "Unknown":
            messages.addErrorMessage("You cann't provide an unknown distance unit.")
            raise arcpy.ExecuteError
        
        workspaceName = inFeat[0:inFeat.rfind("/")] 
        env.workspace=workspaceName
        env.overwriteOutput = True

        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        # check the 'featID' field exists
        # if not, add and calculate it
        if 'featID' not in field_names:
            arcpy.AddMessage("Adding an unique featID...")
            helper.addIDField(inFeat,'featID')

        # call the helper function to generate a new list of featID
        # the features to be connected are assigned the same featID
        featIDNewList = helper.findNewFeatIDs_1(inFeat,headFeat,footFeat,distThreshold)
        arcpy.AddMessage('new list of featID generated')

        inFeat1 = 'inFeat1'
        arcpy.Copy_management(inFeat,inFeat1)
        # update the featID
        cursor = arcpy.UpdateCursor(inFeat1)
        i = 0
        for row in cursor:
            featIDNew = featIDNewList[i]
            row.setValue('featID',featIDNew)
            cursor.updateRow(row)
            i += 1
        del cursor,row
        # merge connected features to generate output featureclass
        arcpy.Dissolve_management(inFeat1,dissolveFeat,'featID')
        arcpy.AddMessage('merge done')
        # call the helper function to re-calculate featID the output featureclass
        helper.calculateFeatID(dissolveFeat)
        arcpy.Delete_management(inFeat1)           
        
        return

# the helper functions are defined here
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

    # This function gets unique values in a list
    def getUnique(self,l1):
        # l1: input list
        
        l2 = np.unique(np.asarray(l1)).tolist()
        return l2

    # This function gets the common element(s) between two lists and returns the number of these common element(s)
    def calculateCommon(self,l1,l2):
        # l1: first input list
        # l2: second input list
        
        l1_set = set(l1)
        intersection = l1_set.intersection(l2)
        return len(intersection)

    # This function gets unique values in a 2-D list
    def getUnique2D(self,l1):
        # l1: input 2-D list
        
        l2 = np.unique(np.asarray(l1),axis=0).tolist()
        return l2

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
    
    # This function adds and calculates unique featID field
    def calculateFeatID(self,inFeat):
        # inFeat: input features
        
        fieldName = "featID"
        fieldType = "Long"
        fieldPrecision = 6
        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be recalculated")
        else:    
            arcpy.AddField_management(inFeat,fieldName,fieldType,field_precision=fieldPrecision)
        expression = "!OBJECTID!"
        arcpy.CalculateField_management(inFeat,fieldName,expression)
        return
    # This function deletes a feild from input featureclass
    def deleteField(self,inFeat,fieldName):
        # inFeat: input featureclass
        # fieldName: field to be deleted
        
        fields = arcpy.ListFields(inFeat)
        field_names = [f.name for f in fields]
        if fieldName in field_names:
            arcpy.AddMessage(fieldName + " exists and will be deleted")
            arcpy.DeleteField_management(inFeat,[fieldName])
        else:
            arcpy.AddMessage(fieldName + " does not exist")

        return

    # This function finds the polygon features that connect with each other (e.g, near_dist == 0)
    # and generate a new list of featID, with the connected features being assigned the same featID
    def findNewFeatIDs(self,inFeat,inIDList,nearIDList):
        # inFeat: input polygon features
        # inIDList: list of ids of individual input features that have connected features
        # nearIDList:  this list contains the ids of their nearest features
        
        cursor = arcpy.SearchCursor(inFeat)
        objectIDList = []
        featIDList = []
        for row in cursor:
            objectID = row.getValue("OBJECTID")
            featID = row.getValue("featID")
            featIDList.append(featID)
            objectIDList.append(objectID)
        del cursor,row    

        tempListList = [] # each element list contains ids of connected features e.g. [[1, 3], [1, 2, 3], [4, 9], [2, 3, 5], [6, 13]], first iteration
        anotherList = [] # flatten tempListList
        inIDArr = np.asarray(inIDList)
        inIDArrU = np.unique(inIDArr)
        i = 0
        # loop through each input feature
        while i < len(inIDList):
            tempList = []
            inID = inIDList[i]
            if inID not in anotherList:
                # get the id of its connected feature
                nearID = nearIDList[i]
                tempList.append(inID)  
                tempList.append(nearID)
                tempArr = np.where(inIDArr == nearID)[0] # the index position of the nearID

                for el in tempArr:
                    tempList.append(nearIDList[el])
                tempList = np.unique(np.asarray(tempList)).tolist()            
                tempListList.append(tempList)
                # use the flatten function to convert 2-D list into 1-D list
                anotherList = list(flatten(tempListList))
            i += 1


        tempListList1 = [] # each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]], final results after more merge from tempListList
        tempListListCopy = tempListList.copy() # deep copy
        while len(tempListList) > 0:
            tempList = tempListList[0]
            tempListCopy = tempList.copy()
            
            for tempList1 in tempListListCopy:
                # call the helper function to find the number of common elements bewtween the two lists
                leng = self.calculateCommon(tempListCopy,tempList1)
                if leng > 0:
                    tempListList.remove(tempList1)
                    for el in tempList1:
                        tempListCopy.append(el)           
                    # call the helper function to get the unique values within a list
                    tempList3 = self.getUnique(tempListCopy)
                    tempListCopy = tempList3.copy()
                    
            list1 = list(flatten(tempListCopy))
            list2 = self.getUnique(list1)
            tempListList1.append(list2)    
            tempListListCopy = tempListList.copy()

        # generate a new list of featID
        # the connected features are assigned the same featID
        featIDNewList = featIDList.copy()
        for tempList in tempListList1:    
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = objectIDList.index(idv)
                featureID = featIDList[index]        
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]
        return featIDNewList

    # This function identifies the linear polygon features that can be connected
    # These features satitify the following conditions: 1. the distance between the head of one feature and the foot of another feature is less than a user-defined threshold,
    # 2.the two nearby features align in orientation with the intersecting angle < 45 degree.
    # Finally, this function generate a new list of featID, with the connected features being assigned the same featID
    def findNewFeatIDs_1(self,inFeat,headFeat,footFeat,distThreshold):
        # inFeat: input linear Bathymetric Low features
        # headFeat: input head features
        # footFeat: input foot features
        # distThreshold: a distance threshold used to evaluate the connecting condition
        
        ## connect features that have head to foot distance less than the distance threshold, and intersecting angle less than 45 degree

        ### calculate distances between the head and foot features
        itemList = []

        headFeat1 = 'headFeat1'
        footFeat1 = 'footFeat1'
        itemList.append(headFeat1)
        itemList.append(footFeat1)
        
        arcpy.Copy_management(headFeat,headFeat1)
        arcpy.Copy_management(footFeat,footFeat1)
        
        fieldName = 'featID'
        self.deleteField(headFeat1,fieldName)
        self.deleteField(footFeat1,fieldName)
        
        fieldName = 'rectangle_Orientation'
        self.deleteField(headFeat1,fieldName)
        self.deleteField(footFeat1,fieldName)
        
        headFeat2 = 'headFeat2'
        footFeat2 = 'footFeat2'
        itemList.append(headFeat2)
        itemList.append(footFeat2)
        ## use spatial join to copy the featID and rectangle_Orientation fields to the head and foot features
        arcpy.SpatialJoin_analysis(headFeat1,inFeat,headFeat2)
        arcpy.SpatialJoin_analysis(footFeat1,inFeat,footFeat2)
        # Calculates distances between head and foot features within the input distance threshold (searchRadius) 
        nearTable = 'head_foot_nearTable'
        itemList.append(nearTable)
        location = 'NO_LOCATION'
        angle = 'NO_ANGLE'
        closest = 'ALL'
        searchRadius = distThreshold
        arcpy.GenerateNearTable_analysis(headFeat2,footFeat2,nearTable,search_radius=searchRadius,location=location,angle=angle,closest=closest)

        ### get initial list of a pair of features that have head to foot distance less than the input distance threshold

        headIDList1 = []
        footIDList1 = []
        cursor = arcpy.SearchCursor(nearTable)
        for row in cursor:
            inFID = row.getValue('IN_FID')
            nearFID = row.getValue('NEAR_FID')            
            headIDList1.append(inFID)
            footIDList1.append(nearFID)
        del cursor,row    

        # get  attribute values from the input head features
        headIDAll = []
        headFeatIDAll = []
        headOrientationAll = []
        cursor = arcpy.SearchCursor(headFeat2)
        for row in cursor:
            objectID = row.getValue('OBJECTID')
            featID = row.getValue('featID')
            orientation = row.getValue('rectangle_Orientation')
            headIDAll.append(objectID)
            headFeatIDAll.append(featID)
            headOrientationAll.append(orientation)            
        del cursor, row
        # get  attribute values from the input foot features        
        footIDAll = []
        footFeatIDAll = []
        footOrientationAll = []
        cursor = arcpy.SearchCursor(footFeat2)
        for row in cursor:
            objectID = row.getValue('OBJECTID')
            featID = row.getValue('featID')
            orientation = row.getValue('rectangle_Orientation')
            footIDAll.append(objectID)
            footFeatIDAll.append(featID)
            footOrientationAll.append(orientation)            
        del cursor, row

        headFeatIDList1 = []
        footFeatIDList1 = []
        headOrientationList1 = []
        footOrientationList1 = []
        
        
        for idv in headIDList1:
            featID = headFeatIDAll[headIDAll.index(idv)]
            orientation = headOrientationAll[headIDAll.index(idv)]
            headFeatIDList1.append(featID)
            headOrientationList1.append(orientation)
            
        for idv in footIDList1:
            featID = footFeatIDAll[footIDAll.index(idv)]
            orientation = footOrientationAll[footIDAll.index(idv)]
            footFeatIDList1.append(featID)
            footOrientationList1.append(orientation)  

        ### calculate intersecting angles for the feature pairs
        angleList = []
        i = 0
        while i < len(headOrientationList1):           
            orientation1 = headOrientationList1[i]
            orientation2 = footOrientationList1[i]
            orientation_diff = abs(orientation1-orientation2)
            angleList.append(orientation_diff)
            i += 1

        ### select feature pairs that have intersecting angle less than 45 degree
        idListList1 = []
        headFeatIDList2 = []
        footFeatIDList2 = []
        i = 0
        while i < len(angleList):        
            angle = angleList[i]
            headFeatID = headFeatIDList1[i]
            footFeatID = footFeatIDList1[i]
            if (angle < 45) or (angle > 135):
                idListList1.append([headFeatID,footFeatID])
                headFeatIDList2.append(headFeatID)
                footFeatIDList2.append(footFeatID)
            i += 1

        ### merge feature pairs if they share a common feature
        idListList2 = [] #each element list contains ids of connected features e.g. [[1, 2, 3, 5], [4, 9], [6, 13]],
        i = 0
        headIDArray = np.asarray(headFeatIDList2)
        footIDArray = np.asarray(footFeatIDList2)
        while i < len(idListList1):
            tempList = []
            ids = idListList1[i]
            headID = headFeatIDList2[i]
            footID = footFeatIDList2[i]

            if headFeatIDList2.count(headID) > 1: # if multiple pairs share the same headID (e.g. [1,2],[1,3]), select the feature pair with the minimum intersecting angle
                indices = np.where(headIDArray == headID)[0]
                angleListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                ids1 = idListList1[angleList.index(min(angleListTemp))]
                if ids1 not in idListList2:            
                    idListList2.append(ids1)  
            elif footFeatIDList2.count(footID) > 1: # if multiple pairs share the same footID (e.g. [2,1],[3,1]), select the feature pair with the minimum intersecting angle
                indices = np.where(footIDArray == footID)[0]
                angleListTemp = []
                for index in indices:
                    angle = angleList[index]
                    angleListTemp.append(angle)
                ids1 = idListList1[angleList.index(min(angleListTemp))]
                if ids1 not in idListList2:
                    idListList2.append(ids1)
            elif headID in footFeatIDList2: # if two pairs (e.g., [2,1],[5,2]), indicates the three features are connected, so add both pairs
                ids1 = idListList1[footFeatIDList2.index(headID)]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in idListList2:
                    idListList2.append(tempList)
            elif footID in headFeatIDList2: # if two pairs (e.g., [1,2],[2,5]), indicates the three features are connected, so add both pairs
                ids1 = idListList1[headFeatIDList2.index(footID)]
                tempList.append(ids)
                tempList.append(ids1)
                tempList = self.getUnique(tempList)
                if tempList not in idListList2:
                    idListList2.append(tempList)
            else: # otherwise, just keep the pair
                idListList2.append(ids)
            i += 1

        cursor = arcpy.SearchCursor(inFeat)
        featIDList = []
        for row in cursor:
            featID = row.getValue("featID")
            featIDList.append(featID)
        del cursor,row    


        ### assign a same featID to features to be connected
        featIDNewList = featIDList.copy()
        for tempList in idListList2:    
            indexList = []
            featureIDList = []
            for idv in tempList:
                index = featIDList.index(idv)
                featureID = featIDList[index]        
                indexList.append(index)
                featureIDList.append(featureID)
            for index in indexList:
                featIDNewList[index] = featureIDList[0]

        return featIDNewList
        
    # This function gets a count of feature sharing by borders and merges input features sharing points
    def mergeFeatures(self,inFeat,dissolveFeat,dissolveFeat1,dissolveFeat2):
        # inFeat: input features
        # dissolveFeat: input features after merging features sharing borders and points
        # dissolveFeat1: input features after merging only features sharing borders
        # dissolvedFeat2: output features after merging only features sharing points
        
        itemList = []
        
        # select individual input features that share points and those stand-alone features
        tempLayer = 'tempLyr'
        arcpy.MakeFeatureLayer_management(inFeat, tempLayer) 
        arcpy.SelectLayerByLocation_management(tempLayer, 'ARE_IDENTICAL_TO', dissolveFeat1)
        selectFeat1 = 'selectFeat1'
        itemList.append(selectFeat1)
        arcpy.CopyFeatures_management(tempLayer, selectFeat1)
        arcpy.AddMessage(selectFeat1 + ' done')
        # select dissolved features sharing points and stand-alone features
        tempLayer = 'tempLyr'
        arcpy.MakeFeatureLayer_management(dissolveFeat, tempLayer) 
        arcpy.SelectLayerByLocation_management(tempLayer, 'intersect', selectFeat1)
        selectFeat2 = 'selectFeat2'
        itemList.append(selectFeat2)
        arcpy.CopyFeatures_management(tempLayer, selectFeat2)
        arcpy.AddMessage(selectFeat2 + ' done')
        # select individual input features sharing borders
        tempLayer = 'tempLyr'
        arcpy.MakeFeatureLayer_management(inFeat, tempLayer) 
        arcpy.SelectLayerByLocation_management(tempLayer, 'ARE_IDENTICAL_TO', dissolveFeat1, 
                                               invert_spatial_relationship = 'INVERT')
        selectFeat3 = 'selectFeat3'
        itemList.append(selectFeat3)
        arcpy.CopyFeatures_management(tempLayer, selectFeat3)
        arcpy.AddMessage(selectFeat3 + ' done')
        
        count = int(arcpy.GetCount_management(selectFeat3).getOutput(0))
        # merge features in the second and third sets
        # which results in output features after merging features sharing points
        inFeats = [selectFeat2,selectFeat3]
        arcpy.Merge_management(inFeats,dissolveFeat2)
        itemList.append(tempLayer)
        self.deleteDataItems(itemList)
        return count

