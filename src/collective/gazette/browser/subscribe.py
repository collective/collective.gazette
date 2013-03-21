from Acquisition import aq_inner
from zope.component import getMultiAdapter
from five import grok
from zope import schema
from zope.app.component.hooks import getSite
from plone.directives import form
from z3c.form import button
from cornerstone.soup import getSoup
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from zExceptions import Forbidden
from zope.interface import Invalid

from collective.gazette.utils import checkEmail
from collective.gazette import config
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteLayer
from collective.gazette.interfaces import IGazetteSubscription

from collective.gazette import gazetteMessageFactory as _


def validateEmail(value):
    if value and not checkEmail(value):
        raise Invalid(_(u"Invalid email format"))
    return True


class ISubscriberSchema(form.Schema):
    form.mode(for_member='hidden')
    for_member = schema.TextLine(title=_(u"You are logged in. The following details will be used for your subscription"), required=False)
    email = schema.TextLine(title=_(u"Email"), constraint=validateEmail)
    fullname = schema.TextLine(title=_(u"Fullname"), required=False)
    form.omitted('active')
    active = schema.Bool(title=u"Active")
    form.omitted('username')
    username = schema.Bool(title=u"Username, if member")
    tos = schema.Bool(title=u"TOS")


@form.default_value(field=ISubscriberSchema['email'])
def default_email(data, *args):
    mtool = getToolByName(getSite(), 'portal_membership')
    member = mtool.getAuthenticatedMember()
    if member:
        return member.getProperty('email', '')
    return u''


@form.default_value(field=ISubscriberSchema['fullname'])
def default_fullname(data, *args):
    mtool = getToolByName(getSite(), 'portal_membership')
    member = mtool.getAuthenticatedMember()
    if member:
        return member.getProperty('fullname', '')
    return u''


class SubscriberForm(form.SchemaForm):
    grok.context(IGazetteFolder)
    grok.name('subscription')
    grok.layer(IGazetteLayer)

    schema = ISubscriberSchema

    ignoreContext = False
    ignoreRequest = False
    label = _(u"Subscription form")

    def getContent(self):
        return {}

    def update(self):
        super(SubscriberForm, self).update()
        self.request.set('disable_border', 1)

    def updateFields(self):
        super(SubscriberForm, self).updateFields()
        self.fields['tos'].field.title = self.context.subscription_tos_text

    def updateWidgets(self):
        super(SubscriberForm, self).updateWidgets()
        pstate = getMultiAdapter((self.context, self.request), name='plone_portal_state')
        context = aq_inner(self.context)
        if not context.subscription_require_tos:
            self.widgets['tos'].mode = 'hidden'

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
        context = self.context
        data, errors = self.extractData()

        pstate = getMultiAdapter((self.context, self.request), name='plone_portal_state')
        ptool = getToolByName(self.context, 'plone_utils')
        level = 'info'
        msg = ''
        res = None
        if context.subscription_require_tos:
            if not data.get('tos'):
                msg = _(u'You must accept terms of service')

        if not msg:
            subs = getMultiAdapter((self.context, self.request), interface=IGazetteSubscription)
            if pstate.anonymous():
                if 'email' in data:
                    res = subs.subscribe(data['email'], data['fullname'])
                else:
                    msg = _(u'Invalid form data.')
                    level = 'error'
            else:
                if not default_email(self):
                    msg = _(u'Your user account has no email defined.')
                    level = 'error'
                else:
                    res = subs.subscribe('', '', username=pstate.member().getUserName())

            if res == config.ALREADY_SUBSCRIBED:
                msg = _(u'This subscription already exists.')
            elif res == config.WAITING_FOR_CONFIRMATION:
                msg = _(u'Subscription confirmation email has been sent. Please follow instruction in the email.')

        if msg:
            ptool.addPortalMessage(msg, level)
        else:
            self.request.response.redirect(self.action)

    @button.buttonAndHandler(_(u"unsubscribe", default=_(u"Unsubscribe")),
                             name='unsubscribe')
    def handleUnsubscribe(self, action):
        """ This form should be used for anonymous subscribers only (not for portal users currently) """
        data, errors = self.extractData()
        ptool = getToolByName(self.context, 'plone_utils')
        if 'email' in data:
            subs = getMultiAdapter((self.context, self.request), interface=IGazetteSubscription)
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
        self.request.response.redirect(self.context.absolute_url())

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
        self.request.response.redirect(self.context.absolute_url())