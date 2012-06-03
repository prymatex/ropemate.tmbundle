#!/usr/bin/env python
#-*- encoding: utf-8 -*-

from PyQt4 import QtGui

def load(application, settings):
    text, accepted = QtGui.QInputDialog.getText(application.mainWindow, "New Name", settings.title, text = settings.result)
    return text