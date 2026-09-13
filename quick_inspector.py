# -*- coding: utf-8 -*-
"""
Quick Inspector - Geometry Inspector universale per QGIS 4.x

    QUICK INSPECTOR
          |
    +-----+-----+------+
    |           |      |
  POINT       LINE   POLYGON
    |           |      |
 Lat/Lon    Lunghezza  Area
 X/Y        Vertici    Perimetro
 CRS        Start/End  Centroide
    |           |      |
    +-----+-----+------+
          |
    COPIA / ESPORTA
          |
   +------+------+
   |      |      |
  WKT  GeoJSON  Coordinate
"""

import os

from qgis.PyQt.QtCore import Qt, QCoreApplication, QSettings, QTranslator
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsApplication

from .inspector_dock_widget import QuickInspectorDockWidget
from .inspector_maptool import InspectorMapTool


def tr(text):
    return QCoreApplication.translate("QuickInspector", text)


class QuickInspector:

    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = os.path.dirname(__file__)

        self.menu = tr("&Quick Inspector")
        self.actions = []

        self.action = None
        self.dock_widget = None
        self.map_tool = None
        self.previous_tool = None
        self.translator = None

    # ------------------------------------------------------------------
    def _load_translation(self):
        """Carica la traduzione QM corrispondente alla lingua di QGIS."""
        locale = QSettings().value("locale/userLocale", "en") or "en"
        locale = str(locale).replace("-", "_")
        language = locale[:2].lower()
        locale_path = os.path.join(self.plugin_dir, "i18n", f"quick_inspector_{language}.qm")
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            if self.translator.load(locale_path):
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        self._load_translation()

        icon_path = os.path.join(self.plugin_dir, "icon.png")
        if os.path.exists(icon_path):
            from qgis.PyQt.QtGui import QIcon
            icon = QIcon(icon_path)
        else:
            icon = QgsApplication.getThemeIcon("/mActionIdentify.svg")

        self.action = QAction(icon, tr("Quick Inspector"), self.iface.mainWindow())
        self.action.setCheckable(True)
        self.action.setStatusTip(tr("Analizza geometria della feature cliccata (Quick Inspector)"))
        self.action.triggered.connect(self.toggle)

        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.actions.append(self.action)

        self.dock_widget = QuickInspectorDockWidget(self.iface, self.iface.mainWindow())
        self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_widget)
        self.dock_widget.hide()
        self.dock_widget.visibilityChanged.connect(self._on_dock_visibility_changed)

        self.map_tool = InspectorMapTool(self.canvas, self.dock_widget, self.iface)
        self.dock_widget.set_capture_callback(self._set_capture_active)

    # ------------------------------------------------------------------
    def toggle(self, checked):
        # L'azione toolbar e il pulsante del dock passano entrambi da qui.
        self._set_capture_active(checked)

    def _set_capture_active(self, active):
        active = bool(active)

        if active:
            # Salva lo strumento precedente solo quando si entra realmente
            # nella modalità cattura, evitando di sovrascriverlo ad ogni sync.
            if self.canvas.mapTool() != self.map_tool:
                self.previous_tool = self.canvas.mapTool()
            self.canvas.setMapTool(self.map_tool)
            self.dock_widget.show()
        else:
            if self.canvas.mapTool() == self.map_tool:
                if self.previous_tool and self.previous_tool != self.map_tool:
                    self.canvas.setMapTool(self.previous_tool)
                else:
                    self.canvas.unsetMapTool(self.map_tool)

        # Sincronizza sempre entrambi i controlli.
        if self.action:
            self.action.blockSignals(True)
            self.action.setChecked(active)
            self.action.blockSignals(False)

        if self.dock_widget:
            self.dock_widget.set_capture_active(active)

    def _on_dock_visibility_changed(self, visible):
        # Chiudere il dock equivale a disattivare la cattura.
        if not visible and self.action and self.action.isChecked():
            self._set_capture_active(False)

    # ------------------------------------------------------------------
    def unload(self):
        if self.translator:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = None

        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)

        if self.canvas.mapTool() == self.map_tool:
            self.canvas.unsetMapTool(self.map_tool)

        if self.dock_widget:
            self.iface.removeDockWidget(self.dock_widget)
            self.dock_widget.deleteLater()
            self.dock_widget = None

        self.map_tool = None
        self.actions = []
