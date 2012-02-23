from plone.app.testing import logout
from plone.app.testing import TEST_USER_ID
from plone.app.testing import TEST_USER_NAME
from plone.app.testing import setRoles
from plone.app.testing import login
import re
import email

from zope.interface import alsoProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import Interface
from zope.component import getMultiAdapter
from zope.component import provideAdapter
from z3c.form.interfaces import IFormLayer
from cornerstone.soup import getSoup

import unittest2 as unittest
from collective.gazette.tests.layer import GAZETTE_INTEGRATION_TESTING
from Products.CMFPlone.utils import _createObjectByType
from collective.gazette import config
from collective.gazette.browser.subscribe import SubscriberForm
from collective.gazette.browser.subscribe import ActivationView
from collective.gazette.browser.subscribe import \
    WAITING_FOR_CONFIRMATION, \
    INVALID_DATA


def _parseMessage(str):
    parser = email.parser.Parser()
    return parser.parsestr(str)


class SubscriptionTest(unittest.TestCase):

    layer = GAZETTE_INTEGRATION_TESTING

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

        self.portal.acl_users.userFolderAddUser('user1',
                                               'secret',
                                               ['Member'],
                                               [])
        logout()

    def test_subscribe_anon(self):

        logout()
        provideAdapter(adapts=(Interface, IBrowserRequest),
                       provides=Interface,
                       factory=SubscriberForm,
                       name=u"subscriber-form")

        # empty form
        request = self.request
        subscriberForm = getMultiAdapter((self.context, request),
                                      name=u"subscriber-form")
        subscriberForm.update()
        data, errors = subscriberForm.extractData()
        self.assertEquals(len(errors), 1)
        self.assertEquals(subscriberForm.subscribe('', ''), INVALID_DATA)

        # fill email only
        request.form = {'form.widgets.email': u'tester@test.com'}
        subscriberForm = getMultiAdapter((self.context, request),
                                      name=u"subscriber-form")
        subscriberForm.update()
        data, errors = subscriberForm.extractData()
        self.assertEquals(len(errors), 0)
        self.assertEquals(subscriberForm.subscribe('tester@test.com', ''), WAITING_FOR_CONFIRMATION)
        self.assertEquals(len(self.mailhost.messages), 1)

        # second subscription of inactive user resends activation email
        self.assertEquals(subscriberForm.subscribe('tester@test.com', ''), WAITING_FOR_CONFIRMATION)
        self.assertEquals(len(self.mailhost.messages), 2)
        msg = _parseMessage(self.mailhost.messages[1])
        self.assertEquals(msg['To'], 'tester@test.com')
        msgtext = msg.get_payload(decode=True)
        # let's retrieve the key from the message
        groups = re.search('\?key=([a-f0-9]+)', msgtext).groups()
        self.assertEquals(len(groups), 1)
        key = groups[0]

        activationView = ActivationView(self.context, request)
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        subscriber = soup.data.values()[0]

        self.assertEquals(subscriber.email, u'tester@test.com')
        self.assertEquals(subscriber.active, False)
        self.assertEquals(subscriber.key, key)
        self.assertEquals(subscriber.username, '')
        activationView.activate(key)
        self.assertEquals(subscriber.key, u'')
        self.assertEquals(subscriber.active, True)
        self.assertEquals(subscriber.username, '')

    def test_unsubscribe_anon(self):
        logout()
        provideAdapter(adapts=(Interface, IBrowserRequest),
                       provides=Interface,
                       factory=SubscriberForm,
                       name=u"subscriber-form")

        # subscribe user
        request = self.request
        request.form = {'form.widgets.email': u'tester@test.com'}
        subscriberForm = getMultiAdapter((self.context, request),
                                      name=u"subscriber-form")
        subscriberForm.update()
        data, errors = subscriberForm.extractData()
        self.assertEquals(subscriberForm.subscribe('tester@test.com', ''), WAITING_FOR_CONFIRMATION)

        msg = _parseMessage(self.mailhost.messages[0])
        self.assertEquals(msg['To'], 'tester@test.com')
        msgtext = msg.get_payload(decode=True)

        groups = re.search('\?key=([a-f0-9]+)', msgtext).groups()
        self.assertEquals(len(groups), 1)
        key = groups[0]

        # activate
        activationView = ActivationView(self.context, request)
        activationView.activate(key)

        self.assertEquals(subscriberForm.unsubscribe('tester@test.com'), WAITING_FOR_CONFIRMATION)
        msg = _parseMessage(self.mailhost.messages[1])
        msgtext = msg.get_payload(decode=True)
        key = re.search('\?key=([a-f0-9]+)', msgtext).groups()[0]
        # deactivate
        activationView.deactivate(key)
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        subscriber = soup.data.values()[0]
        self.assertEquals(subscriber.active, False)

    def test_subscribe_user(self):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        user = self.portal.acl_users.getUserById('user1')
        user.setProperties(email='user@dummy.com', fullname='Joe User')
        login(self.portal, 'user1')

        request = self.request
        subscriberForm = getMultiAdapter((self.context, request),
                                      name=u"subscriber-form")
        subscriberForm.update()
        data, errors = subscriberForm.extractData()
        # email and fullname are prefilled
        self.assertEquals(len(errors), 0)
        # even if I provide different email, it is ignored.
        self.assertEquals(subscriberForm.subscribe('bleh@blah.com', 'Dummy', 'user1'), WAITING_FOR_CONFIRMATION)

        subscriber = soup.data.values()[0]
        self.assertEquals(subscriber.active, False)
        self.assertEquals(subscriber.email, 'user@dummy.com')
        self.assertEquals(subscriber.username, 'user1')

    def test_subscribe_1000users(self):
        logout()
        provideAdapter(adapts=(Interface, IBrowserRequest),
                       provides=Interface,
                       factory=SubscriberForm,
                       name=u"subscriber-form")

        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        request = self.request
        subscriberForm = getMultiAdapter((self.context, request),
                                      name=u"subscriber-form")
        subscriberForm.update()
        # from time import time
        # print "Subscription process start"
        # start = time()
        for i in range(1, 1001):
            self.assertEquals(subscriberForm.subscribe('bleh@blah-%d.com' % i, 'Dummy %d' % i), WAITING_FOR_CONFIRMATION)
        # print "Subscription process: %.2fsec." % (time() - start)

        # start = time()
        subscribers = soup.data.values()
        self.assertEquals(len(subscribers), 1000)
        # print "Retrieve all subscribers: %.5fsec." % (time() - start)

        # start = time()
        subscriber = soup.query(email='bleh@blah-149.com').next()
        self.assertEquals(subscriber.fullname, 'Dummy 149')
        # print "Search for one subscriber: %.5fsec." % (time() - start)
