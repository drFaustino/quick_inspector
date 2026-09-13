# Quick Inspector

Universal Geometry Inspector for QGIS 4.x (Qt6).

```
                                    QUICK INSPECTOR
                                          |
          +---------------+--------------+--------------+---------------+
          |                              |                              |
        POINT                          LINE                          POLYGON
          |                              |                              |
       Lat/Lon                        Length                          Area
       X/Y                            Vertices                        Perimetre
       CRS                            Start/End                       Centroid
          |                              |                              |
          +---------------+--------------+--------------+---------------+
                                          |
                                    COPY / EXPORT
                                          |
                    +---------------------+---------------------+
                    |                     |                     |
                   WKT                GeoJSON               Coordinate
```

## Installation

1. Compress the quick_inspector folder into a .zip file (a ready-to-use archive is already provided: quick_inspector.zip)..
2. In QGIS, go to **Plugins → Manage and Install Plugins → Install from ZIP**.
3. Select the ZIP file and click **Install Plugin**.
4. If the plugin is not enabled automatically, activate it from the plugin list.


## Usage

1. Click the **Quick Inspector** icon in the toolbar (or access it from the **Plugins** menu).
2. The side panel opens and the cursor changes to a crosshair.
3. Click any feature (point, line, or polygon) in a visible vector layer.
4. The panel displays geometry-specific information:
  - **Point**: X/Y coordinates, latitude/longitude (WGS84), and the layer CRS.
  - **Line**: length, vertex count, and start/end coordinates.
  - **Polygon**: area, perimeter, and centroid.
The panel also displays the feature's **attribute table**. Select a row (or double-click it) and click **Edit selected attribute**... to open the editing dialog. Change the value and click **Save**, or click **Cancel** to discard the changes. The layer is automatically switched to edit mode, and changes are committed immediately after saving.
Use the buttons at the bottom to copy the geometric information as WKT, GeoJSON, or a coordinate list, or export it directly to a file.

Length, area, and perimeter measurements are calculated using **QgsDistanceArea** and the project's ellipsoid, ensuring accurate results even when working with layers in different projected or geographic CRSs.

## Technical Notes

- Compatible with QGIS 4.x / Qt6 (using qgis.PyQt as the compatibility layer, with PyQt6 scoped enums handled correctly, e.g. Qt.MouseButton.LeftButton).
- No external dependencies are required beyond the standard PyQGIS API.
- Multipart geometries are supported (multipoints, multilines, and multipolygons); the first part is analyzed.
- Attribute editing detects the field type using QgsField.typeName() (integer/real/boolean/string) and automatically converts the entered value, reporting conversion errors before saving.
- If the layer was not already in edit mode, Quick Inspector automatically starts an edit session and commits the changes after saving. In case of an error, the changes are rolled back.
