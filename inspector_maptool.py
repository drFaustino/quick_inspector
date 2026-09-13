# -*- coding: utf-8 -*-
"""
Map tool di Quick Inspector.

Al click sulla mappa identifica la feature più in alto sotto il cursore
e ne calcola le informazioni geometriche in base al tipo:

    POINT   -> Lat/Lon, X/Y, CRS
    LINE    -> Lunghezza, Vertici, Punto iniziale/finale
    POLYGON -> Area, Perimetro, Centroide

Le misure di lunghezza/area/perimetro usano QgsDistanceArea con
l'ellissoide del progetto, quindi restano corrette indipendentemente
dal CRS del layer.
"""

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.core import (
    QgsWkbTypes,
    QgsDistanceArea,
    QgsProject,
    QgsCoordinateTransform,
    QgsCoordinateReferenceSystem,
    QgsUnitTypes,
)
from qgis.gui import QgsMapToolIdentify


def tr(text):
    return QCoreApplication.translate("QuickInspector", text)


class InspectorMapTool(QgsMapToolIdentify):

    def __init__(self, canvas, dock_widget, iface):
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock_widget
        self.iface = iface
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ------------------------------------------------------------------
    def canvasReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # In Qt6 i metodi QMouseEvent.x()/y() sono stati rimossi.
        # QgsMapMouseEvent espone ancora pos() (QPoint); in caso contrario
        # si usa position() (QPointF) come fallback.
        if hasattr(event, "pos"):
            pos = event.pos()
        else:
            pos = event.position().toPoint()

        results = self.identify(
            pos.x(),
            pos.y(),
            QgsMapToolIdentify.IdentifyMode.TopDownAll,
            QgsMapToolIdentify.Type.VectorLayer,
        )

        if not results:
            self.dock.show_no_match()
            return

        result = results[0]
        layer = result.mLayer
        feature = result.mFeature
        self._process(layer, feature)

    # ------------------------------------------------------------------
    def _process(self, layer, feature):
        geom = feature.geometry()
        if geom is None or geom.isEmpty():
            self.dock.show_no_match()
            return

        geom_type = QgsWkbTypes.geometryType(geom.wkbType())

        da = QgsDistanceArea()
        da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        da.setEllipsoid(QgsProject.instance().ellipsoid())

        rows = []
        type_label = ""
        coords_text = ""

        try:
            if geom_type == QgsWkbTypes.GeometryType.PointGeometry:
                type_label, coords_text = self._process_point(geom, layer, rows)
            elif geom_type == QgsWkbTypes.GeometryType.LineGeometry:
                type_label, coords_text = self._process_line(geom, da, rows)
            elif geom_type == QgsWkbTypes.GeometryType.PolygonGeometry:
                type_label, coords_text = self._process_polygon(geom, da, rows)
            else:
                self.dock.show_no_match()
                return
        except Exception as exc:
            self.iface.messageBar().pushCritical(tr("Quick Inspector"), tr("Errore analisi geometria: {error}").format(error=exc))
            return

        wkt = geom.asWkt(6)
        geojson_text = geom.asJson(6)

        self.dock.update_feature(layer, feature, type_label, rows, wkt, geojson_text, coords_text)

    # ------------------------------------------------------------------
    # POINT
    # ------------------------------------------------------------------
    def _process_point(self, geom, layer, rows):
        pt = geom.asMultiPoint()[0] if geom.isMultipart() else geom.asPoint()

        rows.append((tr("X"), f"{pt.x():.6f}"))
        rows.append((tr("Y"), f"{pt.y():.6f}"))

        try:
            wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
            transform = QgsCoordinateTransform(layer.crs(), wgs84, QgsProject.instance())
            pt_wgs84 = transform.transform(pt)
            rows.append((tr("Lat"), f"{pt_wgs84.y():.6f}"))
            rows.append((tr("Lon"), f"{pt_wgs84.x():.6f}"))
        except Exception:
            rows.append((tr("Lat/Lon"), tr("non disponibile")))

        rows.append((tr("CRS"), layer.crs().authid()))

        coords_text = f"X: {pt.x():.6f}, Y: {pt.y():.6f}"
        return tr("Punto"), coords_text

    # ------------------------------------------------------------------
    # LINE
    # ------------------------------------------------------------------
    def _process_line(self, geom, da, rows):
        length = da.measureLength(geom)
        length_unit = QgsUnitTypes.toString(da.lengthUnits())

        abstract_geom = geom.constGet()
        vertices = abstract_geom.nCoordinates() if abstract_geom else 0

        line = geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
        start = line[0]
        end = line[-1]

        rows.append((tr("Lunghezza"), f"{length:.3f} {length_unit}"))
        rows.append((tr("Vertici"), str(vertices)))
        rows.append((tr("Punto iniziale"), f"{start.x():.6f}, {start.y():.6f}"))
        rows.append((tr("Punto finale"), f"{end.x():.6f}, {end.y():.6f}"))

        coords_text = "\n".join(f"{p.x():.6f}, {p.y():.6f}" for p in line)
        return tr("Linea"), coords_text

    # ------------------------------------------------------------------
    # POLYGON
    # ------------------------------------------------------------------
    def _process_polygon(self, geom, da, rows):
        area = da.measureArea(geom)
        area_unit = QgsUnitTypes.toString(da.areaUnits())

        perimeter = da.measurePerimeter(geom)
        length_unit = QgsUnitTypes.toString(da.lengthUnits())

        centroid = geom.centroid().asPoint()

        rows.append((tr("Area"), f"{area:.3f} {area_unit}"))
        rows.append((tr("Perimetro"), f"{perimeter:.3f} {length_unit}"))
        rows.append((tr("Centroide"), f"{centroid.x():.6f}, {centroid.y():.6f}"))

        ring = geom.asMultiPolygon()[0][0] if geom.isMultipart() else geom.asPolygon()[0]
        coords_text = "\n".join(f"{p.x():.6f}, {p.y():.6f}" for p in ring)
        return tr("Poligono"), coords_text
