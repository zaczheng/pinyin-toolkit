# -*- coding: utf-8 -*-

import copy
from functools import partial
import unittest
from testutils import *

import pinyin.config
from pinyin.db import database
from pinyin.factproxy import markgeneratedfield, isgeneratedfield
from pinyin.updater import *
from pinyin.utils import Thunk
from pinyin.mocks import *


def assertUpdatesTo(updater, expression, theconfig, incomingfact, expectedfact, mediapacks=[], **kwargs):
    actualfact = copy.deepcopy(incomingfact)
    updater(MockNotifier(), MockMediaManager(mediapacks), config.Config(utils.updated({ "dictlanguage" : "en" }, theconfig))).updatefact(actualfact, expression, **kwargs)
    assert_dict_equal(actualfact, expectedfact, values_as_assertions=True)

class TestFieldUpdaterFromAudio(object):
    def testDoesntReformatWhenDisabled(self):
        self.assertUpdatesTo(u"hen3 hao3", dict(forcepinyininaudiotosoundtags = False), { "audio" : u"", "expression" : u"junk" }, { "audio" : u"hen3 hao3", "expression" : u"junk" })
    
    def testLeavesOtherFieldsAlone(self):
        self.assertUpdatesTo(u"", dict(forcepinyininaudiotosoundtags = True), { "audio" : u"[sound:fake.mp3]", "expression" : u"junk" }, { "audio" : u"", "expression" : u"junk" })

    def testReusesOldValueIfNoDelta(self):
        self.assertUpdatesTo(None, dict(forcepinyininaudiotosoundtags = True), { "audio" : u"[sound:fake.mp3]" }, { "audio" : u"[sound:fake.mp3]" })

    def testUpdatingGeneratedVersion(self):
        self.assertUpdatesTo(None, dict(forcepinyininaudiotosoundtags = True), { "audio" : markgeneratedfield(u"[sound:fake.mp3]") }, { "audio" : markgeneratedfield(u"[sound:fake.mp3]") })

    def testReformatsAccordingToConfig(self):
        henhaoaudio = u"[sound:" + os.path.join("Test", "hen3.mp3") + "][sound:" + os.path.join("Test", "hao3.mp3") + "]"

        self.assertUpdatesTo(u"hen3 hao3", dict(forcepinyininaudiotosoundtags = True), { "audio" : "junky" }, { "audio" : henhaoaudio })
        self.assertUpdatesTo(u"hen3,hǎo", dict(forcepinyininaudiotosoundtags = True), { "audio" : "junky" }, { "audio" : henhaoaudio })
    
    def testDoesntModifySoundTags(self):
        config = dict(forcepinyininaudiotosoundtags = True)
        self.assertUpdatesTo(u"[sound:aeuth34t0914bnu.mp3][sound:ae390n32uh2ub.mp3]", config, { "audio" : "" }, { "audio" : u"[sound:aeuth34t0914bnu.mp3][sound:ae390n32uh2ub.mp3]" })
        self.assertUpdatesTo(u"[sound:hen3.mp3][sound:hao3.mp3]", config, { "audio" : "" }, { "audio" : u"[sound:hen3.mp3][sound:hao3.mp3]" })
    
    # Test helpers
    def assertUpdatesTo(self, *args):
        mediapacks = [media.MediaPack("Test", { "shu1.mp3" : "shu1.mp3", "shu1.ogg" : "shu1.ogg",
                                                "san1.mp3" : "san1.mp3", "qi1.ogg" : "qi1.ogg", "Kai1.mp3" : "location/Kai1.mp3",
                                                "hen3.mp3" : "hen3.mp3", "hen2.mp3" : "hen2.mp3", "hao3.mp3" : "hao3.mp3" })]
        assertUpdatesTo(partial(FieldUpdater, "audio"), *args, mediapacks=mediapacks)

