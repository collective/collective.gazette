from zope.interface import implements
from zope.component import getMultiAdapter
from collective.gazette import config
from cornerstone.soup import getSoup
from collective.gazette.interfaces import IGazetteSubscription
from zExceptions import Forbidden
from plone.app.testing import TEST_USER_PASSWORD
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import setRoles
from plone.app.testing import login
from plone.app.textfield.value import RichTextValue
from zope.interface import alsoProvides
from zope.annotation.interfaces import IAttributeAnnotatable
from z3c.form.interfaces import IFormLayer
from plone.testing.z2 import Browser
import transaction
import unittest2 as unittest
from collective.gazette.tests.layer import GAZETTE_FUNCTIONAL_TESTING
from Products.CMFPlone.utils import _createObjectByType
from collective.gazette.interfaces import IGazetteTextProvider
from plone.app.testing import pushGlobalRegistry
from plone.app.testing import popGlobalRegistry
from zope.component import provideUtility


class TestingProvider(object):
    implements(IGazetteTextProvider)

    def __repr__(self):
        return "Test provider"

    def get_gazette_text(self, gazette_folder, gazette):
        return "<p>Hello world</p>"


class AutomatedSendTestCase(unittest.TestCase):

    # using functional testing because tests uses own transaction commit
    # due to the testbrowser integration.
    layer = GAZETTE_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']

        pushGlobalRegistry(self.portal)
        provideUtility(TestingProvider(), provides=IGazetteTextProvider, name="test-provider")
        alsoProvides(self.request, IFormLayer)
        alsoProvides(self.request, IAttributeAnnotatable)

        # First we need to create some content.
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        _createObjectByType('gazette.GazetteFolder', self.portal, 'gazettefolder')
        self.gfolder = self.portal.gazettefolder
        self.gfolder.auto_enabled = True
        self.gfolder.auto_subject = 'Daily issue'
        self.gfolder.auto_providers = ['test-provider']

        # We need to fake a valid mail setup
        self.portal.email_from_address = "portal@plone.test"
        self.mailhost = self.portal.MailHost

    def tearDown(self):
        popGlobalRegistry(self.portal)

    def test_autoissue(self):
        view = self.gfolder.restrictedTraverse('auto-issue')
        result = view.render(test_mode=True, html_only=True)
        self.assertEqual(result, u"""<!doctype html>\n<html>\n<head>\n<meta http-equiv="content-type" content="text/html; charset=utf-8" />\n</head>\n<body>\n<p>Hello world</p>\n</body>\n</html>\n""")
        # this was a test mode - no recent issue created/set
        self.failIf(self.gfolder.objectIds())
        self.failIf(self.gfolder.most_recent_issue)
        result = view.render(test_mode=False, html_only=True)
        # no subscribers, no email
        self.failIf(len(self.mailhost.messages) != 0)
        self.failUnless(len(self.gfolder.objectIds()) == 1)
        self.failUnless(self.gfolder.objectIds()[0] == self.gfolder.most_recent_issue.getId())

        # subscibe a subscriber
        request = self.request
        adapter = getMultiAdapter((self.gfolder, request), IGazetteSubscription)
        adapter.subscribe('tester@test.com', '')
        result = view.render(test_mode=False, html_only=True)
        # subscription request only -- user is not active yet
        self.failUnless(len(self.mailhost.messages) == 1)

        # Activate subsriber
        soup = getSoup(self.gfolder, config.SUBSCRIBERS_SOUP_ID)
        s = soup.query(email='tester@test.com').next()
        s.active = True
        s.key = u''
        soup.reindex([s])

        result = view.render(test_mode=False, html_only=True)
        # subscription request and issue emails
        self.failUnless(len(self.mailhost.messages) == 2)
        # but all issues are stored as sub objects
        self.failUnless(len(self.gfolder.objectIds()) == 3)

        # finally try to make a PDF
        result = view.render(test_mode=True, html_only=False)
        self.failUnless(result.startswith(r'%PDF-'), msg='Please check wkhtmltopdf is installed in your system.')