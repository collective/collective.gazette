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


class GazetteSendTestCase(unittest.TestCase):

    # using functional testing because tests uses own transaction commit
    # due to the testbrowser integration.
    layer = GAZETTE_FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        alsoProvides(self.request, IFormLayer)
        alsoProvides(self.request, IAttributeAnnotatable)

        # First we need to create some content.
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        _createObjectByType('gazette.GazetteFolder', self.portal, 'gazettefolder')
        self.gfolder = self.portal.gazettefolder
        self.context = self.gfolder

        # We need to fake a valid mail setup
        self.portal.email_from_address = "portal@plone.test"
        self.mailhost = self.portal.MailHost

    def tearDown(self):
        setRoles(self.portal, TEST_USER_ID, ['Manager'])
        login(self.portal, TEST_USER_NAME)
        self.portal.manage_delObjects(['gazettefolder'])

    def test_testSend(self):
        self.gfolder.invokeFactory('gazette.GazetteIssue', 'issue')
        issue = self.gfolder['issue']
        issue.title = u'Test issue'
        issue.text = RichTextValue('Hello world!')

        # DON'T USE mailhost.reset() - probably does/nt work well with functional testing.
        # If I use mailhost.reset, nothing is added to the mailhost.messages in the test
        # It seems like it creates anothe rmessages persistent list which is not visible from tests
        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.handleErrors = False
        browser.addHeader('Authorization', 'Basic %s:%s' % (TEST_USER_NAME, TEST_USER_PASSWORD,))
        browser.open(issue.absolute_url() + '/test-send')
        self.failUnless('No test email set. Please check Gazette folder settings.' in browser.contents)

        self.gfolder.test_mail = 'john@doe.com'
        transaction.commit()

        browser.open(issue.absolute_url() + '/test-send')
        self.failIf('No test email set. Please check Gazette folder settings.' in browser.contents)
        self.failUnless('Gazette test has been sent to john@doe.com')
        self.failUnless(len(self.mailhost.messages) == 1)

    def test_send_empty(self):
        self.gfolder.invokeFactory('gazette.GazetteIssue', 'issue')
        issue = self.gfolder['issue']
        issue.title = u'Test issue'
        issue.text = RichTextValue('Hello world!')

        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.handleErrors = False
        browser.addHeader('Authorization', 'Basic %s:%s' % (TEST_USER_NAME, TEST_USER_PASSWORD,))

        # no authenticater - we can't call the send_gazette directly
        self.assertRaises(Forbidden, browser.open, issue.absolute_url() + '/send_gazette')

        browser.open(issue.absolute_url() + '/send')
        self.failUnless('Number of subscribers: 0' in browser.contents)
        browser.getControl(name='submit').click()
        self.failUnless('Gazette has been sent to 0 recipients' in browser.contents)
        # no recipients but issue has been "sent" and saved as the most recent one.
        self.failUnless(self.gfolder.most_recent_issue == issue)

    def test_send_subscriber(self):
        self.gfolder.invokeFactory('gazette.GazetteIssue', 'issue')
        issue = self.gfolder['issue']
        issue.title = u'Test issue'
        issue.text = RichTextValue('Hello world!')

        request = self.request
        adapter = getMultiAdapter((self.gfolder, request), IGazetteSubscription)
        adapter.subscribe('tester@test.com', '')

        # activation message
        self.failUnless(len(self.mailhost.messages) == 1)

        # Activate subsriber
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        s = soup.query(email='tester@test.com').next()
        s.active = True
        s.key = u''
        soup.reindex([s])

        transaction.commit()
        browser = Browser(self.layer['app'])
        browser.handleErrors = False
        browser.addHeader('Authorization', 'Basic %s:%s' % (TEST_USER_NAME, TEST_USER_PASSWORD,))

        browser.open(issue.absolute_url() + '/send')
        self.failUnless('Number of subscribers: 1' in browser.contents)
        browser.getControl(name='submit').click()
        self.failUnless('Gazette has been sent to 1 recipients' in browser.contents)
        # activation + issue
        self.failUnless(len(self.mailhost.messages) == 2)
