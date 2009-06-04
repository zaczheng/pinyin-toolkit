#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4.QtCore import QVariant, SIGNAL
from PyQt4.QtGui import QColor, QIcon, QPalette

import pinyin.config
from pinyin.languages import languages
import pinyin.mocks
import pinyin.updater
import pinyin.utils


previewexpression = u"书"
# TODO: set media pack up up according to user extensions
previewmedia = [pinyin.media.MediaPack("Example", {"shu1.mp3" : "shu1.mp3", "shu1.ogg" : "shu1.ogg"})]

class PreferencesController(object):
    def __init__(self, view, initialconfig, dictionary):
        # Clone the configuration so we can change it at will
        self.model = pinyin.config.Config(initialconfig.settings)
    
        # Save the view (typically a Preferences instance) for later reference
        self.view = view
        
        # Set up an updater we will use to deal with the live preview, based off the current model
        self.updater = pinyin.updater.FieldUpdater(pinyin.mocks.NullNotifier(), pinyin.mocks.MockMediaManager(previewmedia), self.model, dictionary)
        
        # Set up the controls - one time only
        self.mappings = []
        self.setUpText()

        # Use the mappings to reflect the initial setting values into the controls and preview pane
        self.updateView()
        self.updateViewPreview()
    
    #
    # Setup
    #
    
    def setUpText(self):
        # The Hanzi and Pinyin panel
        def setUpHanziPinyin():
            self.registerRadioMapping("tonedisplay", {
                self.view.controls.numericPinyinTonesRadio : "numeric",
                self.view.controls.tonifiedPinyinTonesRadio : "tonified"
              })
            
            self.registerRadioMapping("prefersimptrad", {
                self.view.controls.simplifiedHanziRadio : "simp",
                self.view.controls.traditionalHanziRadio : "trad"
              })
        
        # The Meanings panel
        def setUpMeanings():
            # Add languages to the combo box lexically sorted by support level, then by friendly name
            lastsupportlevel = None
            for supportlevel, langcode, countrycode, name in sorted(languages, lambda x, y: cmp((y[0], x[3]), (x[0], y[3]))):
                # Add a seperator if we have moved to a new support level
                if lastsupportlevel != None and supportlevel != lastsupportlevel:
                    self.addComboSeparator(self.view.controls.languageCombo)
                lastsupportlevel = supportlevel
            
                # Decide on the icon to use, if any
                if countrycode:
                    icon = ":/flags/%s.png" % countrycode
                else:
                    icon = None
            
                # Set the langcode as the user data for the combo item - this
                # will be picked up by the ComboMapping stuff
                self.addComboItem(self.view.controls.languageCombo, icon, name, langcode)
            
            self.registerCheckMapping("detectmeasurewords", self.view.controls.seperateMeasureWordCheck)
            
            self.registerComboMapping("dictlanguage", self.view.controls.languageCombo)
            
            self.registerCheckMapping("fallbackongoogletranslate", self.view.controls.googleTranslateCheck)
            
            self.registerRadioMapping("meaningnumbering", {
                self.view.controls.circledChineseNumberingRadio : "circledChinese",
                self.view.controls.circledArabicNumberingRadio : "circledArabic",
                self.view.controls.plainNumberingRadio : "arabicParens",
                self.view.controls.noNumberingRadio : "none",
              })
            
            self.registerRadioMapping("meaningseperator", {
                self.view.controls.linesSeperatorRadio : "lines",
                self.view.controls.commasSeperatorRadio : "commas",
                self.view.controls.customSeperatorRadio : "custom"
              })
            
            self.registerTextMapping("custommeaningseperator", self.view.controls.customSeperatorLineEdit)
        
        # The Tone Colors panel
        def setUpToneColors():
            self.registerCheckMapping("colorizedpinyingeneration", self.view.controls.colorizeCheck)
            
            for tone in range(1, 6):
                self.registerColorChooserMapping("tone%dcolor" % tone, getattr(self.view.controls, "tone%dButton" % tone))
        
        setUpHanziPinyin()
        setUpMeanings()
        setUpToneColors()
    
    def addComboItem(self, combo, icon, name, data):
        if icon:
            combo.addItem(QIcon(icon), name, QVariant(data))
        else:
            combo.addItem(name, QVariant(data))

    def addComboSeparator(self, combo):
        combo.insertSeparator(combo.count())
    
    #
    # Tear down
    #
    
    def __del__(self):
        self.unregisterMappings()
    
    #
    # View manipulation
    #
    
    def updateView(self):
        for mapping in self.mappings:
            mapping.updateView()
    
    def updateViewPreview(self):
        # Create a model fact that we will fill with information, as well
        # as a list of fields to put that information into
        fact = {}
        fieldnamesbykey = {}
        for key, candidatefieldnames in self.model.candidateFieldNamesByKey.items():
            fact[key] = u""
            fieldnamesbykey[key] = pinyin.utils.heador(candidatefieldnames, key.capitalize())
        
        # Update the fact using the current model configuration
        self.updater.updatefact(fact, previewexpression)
        
        # Pull together the name of the field and the contents it should have
        namedvalues = []
        for key, value in fact.items():
            namedvalues.append((fieldnamesbykey[key], value))
        
        # Done: give the named values to the view, sorted by the field name
        self.view.updateFields(sorted(namedvalues, lambda x, y: cmp(x[0], y[0])))

    #
    # Mapping helpers
    #
    
    def registerRadioMapping(self, *args):
        self.registerMapping(RadioMapping(self.model, *args))
    
    def registerCheckMapping(self, *args):
        self.registerMapping(CheckMapping(self.model, *args))
    
    def registerComboMapping(self, *args):
        self.registerMapping(ComboMapping(self.model, *args))
    
    def registerTextMapping(self, *args):
        self.registerMapping(TextMapping(self.model, *args))
    
    def registerColorChooserMapping(self, *args):
        self.registerMapping(ColorChooserMapping(self.model, lambda initcolor: self.view.pickColor(initcolor), *args))

    def registerMapping(self, mapping):
        # Ensure that we update the view whenever any of the mappings changes the model
        mapping.modelchanged.subscribe(self.updateViewPreview)
        
        self.mappings.append(mapping)

    def unregisterMappings(self):
        # Ensure that we remove the event handlers we install during registration,
        # to avoid memory leaks and other nasty stuff
        for mapping in self.mappings:
            mapping.modelchanged.unsubscribe(self.updateViewPreview)

