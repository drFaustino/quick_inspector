# -*- coding: utf-8 -*-
"""
Dialog di modifica attributo di Quick Inspector.

Finestra modale con un campo per modificare il valore dell'attributo
selezionato e i pulsanti Salva / Annulla. La conversione del valore
al tipo del campo (intero, reale, testo, booleano) si basa sul nome
del tipo (QgsField.typeName()) invece che sull'enum QVariant, per
restare compatibile sia con le API legacy (QVariant) sia con quelle
basate su QMetaType introdotte con Qt6 / QGIS 4.x.
"""

from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QMessageBox,
)
from qgis.PyQt.QtCore import QCoreApplication


def tr(text):
    return QCoreApplication.translate("QuickInspector", text)



def _classify_field(field):
    """Restituisce 'bool', 'int', 'double' o 'string' in base al tipo del campo."""
    type_name = (field.typeName() or "").lower()

    if "bool" in type_name:
        return "bool"
    if any(key in type_name for key in ("real", "double", "float", "numeric", "decimal")):
        return "double"
    if any(key in type_name for key in ("int", "long", "short")):
        return "int"
    return "string"


class AttributeEditDialog(QDialog):
    """Dialog per la modifica di un singolo attributo di una feature."""

    def __init__(self, field, current_value, parent=None):
        super().__init__(parent)
        self.field = field
        self._kind = _classify_field(field)
        self._result_value = None

        self.setWindowTitle(tr("Modifica attributo: {field}").format(field=field.name()))
        self.setMinimumWidth(320)

        self._build_ui(current_value)

    # ------------------------------------------------------------------
    def _build_ui(self, current_value):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.addRow(QLabel(tr("Campo:")), QLabel(f"<b>{self.field.name()}</b>"))
        form.addRow(QLabel(tr("Tipo:")), QLabel(self.field.typeName()))

        if self._kind == "bool":
            self.editor = QCheckBox()
            self.editor.setChecked(bool(current_value) if current_value is not None else False)
        else:
            self.editor = QLineEdit()
            self.editor.setText("" if current_value is None else str(current_value))

        form.addRow(QLabel(tr("Nuovo valore:")), self.editor)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("Salva"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("Annulla"))
        buttons.accepted.connect(self._on_save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    def _on_save(self):
        raw_text = None

        try:
            if self._kind == "bool":
                value = self.editor.isChecked()
            else:
                raw_text = self.editor.text().strip()
                if raw_text == "":
                    value = None
                elif self._kind == "int":
                    value = int(raw_text)
                elif self._kind == "double":
                    value = float(raw_text)
                else:
                    value = raw_text
        except (ValueError, TypeError):
            QMessageBox.warning(
                self,
                tr("Valore non valido"),
                tr("Il valore '{value}' non è compatibile con il tipo di campo '{field_type}'.").format(value=raw_text, field_type=self.field.typeName()),
            )
            return

        self._result_value = value
        self.accept()

    # ------------------------------------------------------------------
    def value(self):
        """Restituisce il nuovo valore confermato (None se annullato)."""
        return self._result_value
