Update Feature Boundary
-----------------------


Two or multiple feature classes may have overlapped polygons.
This tool merges the overlapped polygons into one and update its boundary.

The followings are the steps:

1. Merge the input featureclasses using ArcGIS *Merge* tool . This stacks the polygons on top of each other without dissoving the boundaries
2. Add a *temporay* field to the merged *featureclass* and assin it a single value
3. Dissolve the merged featureclass using ArcGIS *Dissolve* tool, with the *temporary* field and the *SINGLE_PART* option

Note that this accessory tool is clearner than ArcGIS *Update* tool because the duplicates have been removed. In addition, this tool can update feature boundary for more than two input datasets.

.. image:: images/update.png
   :align: center
