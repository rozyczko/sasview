from PySide6 import QtGui
from PySide6.QtGui import QColor, QIntValidator, QPalette, Qt
from PySide6.QtWidgets import QAbstractScrollArea, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QApplication
from PySide6.QtCore import Slot
from warning_label import WarningLabel
from col_editor import ColEditor
from row_status_widget import RowStatusWidget
from guess import guess_column_count, guess_columns, guess_seperator, guess_starting_position
from os import path
from dataset_types import DatasetType, dataset_types, one_dim, two_dim, sesans
import re

TABLE_MAX_ROWS = 100

class AsciiDialog(QWidget):
    def __init__(self):
        super().__init__()

        self.raw_csv = None

        self.seperators = {
            'Comma': True,
            'Whitespace': True,
            'Tab': True
        }

        self.filename_label = QLabel("Click the button below to load a file.")

        self.load_button = QPushButton("Load File")
        self.load_button.clicked.connect(self.load)

        # Data parameters

        ## Dataset type selection
        self.dataset_layout = QHBoxLayout()
        self.dataset_label = QLabel("Dataset Type")
        self.dataset_combobox = QComboBox()
        for name in dataset_types:
            self.dataset_combobox.addItem(name)
        self.dataset_layout.addWidget(self.dataset_label)
        self.dataset_layout.addWidget(self.dataset_combobox)

        ## Seperator
        self.sep_layout = QHBoxLayout()

        self.sep_widgets = []
        self.sep_label = QLabel('Seperators:')
        self.sep_layout.addWidget(self.sep_label)
        for seperator_name, value in self.seperators.items():
            check_box = QCheckBox(seperator_name)
            check_box.setChecked(value)
            check_box.clicked.connect(self.seperator_toggle)
            self.sep_widgets.append(check_box)
            self.sep_layout.addWidget(check_box)

        ## Starting Line
        self.startline_layout = QHBoxLayout()
        self.startline_label = QLabel('Starting Line')
        self.startline_entry = QSpinBox()
        self.startline_entry.valueChanged.connect(self.update_startpos)
        self.startline_layout.addWidget(self.startline_label)
        self.startline_layout.addWidget(self.startline_entry)

        ## Column Count
        self.colcount_layout = QHBoxLayout()
        self.colcount_label = QLabel('Number of Columns')
        self.colcount_entry = QSpinBox()
        self.colcount_entry.setMinimum(1)
        self.colcount_entry.valueChanged.connect(self.update_colcount)
        self.colcount_layout.addWidget(self.colcount_label)
        self.colcount_layout.addWidget(self.colcount_entry)

        ## Column Editor
        current_dataset_type = self.current_dataset_type()
        options =  current_dataset_type.required + current_dataset_type.optional
        self.col_editor = ColEditor(self.colcount_entry.value(), options)
        self.dataset_combobox.currentTextChanged.connect(self.change_dataset_type)
        self.col_editor.column_changed.connect(self.update_column)

        ## Data Table

        self.table = QTableWidget()
        self.table.show()
        # Make the table readonly
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)

        # Warning Label
        self.warning_label = WarningLabel(self.required_missing(), self.duplicate_columns())

        self.layout = QVBoxLayout(self)

        self.layout.addWidget(self.filename_label)
        self.layout.addWidget(self.load_button)
        self.layout.addLayout(self.dataset_layout)
        self.layout.addLayout(self.sep_layout)
        self.layout.addLayout(self.startline_layout)
        self.layout.addLayout(self.colcount_layout)
        self.layout.addWidget(self.col_editor)
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.warning_label)

        self.row_status_widgets: list[Qt.CheckState] = []

    def split_line(self, line: str) -> list[str]:
        expr = ''
        for seperator, isenabled in self.seperators.items():
            if expr != r'':
                expr += r'|'
            if isenabled:
                match seperator:
                    case 'Comma':
                        seperator_text = r','
                    case 'Whitespace':
                        seperator_text = r'\s+'
                    case 'Tab':
                        seperator_text = r'\t'
                expr += seperator_text

        return re.split(expr, line)

    def attempt_guesses(self):
        # TODO: We're not guessing seperators anymore (just presuming that they
        # are all enabled). Can probably delete this code later.
        #
        # guessed_seperator = guess_seperator(self.raw_csv)
        # if guessed_seperator == None:
        #     # Seperator couldn't be guessed; just let the user fill that in.
        #     guessed_seperator = ''

        # self.sep_entry.setText(guessed_seperator)

        split_csv = [self.split_line(line.strip()) for line in self.raw_csv]

        self.initial_starting_pos = guess_starting_position(split_csv)

        guessed_colcount = guess_column_count(split_csv,
                                              self.initial_starting_pos)
        self.col_editor.set_cols(guessed_colcount)

        columns = guess_columns(guessed_colcount, self.current_dataset_type())
        self.col_editor.set_col_order(columns)
        self.colcount_entry.setValue(guessed_colcount)
        self.startline_entry.setValue(self.initial_starting_pos)

    def guess_row_status(self, row) -> Qt.CheckState:
        if row < self.initial_starting_pos:
            return Qt.CheckState.PartiallyChecked
        else:
            return Qt.CheckState.Checked

    def fill_table(self):
        # At the moment, we're just going to start making the table from where
        # the user told us to start. Just trying this for now. We might want to
        # draw the full table later.

        # Don't try to fill the table if there's no data.
        if self.raw_csv is None:
            return

        self.table.clear()

        starting_pos = self.startline_entry.value()
        col_count = self.colcount_entry.value()

        self.table.setRowCount(min(len(self.raw_csv) - starting_pos, TABLE_MAX_ROWS))
        self.table.setColumnCount(col_count + 1)
        self.table.setHorizontalHeaderLabels(["Included"] + self.col_editor.col_names())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Now fill the table with data
        for i, row in enumerate(self.raw_csv):
            if i < len(self.row_status_widgets):
                initial_state = self.row_status_widgets[i]
            else:
                initial_state = self.guess_row_status(i)
                self.row_status_widgets.append(initial_state)
            row_status = RowStatusWidget(initial_state, i)
            row_status.status_changed.connect(self.update_row_status)
            self.table.setCellWidget(i, 0, row_status)
            row_split = self.split_line(row)
            for j, col_value in enumerate(row_split):
                if j >= col_count:
                    continue # Ignore rows that have extra columns.
                item = QTableWidgetItem(col_value)
                # if initial_state == Qt.CheckState.PartiallyChecked:
                #     item.setForeground(QColor.fromString('grey'))
                # elif initial_state == Qt.CheckState.Unchecked:
                #     item.setForeground(QColor.fromString('grey'))
                #     item_font = item.font()
                #     item_font.setStrikeOut(True)
                #     item.setFont(item_font)
                #     item.font().setStrikeOut(True)
                self.table.setItem(i, j + 1, item)
            if i == TABLE_MAX_ROWS:
                break

        self.table.show()
        for row in range(self.table.rowCount()):
            self.set_row_typesetting(row, self.row_status_widgets[row])

    def current_dataset_type(self) -> DatasetType:
        # TODO: Using linear search but should probably just use a dictionary
        # later.
        for type in [one_dim, two_dim, sesans]:
            if type.name == self.dataset_combobox.currentText():
                return type
        return one_dim

    def set_row_typesetting(self, row, row_status: Qt.CheckState):
        for column in range(1, self.table.columnCount() + 1):
            item = self.table.item(row, column)
            if item is None:
                continue
            match row_status:
                case Qt.CheckState.PartiallyChecked:
                    item.setForeground(QColor.fromString('grey'))
                case Qt.CheckState.Unchecked:
                    item.setForeground(QColor.fromString('grey'))
                    item_font = item.font()
                    item_font.setStrikeOut(True)
                    item.setFont(item_font)


    @Slot()
    def load(self):
        result = QFileDialog.getOpenFileName(self)
        # Happens when the user cancels without selecting a file. There isn't a
        # file to load in this case.
        if result[1] == '':
            return
        filename = result[0]
        self.filename_label.setText(path.basename(filename))

        # TODO: Add error handling
        with open(filename) as file:
            self.raw_csv = file.readlines()

        self.attempt_guesses()
        self.fill_table()

    @Slot()
    def update_colcount(self):
        self.col_editor.set_cols(self.colcount_entry.value())
        self.fill_table()

    @Slot()
    def update_startpos(self):
        self.fill_table()

    @Slot()
    def update_seperator(self):
        self.fill_table()

    @Slot()
    def update_column(self):
        self.fill_table()
        required_missing = self.required_missing()
        duplicates = self.duplicate_columns()
        self.warning_label.update(required_missing, duplicates)

    @Slot()
    def seperator_toggle(self):
        check_box = self.sender()
        self.seperators[check_box.text()] = check_box.isChecked()
        self.fill_table()

    @Slot()
    def change_dataset_type(self):
        new_dataset = self.current_dataset_type()
        self.col_editor.replace_options(new_dataset.required + new_dataset.optional)

        # Update columns as they'll be different now.
        columns = guess_columns(self.colcount_entry.value(), self.current_dataset_type())
        self.col_editor.set_col_order(columns)

    @Slot()
    def update_row_status(self, row):
        new_status = self.table.cellWidget(row, 0).checkState()
        self.row_status_widgets[row] = new_status
        self.set_row_typesetting(row, new_status)

    def required_missing(self) -> list[str]:
        dataset = self.current_dataset_type()
        missing_columns = [col for col in dataset.required if col not in self.col_editor.col_names()]
        return missing_columns

    def duplicate_columns(self) -> list[str]:
        col_names = self.col_editor.col_names()
        return [col for col in col_names if col_names.count(col) > 1]

    def set_required_error(self, required_missing):
        self.warning_label.setText(f'The following columns are missing: {required_missing}')
        self.warning_label.setStyleSheet("QLabel { color: red}")

if __name__ == "__main__":
    app = QApplication([])

    widget = AsciiDialog()
    widget.show()


    exit(app.exec())
