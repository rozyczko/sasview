import sys
import os
from typing import Optional


from PySide6 import QtGui, QtWebEngineWidgets, QtCore, QtWidgets, QtWebEngineCore

from .UI.DocViewWidgetUI import Ui_DocViewerWindow
from sas.qtgui.Utilities.TabbedModelEditor import TabbedModelEditor


class DocViewWindow(QtWidgets.QDialog, Ui_DocViewerWindow):
    """
    Instantiates a window to view documentation using a QWebEngineViewer widget
    """
    def __init__(self, parent=None, source=None):
        super(DocViewWindow, self).__init__(parent)
        self.parent = parent
        self.setupUi(self)
        # disable the context help icon
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setWindowTitle("Documentation Viewer")

        # Necessary global
        self.source = source

        self.loadHtml() #loads the html file specified in the source url to the QWebViewer

        self.initializeSignals() # Connect signals

    def initializeSignals(self):
        self.editButton.clicked.connect(self.onEdit)
        self.closeButton.clicked.connect(self.onClose)

    def onEdit(self):
        """
        Open editor (TabbedModelEditor) window.
        """
        # Convert QUrl to pathname:
        from re import findall
        # Extract path from QUrl
        path = findall(r"(?<=file:\/\/\/).+\.html", str(self.webEngineViewer.url()))
        # Test to see if we're dealing with a model html file or other html file
        if "models" in path[0]:
            file = os.path.splitext(os.path.basename(path[0]))[0]
            print(file)
            self.editorWindow =  TabbedModelEditor(parent=self.parent,
                                                   edit_only=True,
                                                   load_file=file,
                                                   model=True)
        else:
            self.editorWindow =  TabbedModelEditor(parent=self.parent,
                                                   edit_only=True,
                                                   load_file=file,
                                                   model=False)
        self.editorWindow.show()

    def onClose(self, event):
        """
        Close window
        """
        self.close()
        
    def loadHtml(self):
        """
        Loads the HTML file specified when this python is called from another part of the program.
        """
        # Ensure urls are properly processed before passing into widget
        url = self.processUrl()
        print(url)
        settings = self.webEngineViewer.settings()
        # Allows QtWebEngine to access MathJax and code highlighting APIs
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        self.webEngineViewer.load(url)

    def processUrl(self):
        url = self.source
        # Check to see if path is absolute or relative, accomodating urls from many different places
        if not os.path.exists(url):
            from sas.qtgui.Utilities.GuiUtils import HELP_DIRECTORY_LOCATION
            location = HELP_DIRECTORY_LOCATION + url
            sas_path = os.path.abspath(os.path.dirname(sys.argv[0]))
            url = sas_path+"/"+location
        # Convert path to a QUrl needed for QWebViewerEngine
        abs_url = QtCore.QUrl()
        abs_url.setUrl(QtCore.QUrl.fromLocalFile(url).toLocalFile())
        return abs_url


# if __name__ == "__main__":
#     app = QtWidgets.QApplication(sys.argv)
#     win =  DocViewWindow()
#     win.show()
#     app.exec_()
