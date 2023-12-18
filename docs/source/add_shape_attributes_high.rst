Add Shape Attributes High
-------------------------


This tool add a number of shape attributes to the input bathymetric high feature class as described in :download:`Wirth, M.A. Shape Analysis & Measurement <auxiliary/wirth10.pdf>`.

The following attributes are calculated to describe the polygon shape of each bathymetric high feature.

1. *head_foot_length*: the euclidean distance between two ends of the feature polygon, along the long axis
2. *sinuous_length*: the sinuous distance between two ends of the feature polygon, along the long axis
3. *mean_width*: the mean width of the feature polygon, calculated from a number of cross-sections perpendicular to the orientation of the feature polygon
4. *Compactness*: Describe how compact the feature polygon is. More complex polygon shape has a lower compactness. It is calculated by equation :eq:`compactness`, where *A* is the area of the polygon, *P* is the perimeter of the polygon
5. *Sinuosity*: Describe the sinuosity of the feature polygon. Larger the value more sinuous the feature polygon is. It is calculated by equation :eq:`sinuosity`
6. *LengthWidthRatio*: Describe the length to width ratio of the feature polygon. Larger the value more elongate the feature polygon is. It is calculated by equation :eq:`length-width-ratio`
7. *Circularity*: Describe how close the feature polygon is to a circle. Larger the value closer to a circle the feature polygon is. It is calculated by equation :eq:`circularity`, where *Pc* is the perimeter of the convex hull polygon that bounds the feature polygon. TODO: confirm that it should instead be equation :eq:`circularity2`
8. *Convexity*: Describe the convexity of the feature polygon. More complex polygon has a lower convexity. It is calculated by equation :eq:`convexity`
9. *Solidity*: Describe the solidity of the feature polygon. More complex polygon has a lower solidity.  It is calculated by equation :eq:`solidity`

In addition, a number of intermediate attributes are also calculated.
1. *rectangle_Length*: the length of the bounding rectangle (by width) that bounds the feature polygon
2. *rectangle_Width*: the width of the bounding rectangle (by width) that bounds the feature polygon
3. *rectangle_Orientation*: the orientation of the bounding rectangle (by width) that bounds the feature polygon
4. *convexhull_Area*: the area of the convex hull that bounds the feature polygon
5. *convexhull_Perimeter*: the perimeter of the convex hull that bounds the feature polygon


.. math::
   :label: compactness

   4 * \pi * A / P^2


.. math::
   :label: sinuosity

   sinuous\_length / head\_foot\_length


.. math::
   :label: length-width-ratio

   sinuous\_length / mean\_width


.. math::
   :label: circularity

   4 * \pi / A / Pc^2


.. math::
   :label: circularity2

   \frac{4 * \pi * A}{Pc^2}


.. math::
   :label: convexity

   Pc / P


.. math::
   :label: solidity

   A / Ac


.. image:: images/shape_attributes3.png
   :align: center
