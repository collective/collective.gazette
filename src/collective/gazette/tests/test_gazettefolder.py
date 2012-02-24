from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import setRoles
from plone.app.testing import login
from plone.testing.z2 import Browser
import transaction
import unittest2 as unittest
from collective.gazette.tests.layer import GAZETTE_FUNCTIONAL_TESTING
from Products.CMFPlone.utils import _createObjectByType
from collective.gazette.gazettefolder import validateEmail
from zope.interface import Invalid


class GazetteSendTestCase(unittest.TestCase):

    # using functional testing because tests uses own transaction commit
    # due to the testbrowser integration.
    layer = GAZETTE_FUNCTIONAL_TESTING

    def test_validate_email(self):
        self.failUnless(validateEmail('john@doe.com'))
        self.failUnless(validateEmail('john@doe.dot.com'))
        self.assertRaises(Invalid, validateEmail, 'john')
        self.assertRaises(Invalid, validateEmail, 'john@com')

    def test_gazette_folder_view(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']

        # First we need to create some content.
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        _createObjectByType('gazette.GazetteFolder', self.portal, 'gazettefolder')
        self.gfolder = self.portal.gazettefolder
        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.open(self.gfolder.absolute_url())
        self.failUnless('Recent newsletters' in browser.contents)
        self.failUnless('There are no newsletters yet.' in browser.contents)
        self.failIf('table class="listing"' in browser.contents)
        _createObjectByType('gazette.GazetteIssue', self.gfolder, 'issue1', title='Issue 1')
        _createObjectByType('gazette.GazetteIssue', self.gfolder, 'issue2', title='Issue 2')
        self.gfolder.issue1.reindexObject()
        self.gfolder.issue2.reindexObject()
        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.open(self.gfolder.absolute_url())
        self.failIf('There are no newsletters yet.' in browser.contents)
        self.failUnless('table class="listing"' in browser.contents)
        self.failUnless('Issue 1' in browser.contents)
        self.failUnless('Issue 2' in browser.contents)
