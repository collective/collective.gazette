import re
import email
from Acquisition import aq_base
from zope.interface import alsoProvides
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.annotation.interfaces import IAttributeAnnotatable
from zope.interface import Interface
from zope.component import getMultiAdapter
from zope.publisher.browser import TestRequest
from zope.component import provideAdapter
from z3c.form.interfaces import IFormLayer
import unittest
from zope.component import getSiteManager

from Products.MailHost.interfaces import IMailHost
from Products.CMFPlone.tests.utils import MockMailHost

from cornerstone.soup import getSoup
from Products.PloneTestCase.ptc import PloneTestCase
from collective.gazette.tests.layer import GazetteLayer

from collective.gazette import config
from collective.gazette.browser.subscribe import SubscriberForm
from collective.gazette.browser.subscribe import ActivationView
from collective.gazette.browser.subscribe import \
    ALREADY_SUBSCRIBED, \
    WAITING_FOR_CONFIRMATION, \
    SUBSCRIPTION_SUCCESSFULL, \
    NO_SUCH_SUBSCRIPTION, \
    ALREADY_UNSUBSCRIBED, \
    INVALID_DATA

def _parseMessage(str):
    parser = email.parser.Parser()
    return parser.parsestr(str) 

def make_request(form={}):
    request = TestRequest()
    request.form.update(form)
    alsoProvides(request, IFormLayer)
    alsoProvides(request, IAttributeAnnotatable)
    return request        

class SubscriptionTest(PloneTestCase):

    layer = GazetteLayer

    def afterSetUp(self):
        # First we need to create some content.
        self.loginAsPortalOwner()
        typetool = self.portal.portal_types
        typetool.constructContent('GazetteFolder', self.portal, 'gazettefolder')
        self.gfolder = self.portal.gazettefolder
        self.request = self.app.REQUEST
        self.context = self.gfolder

        # Set up a mock mailhost
        self.portal._original_MailHost = self.portal.MailHost
        self.portal.MailHost = mailhost = MockMailHost('MailHost')
        sm = getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(mailhost, provided=IMailHost)

        # We need to fake a valid mail setup
        self.portal.email_from_address = "portal@plone.test"
        self.mailhost = self.portal.MailHost

    def beforeTearDown(self):
        self.portal.MailHost = self.portal._original_MailHost
        sm = getSiteManager(context=self.portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(aq_base(self.portal._original_MailHost), 
                           provided=IMailHost)
                
    def test_subscribe(self):

        provideAdapter(adapts=(Interface, IBrowserRequest),
                       provides=Interface,
                       factory=SubscriberForm,
                       name=u"subscriber-form")

        # empty form
        request = make_request(form={})
        subscriberForm = getMultiAdapter((self.context, request), 
                                      name=u"subscriber-form")
        subscriberForm.update()
        data, errors = subscriberForm.extractData()
        self.assertEquals(len(errors), 1)
        self.assertEquals(subscriberForm.subscribe('', ''), INVALID_DATA)

        # fill email only
        request = make_request(form={'form.widgets.email': 'tester@test.com'})
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
        activationView.activate(key)
        self.assertEquals(subscriber.key, u'')
        self.assertEquals(subscriber.active, True)

    def test_unsubscribe(self):
        provideAdapter(adapts=(Interface, IBrowserRequest),
                       provides=Interface,
                       factory=SubscriberForm,
                       name=u"subscriber-form")

        # subscribe user
        request = make_request(form={'form.widgets.email': 'tester@test.com'})
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

def test_suite():
    return unittest.defaultTestLoader.loadTestsFromName(__name__)
