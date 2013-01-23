#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from prymatex.qt import QtGui

from prymatex.core import PMXBaseDialog

class InputDialog(QtGui.QInputDialog, PMXBaseDialog):
    def __init__(self, parent = None):
        QtGui.QInputDialog.__init__(self, parent)
        PMXBaseDialog.__init__(self)
    
    def setParameters(self, parameters):
        if "title" in parameters:
            self.setWindowTitle(parameters["title"])
        if "result" in parameters:
            self.setTextValue(parameters["result"])
        self.setLabelText("New name")
        
    def execModal(self):
        code = self.exec_()
        if code == QtGui.QDialog.Accepted:
            return self.textValue()
        return ""
        
dialogClass = InputDialog