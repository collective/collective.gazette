from Testing import ZopeTestCase as ztc

from Products.PloneTestCase import ptc
from Products.PloneTestCase import layer
from Products.Five import zcml
from Products.Five import fiveconfigure

ptc.setupPloneSite(
    extension_profiles=('collective.gazette:default', )
)

class GazetteLayer(layer.PloneSite):
    """Configure collective.gazette"""

    @classmethod
    def setUp(cls):
        fiveconfigure.debug_mode = True
        import collective.gazette
        zcml.load_config("configure.zcml", collective.gazette)
        fiveconfigure.debug_mode = False
        ztc.installPackage("collective.gazette", quiet=1)

    @classmethod
    def tearDown(cls):
        pass