class Event(object):
    def __init__(self):
        self.subscribers = []
    
    def subscribe(self, function):
        self.subscribers.append(function)
    
    def unsubscribe(self, function):
        self.subscribers.delete(function)
    
    def fire(self, *args, **kwargs):
        for subscriber in self.subscribers:
            subscriber(*args, **kwargs)

class Mapping(object):
    def __init__(self, model, key):
        self.model = model
        self.key = key
        
        self.modelchanged = Event()

    def updateView(self):
        self.updateViewValue(getattr(self.model, self.key))

    def updateModelValue(self, value):
        setattr(self.model, self.key, value)
        
        modelchanged.fire(value)

class RadioMapping(Mapping):
    def __init__(self, model, key, radiobuttonswithvalues):
        Mapping.__init__(self, model, key)
        self.radiobuttonswithvalues = radiobuttonswithvalues
        
        for radiobutton, correspondingvalue in self.radiobuttonswithvalues.items():
            radiobutton.connect(radiobutton, SIGNAL("clicked()"), lambda: self.updateModelValue(correspondingvalue))

    def updateViewValue(self, value):
        for radiobutton, correspondingvalue in self.radiobuttonswithvalues.items():
            radiobutton.setChecked(value == correspondingvalue)

class CheckMapping(Mapping):
    def __init__(self, model, key, checkbox):
        Mapping.__init__(self, model, key)
        self.checkbox = checkbox
        
        self.checkbox.connect(self.checkbox, SIGNAL("clicked()"), lambda: self.updateModel())
    
    def updateModel(self):
        self.updateModelValue(self, self.checkbox.checked())
    
    def updateViewValue(self, value):
        self.checkbox.setChecked(value)
        
class ComboMapping(Mapping):
    def __init__(self, model, key, combobox):
        Mapping.__init__(self, model, key)
        self.combobox = combobox
        
        self.combobox.connect(self.combobox, SIGNAL("currentIndexChanged(int)"), lambda: self.updateModel())
    
    def updateModel(self, n):
        self.updateModelValue(self.combobox.itemData(n).toPyObject())
    
    def updateViewValue(self, value):
        for n in range(0, self.combobox.count()):
            if self.combobox.itemData(n).toPyObject() == value:
                self.combobox.setCurrentIndex(n)
                return
        
        raise AssertionError("The value %s was not in the list of options" % value)
        
class TextMapping(Mapping):
    def __init__(self, model, key, lineedit):
        Mapping.__init__(self, model, key)
        self.lineedit = lineedit
        
        self.lineedit.connect(self.lineedit, SIGNAL('textEdited()'), lambda: self.updateModel())
    
    def updateModel(self):
        self.updateModelValue(self.lineedit.text())
    
    def updateViewValue(self, value):
        self.lineedit.setText(value)
        
class ColorChooserMapping(Mapping):
    def __init__(self, model, pickcolor, key, button):
        Mapping.__init__(self, model, key)
        self.button = button
        self.pickcolor = pickcolor
        
        self.button.connect(self.button, SIGNAL("clicked()"), lambda: self.updateModel())
    
    def palette(self):
        return self.button.palette()
    
    def updateModel(self):
        color = self.pickcolor(self.palette().color(QPalette.ButtonText))
        
        # The isValid flag is cleared if the user cancels the dialog
        if color != None and color.isValid():
            value = pinyin.utils.toHtmlColor(color.red(), color.green(), color.blue())
            self.updateModelValue(value)
            self.updateViewValue(value)
    
    def updateViewValue(self, value):
        r, g, b = pinyin.utils.parseHtmlColor(value)
        
        self.palette().setColor(QPalette.ButtonText, QColor(r, g, b))
        
        # Modifying the palette seems to require an explicit repaint
        self.button.update()