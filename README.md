# GA-SaMMT
Geoscience Australia's Semi-automated Morphological Mapping Tools (GA-SaMMT) for Seabed Characterisation

Seabed characterisation requires the measurement, description and classification of physical features on the seabed.
A key first step in this process is the identification of morphological forms, as derived from bathymetric data.
To facilitate rapid and consistent morphological mapping, Geoscience Australia has developed several semi-automated ArcGIS toolboxes that:

* Generate polygons from bathymetry surfaces that represent *bathymetric high* and *bathymetric low* seabed features
* Calculate metrics/attributes to describe the characteristics of the polygons
* Classify individual polygons into one of the bathymetric *high* or *low* seabed morphological features

The toolboxes adopt the suite of terms as presented in the glossary of seabed morphology deatures defined by [Dove, D., Nanson, R., Bjarnadóttir, L., Guinan, J., Gafeira, J., Post, A., Dolan, M.; Stewart, H.; Arosio, R, Scott, G.. (2020). A two-part seabed geomorphology classification scheme (v.2); Part 1: morphology features glossary. Zenodo.](http://doi.org/10.5281/zenodo.4075248).

## Toolboxes
The ESRI [toolboxes](./Tools) contains six Python toolboxes:

* BathymetricHigh is used to map bathymetric high features and contains:
    * TPI Tool Bathymetric High
    * TPI LMI Tool Bathymetric High
    * Openness Tool Bathymetric High
* BathymetricLow is used to map bathymetric low features and contains:
    * TPI Tool Bathymetric Low
    * TPI CI Tool Bathymetric Low
    * Openness Tool Bathymetric Low
* AddAttributes is used to calculate attributes for bathymetric high and low features and contains:
    * Add Shape Attributes High Tool
    * Add Shape Attributes Low Tool
    * Add Topographic Attributes High Tool
    * Add Topographic Attributes Low Tool
    * Add Profile Attributes High Tool
    * Add Profile Attributes Low Tool
* ClassificationFeature is used to classify bathymetric high and low features into morphological categories as defined by [Dove et al](http://doi.org/10.5281/zenodo.4075248) and contains:
    * Classify Bathymetric High Features
    * Classify Bathymetric Low Features
* Accessory_Tools is used to help the mapping processes and contains:
    * Merge Connected Features Tool
    * Connect Nearby Linear Features Tool
    * Connect Nearby Linear HF Features Tool
    * Update Feature Boundary
* Surface is used to map three-class morophological surface and contains:
    * Morphological Surface Tool Bathymetry
    * Morphological Surface Tool Slope

## User guide
See the [user guide](./User_Guide/GA-SaMMT_v1p2_user_guide.pdf) for a tutorial and walkthrough of the toolsets.


## Publication and sample data

See [here](https://dx.doi.org/10.26186/146832) for additional details including sample datasets.
