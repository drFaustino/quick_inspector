# -*- coding: utf-8 -*-
"""
Quick Inspector
---------------
Geometry Inspector universale per QGIS 4.x.

Questo file espone la classFactory richiesta da QGIS per caricare il plugin.
"""


def classFactory(iface):
    from .quick_inspector import QuickInspector
    return QuickInspector(iface)
