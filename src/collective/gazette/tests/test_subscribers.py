from plone.app.testing import TEST_USER_PASSWORD
from plone.testing.z2 import Browser
from Products.CMFPlone.utils import _createObjectByType
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import setRoles
import unittest2 as unittest
from collective.gazette.tests.layer import GAZETTE_FUNCTIONAL_TESTING
from collective.gazette import config
from cornerstone.soup import getSoup
from collective.gazette.subscribers import Subscriber
from collective.gazette.browser.subscribers import SubscribersView
from plone.app.testing import login
import transaction


class SubscribersTest(unittest.TestCase):

    layer = GAZETTE_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']

        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        _createObjectByType('gazette.GazetteFolder', self.portal, 'gazettefolder')
        self.gfolder = self.portal.gazettefolder
        self.context = self.gfolder
        self.soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        self.soup.add(Subscriber(email='test1@tester.com', fullname="Tester One", active=True))
        self.soup.add(Subscriber(email='test2@tester.com', fullname="Tester Two", active=False))
        self.soup.add(Subscriber(email='test3@tester.com', fullname="Tester Three", active=True))
        self.soup.add(Subscriber(email='test4@tester.com', fullname="Tester Four", active=False))
        self.soup.add(Subscriber(email='test5@tester.com', fullname="Tester Five", active=True))

    def test_count(self):
        view = SubscribersView(self.context, self.request)
        res = view.count()
        self.assertEquals(res['active'], 3)
        self.assertEquals(res['inactive'], 2)

    def test_search(self):
        view = SubscribersView(self.context, self.request)
        self.assertEquals(len(view.search(SearchableText='Two')), 1)
        self.assertEquals(len(view.search(SearchableText='Five')), 1)
        self.assertEquals(len(view.search(SearchableText='Blah')), 0)
        self.assertEquals(len(view.search(SearchableText='Tester')), 5)
        self.assertEquals(len(view.search(SearchableText='Test*')), 5)
        self.assertEquals(len(view.search(SearchableText='test')), 0)
        self.assertEquals(len(view.search(SearchableText='test*')), 5)
        self.assertEquals(len(view.search(SearchableText='Tester', active=True)), 3)
        self.assertEquals(len(view.search(SearchableText='Three', active=True)), 1)
        self.assertEquals(len(view.search(SearchableText='Three', active=False)), 0)
        self.assertEquals(len(view.search(active=True)), 3)
        self.assertEquals(len(view.search(active=False)), 2)
        self.assertEquals(len(view.search(email='test2@tester.com')), 1)
        self.assertEquals(len(view.search(email='test2*')), 0)  # field index
        self.assertEquals(len(view.search(email='test2')), 0)  # field index
        self.assertEquals(len(view.search(SearchableText='test2*')), 1)
        self.assertEquals(len(view.search(SearchableText='test2')), 1)  # Splitter by @ works...

    def test_view(self):
        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.handleErrors = False
        browser.addHeader('Authorization', 'Basic %s:%s' % (TEST_USER_NAME, TEST_USER_PASSWORD,))
        browser.open(self.gfolder.absolute_url() + '/subscribers')
        self.failUnless('<li><label>Active subscribers:</label>\n           3' in browser.contents)
        self.failUnless('<li><label>Inactive subscribers:</label>\n           2' in browser.contents)
