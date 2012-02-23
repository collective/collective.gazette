from cornerstone.soup.interfaces import ISoupAnnotatable
from plone.app.testing import TEST_USER_ID
from zope.component import createObject
from zope.component import queryUtility
from plone.app.testing import setRoles
from plone.dexterity.interfaces import IDexterityFTI
import unittest2 as unittest
from collective.gazette.tests.layer import GAZETTE_INTEGRATION_TESTING
from collective.gazette.issue import IGazetteIssue
from collective.gazette.gazettefolder import IGazetteFolder


class TestGazetteFolder(unittest.TestCase):

    layer = GAZETTE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.invokeFactory('Folder', 'test-folder')
        setRoles(self.portal, TEST_USER_ID, ['Contributor'])
        self.folder = self.portal['test-folder']

    def test_adding(self):
        self.portal.invokeFactory('gazette.GazetteFolder', 'gf1')
        p1 = self.portal['gf1']
        self.failUnless(IGazetteFolder.providedBy(p1))
        self.failUnless(ISoupAnnotatable.providedBy(p1))

    def test_fti(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteFolder')
        self.assertNotEquals(None, fti)

    def test_schema(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteFolder')
        schema = fti.lookupSchema()
        self.assertEquals(IGazetteFolder, schema)

    def test_factory(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteFolder')
        factory = fti.factory
        new_object = createObject(factory)
        self.failUnless(IGazetteFolder.providedBy(new_object))
        self.failUnless(ISoupAnnotatable.providedBy(new_object))


class TestGazette(unittest.TestCase):

    layer = GAZETTE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        self.portal.invokeFactory('gazette.GazetteFolder', 'gazette-folder')
        setRoles(self.portal, TEST_USER_ID, ['Contributor'])
        self.folder = self.portal['gazette-folder']

    def test_adding(self):
        # cannot be added do folder, only to GazetteFolder
        self.assertRaises(ValueError, self.portal.invokeFactory, 'gazette.GazetteIssue', 'issue')
        self.folder.invokeFactory('gazette.GazetteIssue', 'issue')
        p1 = self.folder['issue']
        self.failUnless(IGazetteIssue.providedBy(p1))

    def test_fti(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteIssue')
        self.assertNotEquals(None, fti)

    def test_schema(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteIssue')
        schema = fti.lookupSchema()
        self.assertEquals(IGazetteIssue, schema)

    def test_factory(self):
        fti = queryUtility(IDexterityFTI, name='gazette.GazetteIssue')
        factory = fti.factory
        new_object = createObject(factory)
        self.failUnless(IGazetteIssue.providedBy(new_object))
