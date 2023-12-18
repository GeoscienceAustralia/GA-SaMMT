TPI Tool Bathymetric Low
------------------------


This tool maps bathymetric low features from a bathymetric data using a Topographic Position Index (TPI) :cite:`Weiss2001TopographicPA` based method.
Negative TPI usually indicates bathymetric low location.

The followings are the key steps of this tool:

1. Calculate TPI from the input bathymetry raster using the *TPI Circle Radius* parameter
2. Calculate the TPI threshold using this equation :eq:`tpi-threshold`, where *c* is the *TPI STD Scale* parameter, *mean_TPI* and *STD_TPI* are the mean and standard deviation statistics of the TPI raster. The TPI threshold should always have a negative value
3. Select locations that have TPI values smaller than the TPI threshold
4. Convert the selected areas into polygons
5. Remove the polygons with areas smaller than the *Area Threshold* parameter to obtain the final set of bathymetric low features as output

The TPI radius should be large enough to capture the largest bathymetric low features in the dataset.
For example, for a 5m resolution bathymetry raster, a radius of 50 cells should be used to capture any bathymetric  low features that is smaller than 500m in length.
Users should also experiment the *TPI STD Scale* and the *Area Threshold* parameters to obtain an optimal output solution. 


.. image:: images/TPI.png
   :align: center