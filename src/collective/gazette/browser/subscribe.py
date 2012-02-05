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
from zExceptions import Forbidden

from collective.gazette import config
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteLayer
from collective.gazette.interfaces import IGazetteSubscription

from collective.gazette import gazetteMessageFactory as _


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


class SubscriberForm(form.SchemaForm):
    grok.context(IGazetteFolder)
    grok.name('subscription')
    grok.layer(IGazetteLayer)

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
        subs = IGazetteSubscription(self.context)
        if pstate.anonymous():
            if data.has_key('email'):
                res = subs.subscribe(data['email'], data['fullname'])
            else:
                msg = _(u'Invalid form data.')
                level = 'error'
        else:
            res = subs.subscribe('', '', username=pstate.member().getUserName())

        if res == config.ALREADY_SUBSCRIBED:
            msg = _(u'This subscription already exists.')
        elif res == config.WAITING_FOR_CONFIRMATION:
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
            subs = IGazetteSubscription(self.context)
            res = subs.unsubscribe(data['email'])
            if res == config.ALREADY_UNSUBSCRIBED:
                ptool.addPortalMessage(_(u'You are not subscribed.'))
            elif res == config.WAITING_FOR_CONFIRMATION:
                ptool.addPortalMessage(_(u'Unsubscribe confirmation email has been sent. Please follow instruction in the email.'))
            elif res == config.NO_SUCH_SUBSCRIPTION:
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