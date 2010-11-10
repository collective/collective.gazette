from zope.component import getUtility
from plone.keyring.keyring import Keyring
from plone.keyring.interfaces import IKeyManager
from collective.gazette import config 

def setupVarious(context):

    if context.readDataFile('collective.gazette.txt') is None:
        return

    # portal = context.getSite()