class TestFieldUpdaterFromMeaning(object):
    def testDoesntReformatWhenDisabled(self):
        config = dict(forcemeaningnumberstobeformatted = False)
        self.assertUpdatesTo(u"(1) yes (2) no", config, { "meaning" : "", "expression" : "junk" }, { "meaning" : "(1) yes (2) no", "expression" : "junk" })
    
    def testLeavesOtherFieldsAlone(self):
        self.assertUpdatesTo(u"", dict(forcemeaningnumberstobeformatted = True), { "meaning" : "junk", "expression" : "junk" }, { "meaning" : u"", "expression" : "junk" })

    def testReusesOldValueIfNoDelta(self):
        self.assertUpdatesTo(None, dict(forcemeaningnumberstobeformatted = True), { "meaning" : "hen3" }, { "meaning" : u"hen3" })

    def testUpdatingGeneratedVersion(self):
        self.assertUpdatesTo(None, dict(forcemeaningnumberstobeformatted = True), { "meaning" : markgeneratedfield(u"hen3") }, { "meaning" : markgeneratedfield(u"hen3") })

    def testReformatsAccordingToConfig(self):
        self.assertUpdatesTo(u"(1) yes (2) no", dict(forcemeaningnumberstobeformatted = True, meaningnumbering = "circledArabic", colormeaningnumbers = False), { "meaning" : "junky" }, { "meaning" : u"① yes ② no" })
        self.assertUpdatesTo(u"(10) yes 2 no", dict(forcemeaningnumberstobeformatted = True, meaningnumbering = "none", colormeaningnumbers = False), { "meaning" : "junky" }, { "meaning" : u" yes 2 no" })
    
    # Test helpers
    def assertUpdatesTo(self, *args):
        assertUpdatesTo(partial(FieldUpdater, "meaning"), *args)

class TestFieldUpdaterFromReading(object):
    def testDoesntReformatWhenDisabled(self):
        config = dict(forcereadingtobeformatted = False)
        self.assertUpdatesTo(u"hen3 hǎo", config, { "reading" : "", "expression" : "junk" }, { "reading" : u"hen3 hǎo", "expression" : "junk" })
    
    def testDoesSomethingWhenDisabledIfAlways(self):
        self.assertUpdatesTo(u"also junk", { "forcereadingtobeformatted" : False },
            { "reading" : "", "expression" : "junk" },
            { "reading" : lambda reading: len(reading) > 0 and reading != "also junk", "expression" : "junk" }, alwaysreformat=True)
    
    def testLeavesOtherFieldsAlone(self):
        self.assertUpdatesTo(u"", dict(forcereadingtobeformatted = True),
            { "reading" : "junk", "expression" : "junk" },
            { "reading" : u"", "expression" : "junk" })

    def testReusesOldValueIfNoDelta(self):
        config = dict(forcereadingtobeformatted = True, tonedisplay = "tonified", colorizedpinyingeneration = False)
        self.assertUpdatesTo(None, config, { "reading" : u"hen3" }, { "reading" : u"hěn" })
    
    def testUpdateColor(self):
        config = dict(forcereadingtobeformatted = False, colorizedpinyingeneration = False, colorizedcharactergeneration = True, tonecolors = [u"#111111", u"#222222", u"#333333", u"#444444", u"#555555"])
        for updatewith, old, new in [(u"hen3", u"", u"hen3"), (u"hěn", u"", u"hěn"), (None, markgeneratedfield(u"hěn"), markgeneratedfield(u"hěn"))]:
            yield (self.assertUpdatesTo, updatewith, config,
                { "reading" : old, "expression" : u"很", "color" : u"" },
                { "reading" : new, "expression" : u"很", "color" : markgeneratedfield(u'<span style="color:#333333">很</span>') })

    def testUpdatingGeneratedVersion(self):
        config = dict(forcereadingtobeformatted = True, tonedisplay = "numeric")
        self.assertUpdatesTo(None, config,
            { "reading" : markgeneratedfield(u"hen3") },
            { "reading" : markgeneratedfield(u"hen3") })

    def testReformatsAccordingToConfig(self):
        config = dict(forcereadingtobeformatted = True, tonedisplay = "tonified",
                      colorizedpinyingeneration = True, tonecolors = [u"#111111", u"#222222", u"#333333", u"#444444", u"#555555"])
        self.assertUpdatesTo(u"hen3 hǎo", config,
            { "reading" : "junky" },
            { "reading" : u'<span style="color:#333333">hěn</span> <span style="color:#333333">hǎo</span>' })
    
    def testReformattingRespectsExistingColorization(self):
        config = dict(forcereadingtobeformatted = True, tonedisplay = "numeric",
                      colorizedpinyingeneration = True, tonecolors = [u"#111111", u"#222222", u"#333333", u"#444444", u"#555555"])
        self.assertUpdatesTo(u"<span style='color: red'>hen3</span> hǎo", config,
            { "reading" : "junky" },
            { "reading" : u'<span style=\"\"><span style="color: red">hen3</span></span> <span style="color:#333333">hao3</span>' })

    # Test helpers
    def assertUpdatesTo(self, *args, **kwargs):
        assertUpdatesTo(partial(FieldUpdater, "reading"), *args, **kwargs)

