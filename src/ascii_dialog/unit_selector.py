from PySide6.QtCore import Slot
from PySide6.QtWidgets import QApplication, QComboBox, QDialog, QLineEdit, QPushButton, QVBoxLayout
from sasdata.quantities.units import NamedUnit, UnitGroup, unit_group_names, unit_groups

from unit_list_widget import UnitListWidget

all_unit_groups = list(unit_groups.values())

class UnitSelector(QDialog):
    def current_unit_group(self) -> UnitGroup:
        index = self.unit_type_selector.currentIndex()
        return all_unit_groups[index]

    @property
    def selected_unit(self) -> NamedUnit | None:
        return self.unit_list_widget.selected_unit

    @Slot()
    def on_search_changed(self):
        search_input = self.search_box.text()
        current_group = self.current_unit_group()
        units = current_group.units
        if search_input != '':
            units = [unit for unit in units if search_input.lower() in unit.name]
        self.unit_list_widget.populate_list(units)


    @Slot()
    def unit_group_changed(self):
        new_group = self.current_unit_group()
        self.search_box.setText('')
        self.unit_list_widget.populate_list(new_group.units)

    @Slot()
    def select_unit(self):
        self.accept()

    @Slot()
    def selection_changed(self):
        self.select_button.setDisabled(False)

    def __init__(self, default_group='length', allow_group_edit=True):
        super().__init__()

        self.unit_type_selector = QComboBox()
        self.unit_type_selector.addItems(unit_group_names)
        self.unit_type_selector.setCurrentText(default_group)
        if not allow_group_edit:
            self.unit_type_selector.setDisabled(True)
        self.unit_type_selector.currentTextChanged.connect(self.unit_group_changed)

        self.search_box = QLineEdit()
        self.search_box.textChanged.connect(self.on_search_changed)
        self.search_box.setPlaceholderText('Search for a unit...')

        self.unit_list_widget = UnitListWidget()
        # TODO: Are they all named units?
        self.unit_list_widget.populate_list(self.current_unit_group().units)
        self.unit_list_widget.itemSelectionChanged.connect(self.selection_changed)

        self.select_button = QPushButton('Select Unit')
        self.select_button.pressed.connect(self.select_unit)
        self.select_button.setDisabled(True)

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.unit_type_selector)
        self.layout.addWidget(self.search_box)
        self.layout.addWidget(self.unit_list_widget)
        self.layout.addWidget(self.select_button)

if __name__ == "__main__":
    app = QApplication([])

    widget = UnitSelector()
    widget.exec()
    print(widget.selected_unit)

    exit()
