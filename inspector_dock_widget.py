# -*- coding: utf-8 -*-
"""
Dock widget di Quick Inspector.

Mostra le informazioni della geometria selezionata (adattate al tipo:
Punto / Linea / Poligono), la tabella degli attributi della feature e
i pulsanti per copiare/esportare come WKT, GeoJSON o coordinate.
Permette inoltre di modificare l'attributo selezionato tramite un
dialog dedicato con Salva/Annulla.
"""

from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QFileDialog,
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
    QHeaderView,
    QMessageBox,
)

def tr(text):
    return QCoreApplication.translate("QuickInspector", text)


from .attribute_edit_dialog import AttributeEditDialog


class QuickInspectorDockWidget(QDockWidget):

    def __init__(self, iface, parent=None):
        super().__init__(tr("Quick Inspector"), parent)
        self.iface = iface
        self.setObjectName("QuickInspectorDockWidget")

        self._wkt = ""
        self._geojson = ""
        self._coords_text = ""

        self._current_layer = None
        self._current_feature = None
        self._capture_callback = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout(container)

        # --- Cattura ---
        capture_layout = QHBoxLayout()
        self.btn_capture = QPushButton(tr("Attiva cattura"))
        self.btn_capture.setCheckable(True)
        self.btn_capture.setToolTip(
            tr("Attiva/disattiva la cattura sul canvas (cursore a croce)")
        )
        self.btn_capture.toggled.connect(self._on_capture_toggled)
        capture_layout.addWidget(self.btn_capture)

        self.btn_clear = QPushButton(tr("Cancella"))
        self.btn_clear.setToolTip(tr("Cancella tutte le informazioni visualizzate"))
        self.btn_clear.setEnabled(False)
        self.btn_clear.clicked.connect(self._confirm_clear)
        capture_layout.addWidget(self.btn_clear)

        layout.addLayout(capture_layout)

        self.lbl_layer = QLabel(tr("Clicca una feature sulla mappa"))
        self.lbl_layer.setStyleSheet("font-weight: bold;")
        self.lbl_layer.setWordWrap(True)
        layout.addWidget(self.lbl_layer)

        self.lbl_type = QLabel("")
        layout.addWidget(self.lbl_type)

        # --- Informazioni geometria ---
        self.info_group = QGroupBox(tr("Informazioni geometria"))
        self.info_form = QFormLayout()
        self.info_group.setLayout(self.info_form)
        layout.addWidget(self.info_group)

        # --- Attributi ---
        attr_group = QGroupBox(tr("Attributi"))
        attr_layout = QVBoxLayout()

        self.attr_table = QTableWidget(0, 2)
        self.attr_table.setHorizontalHeaderLabels([tr("Campo"), tr("Valore")])
        self.attr_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.attr_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.attr_table.verticalHeader().setVisible(False)
        self.attr_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.attr_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.attr_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        # Più spazio per visualizzare i campi senza dover ridimensionare il dock.
        self.attr_table.setMinimumHeight(280)
        self.attr_table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustIgnored)
        self.attr_table.itemSelectionChanged.connect(self._on_attr_selection_changed)
        self.attr_table.itemDoubleClicked.connect(lambda _item: self._edit_selected_attribute())
        attr_layout.addWidget(self.attr_table)

        self.btn_edit_attr = QPushButton(tr("Modifica attributo selezionato..."))
        self.btn_edit_attr.setEnabled(False)
        self.btn_edit_attr.clicked.connect(self._edit_selected_attribute)
        attr_layout.addWidget(self.btn_edit_attr)

        attr_group.setLayout(attr_layout)
        layout.addWidget(attr_group)

        # --- Copia / Esporta ---
        export_group = QGroupBox(tr("Copia / Esporta"))
        export_layout = QVBoxLayout()

        row1 = QHBoxLayout()
        self.btn_wkt = QPushButton(tr("Copia WKT"))
        self.btn_geojson = QPushButton(tr("Copia GeoJSON"))
        self.btn_coords = QPushButton(tr("Copia Coordinate"))
        row1.addWidget(self.btn_wkt)
        row1.addWidget(self.btn_geojson)
        row1.addWidget(self.btn_coords)
        export_layout.addLayout(row1)

        self.btn_export = QPushButton(tr("Esporta su file..."))
        export_layout.addWidget(self.btn_export)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()
        container.setLayout(layout)
        self.setWidget(container)

        self.btn_wkt.clicked.connect(lambda: self._copy(self._wkt, "WKT"))
        self.btn_geojson.clicked.connect(lambda: self._copy(self._geojson, "GeoJSON"))
        self.btn_coords.clicked.connect(lambda: self._copy(self._coords_text, "Coordinate"))
        self.btn_export.clicked.connect(self._export_to_file)

        self._set_buttons_enabled(False)

    def set_capture_callback(self, callback):
        """Imposta la callback chiamata quando l'utente attiva/disattiva la cattura."""
        self._capture_callback = callback

    def set_capture_active(self, active):
        """Sincronizza lo stato del pulsante con lo strumento sulla toolbar."""
        self.btn_capture.blockSignals(True)
        self.btn_capture.setChecked(bool(active))
        self.btn_capture.blockSignals(False)
        self.btn_capture.setText(tr("Disattiva cattura") if active else tr("Attiva cattura"))

    def _on_capture_toggled(self, checked):
        self.set_capture_active(checked)
        if self._capture_callback:
            self._capture_callback(checked)

    def _set_buttons_enabled(self, enabled):
        for btn in (self.btn_wkt, self.btn_geojson, self.btn_coords, self.btn_export):
            btn.setEnabled(enabled)
        self.btn_clear.setEnabled(enabled)
        if not enabled:
            self.btn_edit_attr.setEnabled(False)

    def _confirm_clear(self):
        if self._current_feature is None and self.attr_table.rowCount() == 0 and self.info_form.rowCount() == 0:
            return

        reply = QMessageBox.question(
            self,
            tr("Conferma cancellazione"),
            tr("Vuoi cancellare tutte le informazioni visualizzate?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.clear()

    # ------------------------------------------------------------------
    # Azioni copia / esporta
    # ------------------------------------------------------------------
    def _copy(self, text, label):
        if not text:
            return
        QApplication.clipboard().setText(text)
        self.iface.messageBar().pushSuccess(tr("Quick Inspector"), tr("{label} copiato negli appunti").format(label=label))

    def _export_to_file(self):
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            tr("Esporta geometria"),
            "",
            tr("GeoJSON (*.geojson);;WKT (*.wkt);;Testo coordinate (*.txt)"),
        )
        if not path:
            return
        try:
            if path.lower().endswith(".geojson"):
                content = self._geojson
            elif path.lower().endswith(".wkt"):
                content = self._wkt
            else:
                content = self._coords_text
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.iface.messageBar().pushSuccess(tr("Quick Inspector"), tr("Esportato in: {path}").format(path=path))
        except Exception as exc:
            self.iface.messageBar().pushCritical(tr("Quick Inspector"), tr("Errore esportazione: {error}").format(error=exc))

    # ------------------------------------------------------------------
    # Attributi
    # ------------------------------------------------------------------
    def _on_attr_selection_changed(self):
        self.btn_edit_attr.setEnabled(bool(self.attr_table.selectedItems()))

    def _populate_attributes(self, feature):
        self.attr_table.setRowCount(0)
        fields = feature.fields()
        for idx, field in enumerate(fields):
            row = self.attr_table.rowCount()
            self.attr_table.insertRow(row)

            name_item = QTableWidgetItem(field.name())
            name_item.setData(Qt.ItemDataRole.UserRole, idx)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            value = feature.attribute(idx)
            value_item = QTableWidgetItem("" if value is None else str(value))
            value_item.setFlags(value_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.attr_table.setItem(row, 0, name_item)
            self.attr_table.setItem(row, 1, value_item)

    def _edit_selected_attribute(self):
        if self._current_layer is None or self._current_feature is None:
            return

        selected_rows = self.attr_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        field_index = self.attr_table.item(row, 0).data(Qt.ItemDataRole.UserRole)

        layer = self._current_layer
        feature = self._current_feature
        field = feature.fields().at(field_index)
        current_value = feature.attribute(field_index)

        dialog = AttributeEditDialog(field, current_value, self)
        if dialog.exec() != AttributeEditDialog.DialogCode.Accepted:
            return

        new_value = dialog.value()
        self._apply_attribute_change(layer, feature, field_index, new_value, row)

    def _apply_attribute_change(self, layer, feature, field_index, new_value, table_row):
        was_editable = layer.isEditable()

        if not was_editable:
            if not layer.startEditing():
                QMessageBox.critical(
                    self, tr("Quick Inspector"), tr("Impossibile avviare la modifica sul layer.")
                )
                return

        success = layer.changeAttributeValue(feature.id(), field_index, new_value)

        if not success:
            layer.rollBack()
            QMessageBox.critical(
                self, tr("Quick Inspector"), tr("Impossibile modificare l'attributo selezionato.")
            )
            return

        if not layer.commitChanges():
            errors = "\n".join(layer.commitErrors())
            QMessageBox.critical(
                self, tr("Quick Inspector"), tr("Errore durante il salvataggio:\n{errors}").format(errors=errors)
            )
            layer.rollBack()
            return

        # Aggiorna la cache locale della feature e la tabella visualizzata
        feature.setAttribute(field_index, new_value)
        value_item = self.attr_table.item(table_row, 1)
        value_item.setText("" if new_value is None else str(new_value))

        self.iface.messageBar().pushSuccess(tr("Quick Inspector"), tr("Attributo aggiornato correttamente"))
        layer.triggerRepaint()

    # ------------------------------------------------------------------
    # Aggiornamento contenuti
    # ------------------------------------------------------------------
    def _clear_form(self):
        while self.info_form.rowCount():
            self.info_form.removeRow(0)

    def clear(self):
        self.lbl_layer.setText(tr("Clicca una feature sulla mappa"))
        self.lbl_type.setText("")
        self._clear_form()
        self.attr_table.setRowCount(0)
        self._wkt = ""
        self._geojson = ""
        self._coords_text = ""
        self._current_layer = None
        self._current_feature = None
        self._set_buttons_enabled(False)

    def show_no_match(self):
        self.clear()
        self.lbl_layer.setText(tr("Nessuna feature trovata in quel punto"))

    def update_feature(self, layer, feature, geom_type_label, rows, wkt, geojson_text, coords_text):
        self.lbl_layer.setText(tr("Layer: {layer}   |   Feature ID: {feature_id}").format(layer=layer.name(), feature_id=feature.id()))
        self.lbl_type.setText(tr("Tipo geometria: {geometry_type}").format(geometry_type=geom_type_label))

        self._clear_form()
        for label, value in rows:
            self.info_form.addRow(QLabel(f"{label}:"), QLabel(str(value)))

        self._populate_attributes(feature)

        self._wkt = wkt
        self._geojson = geojson_text
        self._coords_text = coords_text

        self._current_layer = layer
        self._current_feature = feature

        self._set_buttons_enabled(True)