class TestFieldUpdaterFromExpression(object):
    def testReusesOldValueIfNoDelta(self):
        self.assertUpdatesTo(None, dict(colorizedpinyingeneration = False, tonedisplay = "numeric", readinggeneration = True),
            { "expression" : u"书", "reading" : "" },
            { "expression" : u"书", "reading" : markgeneratedfield("shu1") })
    
    def testUpdatingGeneratedVerison(self):
        self.assertUpdatesTo(None, {}, { "expression" : markgeneratedfield(u"书") }, { "expression" : markgeneratedfield(u"书") })

    def testAutoBlankingGenerated(self):
        self.assertUpdatesTo(u"", {}, {
              "reading" : markgeneratedfield("blather"),
              "meaning" : markgeneratedfield("junk"), 
              "color" : markgeneratedfield("yes!"), 
              "trad" : markgeneratedfield("meh"), 
              "simp" : markgeneratedfield("yay"), 
              "audio" : markgeneratedfield("moo"), 
              "mwaudio" : markgeneratedfield("mehh"), 
              "mw" : markgeneratedfield("a mw")
            },
            { "reading" : "", "meaning" : "", "color" : "", "trad" : "", "simp" : "", "audio" : "", "mwaudio" : "", "mw" : "" })
    
    def testDosentAutoBlankNonGenerated(self):
        nonempty = { "reading" : "a", "meaning" : "b", "color" : "c", "trad" : "d", "simp" : "e", "audio" : "f", "mwaudio" : "g", "mw" : "h" }
        self.assertUpdatesTo(u"", {}, nonempty, nonempty)
    
    def testGenerateAllFieldsWhenEmptyOrGenerated(self):
        config = dict(colorizedpinyingeneration = True, colorizedcharactergeneration = True, meaninggeneration = True, detectmeasurewords = True, emphasisemainmeaning = False,
                      tonedisplay = "tonified", meaningnumbering = "circledChinese", colormeaningnumbers = False, meaningseperator = "lines", prefersimptrad = "simp",
                      audiogeneration = True, mwaudiogeneration = True, audioextensions = [".mp3"], tonecolors = [u"#ff0000", u"#ffaa00", u"#00aa00", u"#0000ff", u"#545454"], weblinkgeneration = False, hanzimasking = False,
                      tradgeneration = True, simpgeneration = True, forceexpressiontobesimptrad = False)
        
        for default in ["", markgeneratedfield("Generated")]:
            expected = {
                "expression" : u"书",
                "reading" : markgeneratedfield(u'<span style="color:#ff0000">shū</span>'),
                "meaning" : markgeneratedfield(u'㊀ book<br />㊁ letter<br />㊂ see also <span style="color:#ff0000">\u4e66</span><span style="color:#ff0000">\u7ecf</span> Book of History'),
                "mw" : markgeneratedfield(u'<span style="color:#00aa00">本</span> - <span style="color:#00aa00">běn</span>, <span style="color:#0000ff">册</span> - <span style="color:#0000ff">cè</span>, <span style="color:#0000ff">部</span> - <span style="color:#0000ff">bù</span>'),
                "audio" : markgeneratedfield(u"[sound:" + os.path.join("Test", "shu1.mp3") + "]"),
                "mwaudio" : lambda mwaudio: assert_equal(sanitizequantitydigits(mwaudio), markgeneratedfield((u"[sound:" + os.path.join("Test", "X.mp3") + u"][sound:" + os.path.join("Test", "shu1.mp3") + "]") * 3)),
                "color" : markgeneratedfield(u'<span style="color:#ff0000">书</span>'),
                "trad" : markgeneratedfield(u"書"),
                "simp" : markgeneratedfield(u"书")
              }
            yield self.assertUpdatesTo, u"书", config, { "expression" : u"书", "reading" : default, "meaning" : default, "mw" : default, "audio" : default, "mwaudio" : default, "color" : default, "trad" : default, "simp" : default }, expected
    
    def testDontOverwriteNonGeneratedFields(self):
        config = dict(colorizedpinyingeneration = True, colorizedcharactergeneration = True, meaninggeneration = True, detectmeasurewords = True,
                      tonedisplay = "tonified", meaningnumbering = "circledChinese", meaningseperator = "lines", prefersimptrad = "simp",
                      audiogeneration = True, mwaudiogeneration = True, audioextensions = [".mp3"], tonecolors = [u"#ff0000", u"#ffaa00", u"#00aa00", u"#0000ff", u"#545454"], weblinkgeneration = True,
                      tradgeneration = True, simpgeneration = True)
        self.assertUpdatesTo(u"书", config,
            { "expression" : "", "reading" : "a", "meaning" : "b", "mw" : "c", "audio" : "[sound:foo.mp3]", "mwaudio" : "[sound:foo.mp3]", "color" : "e", "trad" : "f", "simp" : "g" },
            { "expression" : u"书", "reading" : "a", "meaning" : "b", "mw" : "c", "audio" : "[sound:foo.mp3]", "mwaudio" : "[sound:foo.mp3]", "color" : "e", "trad" : "f", "simp" : "g" })
    
    def testUpdateControlFlags(self):
        baseconfig = dict(readinggeneration = False, colorizedpinyingeneration = True, colorizedcharactergeneration = False, meaninggeneration = False, detectmeasurewords = False,
                          audiogeneration = False, mwaudiogeneration = False, weblinkgeneration = False, tradgeneration = False, simpgeneration = False, forceexpressiontobesimptrad = False)
        blank = { "expression" : u"书", "reading" : "", "meaning" : "", "mw" : "", "audio" : "", "mwaudio" : "", "color" : "", "trad" : "", "simp" : "" }
        for field, flag in config.updatecontrolflags.items():
            if flag is None or field == 'weblinks':
                continue
            
            expected = utils.updated(dict(**blank), { field : lambda s, field=field: assert_true(isgeneratedfield(field, s) and len(s) > 0) })
            yield self.assertUpdatesTo, u"书", utils.updated(dict(**baseconfig), { flag : True }), blank, expected
    
    def testUpdateExpressionItself(self):
        self.assertUpdatesTo(u"啤酒", {}, { "expression" : "" }, { "expression" : u"啤酒" })
        self.assertUpdatesTo(u"啤酒", {}, { "expression" : "Filled" }, { "expression" : u"啤酒" })

    def testWebLinkFieldCanBeMissingAndStaysMissing(self):
        config = dict(weblinkgeneration = True)
        self.assertUpdatesTo(u"一概", config, { "expression" : "" }, { "expression" : u"一概" })
    
    def testWebLinksNotBlankedIfDisabled(self):
        config = dict(weblinkgeneration = False)
        self.assertUpdatesTo(u"一概", config, { "expression" : "", "weblinks": "Nope!" }, { "expression" : u"一概", "weblinks" : "Nope!" })
    
    def testRefomatExpressionAsSimpTrad(self):
        self.assertUpdatesTo(u"个個", dict(forceexpressiontobesimptrad = True, prefersimptrad = "trad"), { "expression" : u"个個" }, { "expression"  : u"個個" })
        self.assertUpdatesTo(u"个個", dict(forceexpressiontobesimptrad = True, prefersimptrad = "simp"), { "expression" : u"个個" }, { "expression"  : u"个个" })

    # Test helpers
    def assertUpdatesTo(self, *args):
        mediapacks = [media.MediaPack("Test", utils.updated(
                        { "shu1.mp3" : "shu1.mp3", "shu1.ogg" : "shu1.ogg", "san1.mp3" : "san1.mp3", "qi1.ogg" : "qi1.ogg",
                          "Kai1.mp3" : "location/Kai1.mp3", "hen3.mp3" : "hen3.mp3", "hen2.mp3" : "hen2.mp3", "hao3.mp3" : "hao3.mp3" }, quantitydigitmediadict))]
        assertUpdatesTo(FieldUpdaterFromExpression, *args, mediapacks=mediapacks)
