#!/usr/bin/env python3

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from h5py import File as H5File, HLObject
from h5py import Group as H5Group
from h5py import Dataset
from h5py._hl.group import Group

class Hd5TreeWidget(QTreeWidget):
    selection_changed = Signal()

    def __init__(self, hd5_file: H5File):
        super().__init__()
        self.header().setVisible(False)
        self.hd5_file: H5File = hd5_file

        # While the items in this list are already contained din the hd5_file,
        # the ordering of them in this list is important because it will be
        # needed to retrieve items based on what the current index selected is.
        self.h5_items: list[HLObject] = []

        self.currentItemChanged.connect(self.selection_changed)

    def __add_to_tree__(self, root: QTreeWidgetItem, group: H5Group):
        for name, group_item in group.items():
            self.h5_items.append(group_item)
            if isinstance(group_item, Group):
                new_tree_item = QTreeWidgetItem(root, [name])
                new_tree_item.setData(0, Qt.ItemDataRole.UserRole, group_item)
                self.__add_to_tree__(new_tree_item, group_item)
            elif isinstance(group_item, Dataset):
                # TODO: Might be able to reduce code duplication here.
                new_tree_item = QTreeWidgetItem(root, [name])
                new_tree_item.setData(0, Qt.ItemDataRole.UserRole, group_item)

    @property
    def selected_item(self) -> HLObject:
        return self.currentItem().data(0, Qt.ItemDataRole.UserRole)

    def update_tree(self):
        self.h5_items = []
        self.__add_to_tree__(self.invisibleRootItem(), self.hd5_file.parent)
