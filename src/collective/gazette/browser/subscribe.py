from zope.component import getMultiAdapter
import random

import hashlib
from five import grok
from zope import schema
from plone.directives import form
from z3c.form import button
from cornerstone.soup import getSoup
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.stringinterp.interfaces import IStringInterpolator
from zExceptions import Forbidden

from collective.gazette import config
from collective.gazette import utils
from collective.gazette.subscribers import Subscriber
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteLayer

from collective.gazette import gazetteMessageFactory as _

ALREADY_SUBSCRIBED = 0
WAITING_FOR_CONFIRMATION = 1
SUBSCRIPTION_SUCCESSFULL = 2
NO_SUCH_SUBSCRIPTION = 3
ALREADY_UNSUBSCRIBED = 4
INVALID_DATA = 5


class ISubscriberSchema(form.Schema):
    form.mode(for_member='hidden')
    for_member = schema.TextLine(title=_(u"You are logged in. The following details will be used for your subscription"), required=False)
    email = schema.TextLine(title=_(u"Email"))
    fullname = schema.TextLine(title=_(u"Fullname"), required=False)
    form.omitted('active')
    active = schema.Bool(title=u"Active")
    form.omitted('username')
    username = schema.Bool(title=u"Username, if member")


@form.default_value(field=ISubscriberSchema['email'])
def default_email(data, *args):
    mtool = getToolByName(data.context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    if member:
        return member.getProperty('email', '')
    return u''


@form.default_value(field=ISubscriberSchema['fullname'])
def default_fullname(data, *args):
    mtool = getToolByName(data.context, 'portal_membership')
    member = mtool.getAuthenticatedMember()
    if member:
        return member.getProperty('fullname', '')
    return u''


def GenerateSecret(length=64):
    secret = ""
    for i in range(length):
        secret += chr(random.getrandbits(8))

    return hashlib.sha1(secret).hexdigest()


class SubscriberForm(form.SchemaForm):
    grok.context(IGazetteFolder)
    grok.name('subscription')
    grok.layer(IGazetteLayer)

    activation_template = ViewPageTemplateFile('activation.pt')
    deactivation_template = ViewPageTemplateFile('deactivation.pt')

    schema = ISubscriberSchema

    ignoreContext = True
    ignoreRequest = False
    label = _(u"Subscription form")

    def update(self):
        super(SubscriberForm, self).update()
        self.request.set('disable_border', 1)

    def updateWidgets(self):
        super(SubscriberForm, self).updateWidgets()
        pstate = getMultiAdapter((self.context, self.request), name='plone_portal_state')
        if pstate.anonymous():
            self.widgets['for_member'].mode = 'hidden'
        else:
            self.widgets['for_member'].mode = 'display'
            self.widgets['email'].mode = 'display'
            self.widgets['fullname'].mode = 'display'

    def activation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.activation_template(key=subscriber.key))
        subject = _(u"Please activate your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def deactivation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.deactivation_template(key=subscriber.key))
        subject = _(u"Please confirm deactivation of your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def subscribe(self, email, fullname, username=u''):
        # find if there is existing subscription
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        email = email.strip()
        if username:
            # ignore everything
            acl = getToolByName(self.context, 'acl_users')
            user = acl.getUserById(username)
            if user:
                email = user.getProperty('email', '')
                if email:
                    # subscribe as portal user
                    # is username is set, subscription is considered as subscription of portal member
                    # override fullname, if any
                    fullname = user.getProperty('fullname', fullname)

        if not email:
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
            s = Subscriber(email=email, fullname=fullname, active=False, username=username)
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
        """ This form should be used for anonymous subscribers only (not for portal users currently) """
        data, errors = self.extractData()
        pstate = getMultiAdapter((self.context, self.request), name='plone_portal_state')
        ptool = getToolByName(self.context, 'plone_utils')
        level = 'info'
        msg = ''
        res = None
        if pstate.anonymous():
            if data.has_key('email'):
                res = self.subscribe(data['email'], data['fullname'])
            else:
                msg = _(u'Invalid form data.')
                level = 'error'
        else:
            res = self.subscribe('', '', username=pstate.member().getUserName())

        if res == ALREADY_SUBSCRIBED:
            msg = _(u'This subscription already exists.')
        elif res == WAITING_FOR_CONFIRMATION:
            msg = _(u'Subscription confirmation email has been sent. Please follow instruction in the email.')

        if msg:
            ptool.addPortalMessage(msg, level)
        self.request.response.redirect(self.action)

    @button.buttonAndHandler(_(u"unsubscribe", default=_(u"Unsubscribe")),
                             name='unsubscribe')
    def handleUnsubscribe(self, action):
        """ This form should be used for anonymous subscribers only (not for portal users currently) """
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
        else:
            ptool.addPortalMessage(_(u'Invalid form data. Email is missing.'), 'error')
        self.request.response.redirect(self.action)


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