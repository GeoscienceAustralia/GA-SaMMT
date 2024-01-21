TPI Tool Bathymetric Low
------------------------


This tool maps bathymetric low features from bathymetry data using a Topographic Position Index (TPI) :cite:`Weiss2001TopographicPA` based method.
Negative TPI usually indicates bathymetric low location.

The followings are the key steps of this tool:

1. Calculate TPI from the input bathymetry raster using the *TPI Circle Radius* parameter
2. Calculate the TPI threshold using this equation :eq:`tpi-threshold-low`, where *c* is the *TPI STD Scale* parameter, *mean_TPI* and *STD_TPI* are the mean and standard deviation statistics of the TPI raster. The TPI threshold should always have a negative value

   .. math::
     :label: tpi-threshold-low
 
     TPI\_threshold = mean\_TPI - c * STD\_TPI

3. Select locations that have TPI values smaller than the TPI threshold
4. Convert the selected areas into polygons
5. Remove the polygons with areas smaller than the *Area Threshold* parameter to obtain the final set of bathymetric low features as output

The TPI radius should be large enough to capture the largest bathymetric low features in the dataset.
For example, for a 5m resolution bathymetry raster, a radius of 50 cells should be used to capture any bathymetric  low features that is smaller than 500m in length.
Users should also experiment the *TPI STD Scale* and the *Area Threshold* parameters to obtain an optimal output solution. 


.. image:: images/TPI.png
   :align: center


.. code-block:: python
   :linenos:

   from arcpy import env
   from arcpy.sa import *
   arcpy.CheckOutExtension("Spatial")
   
   # import the python toolbox
   arcpy.ImportToolbox("C:/semi_automation_tools/User_Guide/Tools/BathymetricLow.pyt")
   
   env.workspace = 'C:/semi_automation_tools/testSampleCode/Gifford.gdb'
   env.overwriteOutput = True
   
   # specify input and output parameters of the tool
   inBathy = 'gifford_bathy'
   outTPI = 'gifford_tpi10'
   outFeat = 'tpi10_1std_300000m2_BL'
   areaT = '300000 SquareMeters'
   tpiRadius = 10
   tpiSTD = 1.0
   tempWorkspace = 'C:/Users/u56061/Documents/ArcGIS/Projects/UserGuide/UserGuide.gdb' 
   
   # execute the tool
   arcpy.BathymetricLow.TPIToolLow(inBathy,outTPI,outFeat,areaT,tpiRadius,tpiSTD,tempWorkspace)
