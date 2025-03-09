from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QCheckBox, QMessageBox, QFormLayout,
)
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtCore import Qt


class EntityDialog(QDialog):
    def __init__(self, parent=None, title="Add Item", fields=None, data=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 300)
        self.fields = fields or []
        self.data = data or {}
        self.result_data = {}
        self.input_widgets = {}
        self.dependent_widgets = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()  # Make form_layout an instance variable

        # Create input fields based on field definitions
        for field in self.fields:
            field_id = field['id']
            field_type = field.get('type', 'text')
            label_text = field.get('label', field_id.capitalize())
            required = field.get('required', True)
            depends_on = field.get('depends_on', None)

            # Create widgets for all fields
            label = QLabel(f"{label_text}{'*' if required else ''}:")

            if field_type == 'text':
                widget = QLineEdit(self.data.get(field_id, ''))
            elif field_type == 'number':
                widget = QLineEdit(str(self.data.get(field_id, '')))
                widget.setValidator(QDoubleValidator())
            elif field_type == 'integer':
                widget = QLineEdit(str(self.data.get(field_id, '')))
                widget.setValidator(QIntValidator())
            elif field_type == 'checkbox':
                widget = QCheckBox()
                widget.setChecked(bool(self.data.get(field_id, False)))
                widget.stateChanged.connect(self.handle_checkbox_change)
            elif field_type == 'combobox':
                widget = QComboBox()
                if 'options' in field:
                    if callable(field['options']):
                        options = field['options']()
                    else:
                        options = field['options']
                    widget.addItems(options)
                    current_value = self.data.get(field_id, '')
                    if current_value and current_value in options:
                        widget.setCurrentText(current_value)
            else:
                widget = QLineEdit(self.data.get(field_id, ''))

            widget.setObjectName(field_id)
            self.input_widgets[field_id] = widget

            # Store widgets that depend on other fields
            if depends_on:
                dep_field, dep_value = depends_on
                if dep_field not in self.dependent_widgets:
                    self.dependent_widgets[dep_field] = []
                self.dependent_widgets[dep_field].append((field, widget, label))

                # Set initial visibility
                should_be_visible = False
                if dep_field in self.input_widgets:
                    dep_widget = self.input_widgets[dep_field]
                    if isinstance(dep_widget, QCheckBox):
                        should_be_visible = (dep_widget.isChecked() == dep_value)

                # Add to layout but set visibility according to dependency
                self.form_layout.addRow(label, widget)
                label.setVisible(should_be_visible)
                widget.setVisible(should_be_visible)
            else:
                self.form_layout.addRow(label, widget)

        layout.addLayout(self.form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)

        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

    # def setup_ui(self):
    #     layout = QVBoxLayout(self)
    #     form_layout = QFormLayout()
    #
    #     # Create input fields based on field definitions
    #     for field in self.fields:
    #         field_id = field['id']
    #         field_type = field.get('type', 'text')
    #         label_text = field.get('label', field_id.capitalize())
    #         required = field.get('required', True)
    #         depends_on = field.get('depends_on', None)
    #
    #         # Skip fields that depend on other fields (they'll be added dynamically)
    #         if depends_on and not self.data.get(depends_on[0]):
    #             continue
    #
    #         label = QLabel(f"{label_text}{'*' if required else ''}:")
    #
    #         if field_type == 'text':
    #             widget = QLineEdit(self.data.get(field_id, ''))
    #         elif field_type == 'number':
    #             widget = QLineEdit(str(self.data.get(field_id, '')))
    #             widget.setValidator(QDoubleValidator())
    #         elif field_type == 'integer':
    #             widget = QLineEdit(str(self.data.get(field_id, '')))
    #             widget.setValidator(QIntValidator())
    #         elif field_type == 'checkbox':
    #             widget = QCheckBox()
    #             widget.setChecked(bool(self.data.get(field_id, False)))
    #             widget.stateChanged.connect(self.handle_checkbox_change)
    #         elif field_type == 'combobox':
    #             widget = QComboBox()
    #             if 'options' in field:
    #                 if callable(field['options']):
    #                     options = field['options']()
    #                 else:
    #                     options = field['options']
    #                 widget.addItems(options)
    #                 current_value = self.data.get(field_id, '')
    #                 if current_value and current_value in options:
    #                     widget.setCurrentText(current_value)
    #         else:
    #             widget = QLineEdit(self.data.get(field_id, ''))
    #
    #         widget.setObjectName(field_id)
    #         self.input_widgets[field_id] = widget
    #
    #         # Store widgets that depend on other fields
    #         if depends_on:
    #             dep_field, dep_value = depends_on
    #             if dep_field not in self.dependent_widgets:
    #                 self.dependent_widgets[dep_field] = []
    #             self.dependent_widgets[dep_field].append((field, widget, label))
    #         else:
    #             form_layout.addRow(label, widget)
    #
    #     layout.addLayout(form_layout)
    #
    #     # Buttons
    #     button_layout = QHBoxLayout()
    #     save_button = QPushButton("Save")
    #     save_button.clicked.connect(self.accept)
    #     cancel_button = QPushButton("Cancel")
    #     cancel_button.clicked.connect(self.reject)
    #
    #     button_layout.addStretch()
    #     button_layout.addWidget(save_button)
    #     button_layout.addWidget(cancel_button)
    #     layout.addLayout(button_layout)

    def handle_checkbox_change(self):
        sender = self.sender()
        field_id = sender.objectName()

        # Show/hide dependent fields
        if field_id in self.dependent_widgets:
            for field, widget, label in self.dependent_widgets[field_id]:
                if sender.isChecked() == field['depends_on'][1]:
                    label.setVisible(True)
                    widget.setVisible(True)
                else:
                    label.setVisible(False)
                    widget.setVisible(False)

    def accept(self):
        # Validate required fields
        missing_fields = []
        for field in self.fields:
            field_id = field['id']
            if field_id not in self.input_widgets:
                continue

            widget = self.input_widgets[field_id]
            required = field.get('required', True)

            # Skip validation for hidden dependent fields
            depends_on = field.get('depends_on', None)
            if depends_on:
                dep_field, dep_value = depends_on
                dep_widget = self.input_widgets.get(dep_field)
                if dep_widget:
                    if isinstance(dep_widget, QCheckBox) and dep_widget.isChecked() != dep_value:
                        continue

            if required:
                if isinstance(widget, QLineEdit) and not widget.text().strip():
                    missing_fields.append(field.get('label', field_id.capitalize()))
                elif isinstance(widget, QComboBox) and widget.currentText() == "":
                    missing_fields.append(field.get('label', field_id.capitalize()))

        if missing_fields:
            QMessageBox.warning(
                self,
                "Missing Information",
                f"Please fill in the following required fields: {', '.join(missing_fields)}"
            )
            return

        # Collect data from widgets
        for field_id, widget in self.input_widgets.items():
            if isinstance(widget, QLineEdit):
                field_def = next((f for f in self.fields if f['id'] == field_id), {})
                field_type = field_def.get('type', 'text')

                if field_type == 'number':
                    try:
                        self.result_data[field_id] = float(widget.text()) if widget.text() else None
                    except ValueError:
                        self.result_data[field_id] = None
                elif field_type == 'integer':
                    try:
                        self.result_data[field_id] = int(widget.text()) if widget.text() else None
                    except ValueError:
                        self.result_data[field_id] = None
                else:
                    self.result_data[field_id] = widget.text()
            elif isinstance(widget, QComboBox):
                self.result_data[field_id] = widget.currentText()
            elif isinstance(widget, QCheckBox):
                self.result_data[field_id] = widget.isChecked()

        super().accept()

    def get_data(self):
        return self.result_data


def show_entity_dialog(parent, title, fields, data=None):
    """
    Shows a dialog for adding or editing an entity.
    Returns the entered data if accepted, None if canceled.
    """
    dialog = EntityDialog(parent, title, fields, data)
    result = dialog.exec_()
    if result == QDialog.Accepted:
        return dialog.get_data()
    return None