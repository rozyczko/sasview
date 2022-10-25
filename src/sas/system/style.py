import os
import pkg_resources
import sys

from sas.system import user, config



class StyleSheet:
    """
    Class to create and load the per-user style sheet.

    Stores the file in ~/.sasview/sasview.css, if it does not already exist, otherwise overwrites it
    """
    _default_sheet = """
        /* Global Properties */
        * {font-size: 9pt; font-family: Helvetica, Arial, Verdana, sans-serif}
    
        /* HTML Elements */
        h1 {font-size: 240%;}
    
        /* Qt Elements */
        QLineEdit {background-color: white; color: black;}
        QLineEdit:focus {background-color: #98dbcc; color: #333333}
        QLineEdit[urgent=true] {background-color: red;}
        QTableWidgetItem[italic=true] {font-style: italic}
    
        QLabel[angstrom=true] {font-family: -apple-system, "Helvetica Neue", "Ubuntu";}
    
        QToolTip {font-size: 80%;}
    
        /* Class-specific Properties */
        .monospace {font-family: 'monospace, monospace'}
        """

    def __init__(self):
        self.style_sheet = None
        self.save()

    def _style_sheet_filename(self):
        """Filename for saving config items"""
        user_dir = user.get_user_dir()
        self.style_sheet = os.path.join(user_dir, config.STYLE_SHEET)

    def save(self):
        """
        Save the existing style in the user directory
        """
        sheet = self.read()
        self._style_sheet_filename()
        with open(self.style_sheet, 'w') as file:
            file.write(sheet)

    def _find_style_sheet(self, filename=None):
        """
        The style sheet is in:
        User directory ~/.sasview/
        Debug .
        """
        if filename is None:
            filename = config.STYLE_SHEET
        self._style_sheet_filename()
        places_to_look_for_conf_file = [
            self.style_sheet,
        ]

        # To avoid the exception in OSx
        # NotImplementedError: resource_filename() only supported for .egg, not .zip
        try:
            places_to_look_for_conf_file.append(
                pkg_resources.resource_filename(__name__, filename))
        except NotImplementedError:
            pass

        for filepath in places_to_look_for_conf_file:
            if os.path.exists(filepath):
                self.style_sheet = filepath
                return
        self.style_sheet = None

    def read(self):
        self._find_style_sheet()
        if self.style_sheet is not None:
            with open(self.style_sheet) as f:
                style = f.read()
        else:
            style = self._default_sheet
        return style


style_sheet = StyleSheet()
