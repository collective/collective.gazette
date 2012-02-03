import random

import hashlib
from zope import interface, schema
from z3c.form import form, field, button
from plone.z3cform.layout import FormWrapper
from cornerstone.soup import getSoup
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.stringinterp.interfaces import IStringInterpolator
from zExceptions import Forbidden

from collective.gazette import config
from collective.gazette import utils
from collective.gazette.subscribers import Subscriber

from collective.gazette import gazetteMessageFactory as _


class ISubscriber(interface.Interface):
    email = schema.TextLine(title=_(u"Email"))
    fullname = schema.TextLine(title=_(u"Fullname"), required=False)
    active = schema.Bool(title=u"Active")

ALREADY_SUBSCRIBED = 0
WAITING_FOR_CONFIRMATION = 1
SUBSCRIPTION_SUCCESSFULL = 2
NO_SUCH_SUBSCRIPTION = 3
ALREADY_UNSUBSCRIBED = 4
INVALID_DATA = 5


def GenerateSecret(length=64):
    secret = ""
    for i in range(length):
        secret += chr(random.getrandbits(8))

    return hashlib.sha1(secret).hexdigest()


class SubscriberForm(form.Form):

    activation_template = ViewPageTemplateFile('activation.pt')
    deactivation_template = ViewPageTemplateFile('deactivation.pt')

    fields = field.Fields(ISubscriber).omit('active')
    ignoreContext = True
    ignoreRequest = False
    label = _(u"Subscription form")

    def activation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.activation_template(key=subscriber.key))
        subject = _(u"Please activate your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def deactivation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.deactivation_template(key=subscriber.key))
        subject = _(u"Please confirm deactivation of your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def subscribe(self, email, fullname):
        # find if there is not existing subscription
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        if not email.strip():
            return INVALID_DATA
        results = [r for r in soup.query(email=email)]
        if results:
            if results[0].active:
                return ALREADY_SUBSCRIBED
            else:
                s = results[0]
                s.key = GenerateSecret()
                soup.reindex([s])
                self.activation_mail(s)
                return WAITING_FOR_CONFIRMATION
        else:
            # new subscriber
            s = Subscriber(email=email, fullname=fullname, active=False)
            s.key = GenerateSecret()
            soup.add(s)
            self.activation_mail(s)
            return WAITING_FOR_CONFIRMATION

    def unsubscribe(self, email):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(email=email)]
        if results:
            if not results[0].active:
                return ALREADY_UNSUBSCRIBED
            else:
                s = results[0]
                s.key = GenerateSecret()
                soup.reindex([s])
                self.deactivation_mail(s)
                return WAITING_FOR_CONFIRMATION
        else:
            return NO_SUCH_SUBSCRIPTION

    @button.buttonAndHandler(_(u"subscribe", default=_(u"Subscribe")),
                             name='subscribe')
    def handleSubscribe(self, action):
        data, errors = self.extractData()
        if data.has_key('email'):
            ptool = getToolByName(self.context, 'plone_utils')
            res = self.subscribe(data['email'], data['fullname'])
            if res == ALREADY_SUBSCRIBED:
                ptool.addPortalMessage(_(u'This subscription already exists.'))
            elif res == WAITING_FOR_CONFIRMATION:
                ptool.addPortalMessage(_(u'Subscription confirmation email has been sent. Please follow instruction in the email.'))
        self.request.response.redirect(self.action)

    @button.buttonAndHandler(_(u"unsubscribe", default=_(u"Unsubscribe")),
                             name='unsubscribe')
    def handleUnsubscribe(self, action):
        data, errors = self.extractData()
        if data.has_key('email'):
            ptool = getToolByName(self.context, 'plone_utils')
            res = self.unsubscribe(data['email'])
            if res == ALREADY_UNSUBSCRIBED:
                ptool.addPortalMessage(_(u'You are not subscribed.'))
            elif res == WAITING_FOR_CONFIRMATION:
                ptool.addPortalMessage(_(u'Unsubscribe confirmation email has been sent. Please follow instruction in the email.'))
            elif res == NO_SUCH_SUBSCRIPTION:
                ptool.addPortalMessage(_(u'Such subscription does not exist.'))
        self.request.response.redirect(self.action)


class SubscriberView(FormWrapper):
    form = SubscriberForm

    def __init__(self, context, request):
        FormWrapper.__init__(self, context, request)
        request.set('disable_border', 1)


class ActivationView(BrowserView):

    def activate(self, key):
        """ """
        if not key:
            raise Forbidden('Authenticator is invalid.')
        ptool = getToolByName(self.context, 'plone_utils')
        # get subscriber by key
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(key=key)]
        if len(results) != 1:
            ptool.addPortalMessage(_(u'Invalid key'))
        else:
            s = results[0]
            s.active = True
            s.key = u''
            soup.reindex([s])
            ptool.addPortalMessage(_(u'Your subscription has been successfully activated.'))
        self.request.response.redirect(self.context.absolute_url() + '/subscription')

    def deactivate(self, key):
        """ """
        if not key:
            raise Forbidden('Authenticator is invalid.')
        ptool = getToolByName(self.context, 'plone_utils')
        # get subscriber by key
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(key=key)]
        if len(results) != 1:
            ptool.addPortalMessage(_(u'Invalid key'))
        else:
            s = results[0]
            s.active = False
            s.key = u''
            soup.reindex([s])
            ptool.addPortalMessage(_(u'Your subscription has been successfully deactivated.'))
        self.request.response.redirect(self.context.absolute_url() + '/subscription')
