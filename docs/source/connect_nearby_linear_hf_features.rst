Connect Nearby Linear HF Features
---------------------------------


A linear bathymetric low feature (e.g., valley/channel) is sometimes broken into multiple smaller and disconnected features due to several possible reasons: 

*  dificiency in the bathymetric data
*  deficiency in the mapping method
*  natural local processes such as ersosion and desposition

Ideally, these disconnected features should be merged to form a single integrated linear feature to facilitate the subsequent attribute generation and classification.

This tool is used to connect (or merge) two or multiple bathymetric low features through their feet and heads that satitifying a number of conditions based on distance and orientation.

The first step of the process is to identify the head and foot points for each feature.
There are three algorithms available for this step. 

1. The *Mid points to Minimum Bounding Rectangle* algorithm identifies the head and foot points as the middle points on the correponding sides of the minimum bounding rectangle 
2. The *Most distant points on feature* algorithm identifies the head and foot points as the intercepted locations between the feature and the corresponding sides of the minimum bounding rectangle
3. The *Mid points and Most distant points* algorithm identifies two sets of head and foot points

    * The *Mid points* algorithm
    * The *Most distant points* algorithm

The next step is to generate connection links from these head and foot points. These links are created from the feet of each feature to the heads of each of its nearby features that are within the distance threshold.

In the following step, the tool selects a subset of these links based on certain criteria. These criteria are determined by the *distance threshold*, the *angle threshold*, the *distance weight* and the *angle weight*.

In this step, there are 12 link directions to consider when determining which nearby features (if any) should be connected:

.. hlist::
    :columns: 3

    * south-to-north
    * north-to-south
    * west-to-north
    * north-to-west
    * south-to-east
    * east-to-south
    * west-to-east
    * east-to-west
    * south-to-west
    * west-to-south
    * north-to-east
    * east-to-north

For example, for the *west-to-north* link direction considers whether a feature orientated (from the east) to the west with a nearby feature orientated from the north (to the south) should be connected.

Finally, the nearby features identified from this subset of suitable connection links are merged. 

When there are a large number of features in the dataset, the *Area Threshold* and *Length to Width Ratio Threshold* parameters can be used to select a subset of features for the above connection process.

Note that the output featureclasses from the *Merge Connected Features Tool* can be used as the input to this tool. 

.. image:: images/connectHF.png
