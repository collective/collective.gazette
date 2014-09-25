# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from zope.component import getMultiAdapter
from z3c.form.interfaces import IAddForm
from z3c.form.interfaces import IDisplayForm
from z3c.form.interfaces import IEditForm
from five import grok
from zope import schema
from zope.interface import Invalid
from plone.autoform import directives
from plone.directives import form
from plone.supermodel import model
from z3c.form import button
from cornerstone.soup import getSoup
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName
from zExceptions import Forbidden
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from collective.gazette.utils import checkEmail
from collective.gazette import config
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteLayer
from collective.gazette.interfaces import IGazetteSubscription
from collective.gazette import gazetteMessageFactory as _
from collective.gazette.vocabulary import optionalProvidersSource
try:
    from zope.component.hooks import getSite
except ImportError:
    from zope.app.component.hooks import getSite


def validateEmail(value):
    if value and not checkEmail(value):
        raise Invalid(_(u"Invalid email format"))
    return True


def validateAccept(value):
    if not (value is True):
        raise Invalid(_(u"You must accept terms of service"))
    return True


class ISubscriberSchema(model.Schema):
    directives.mode(for_member='hidden')
    for_member = schema.TextLine(title=_(u"You are logged in. The following details will be used for your subscription"), required=False)

    form.widget('email', size=40)
    email = schema.TextLine(title=_(u"Email"), constraint=validateEmail)

    form.widget('fullname', size=40)
    fullname = schema.TextLine(title=_(u"Fullname"), required=False)

    directives.omitted('active')
    active = schema.Bool(title=u"Active")

    directives.omitted('username')
    username = schema.Bool(title=u"Username, if member")

    form.widget('salutation', size=40)
    salutation = schema.TextLine(
        title=_(u"Optional salutation"),
        required=False,
        default=u''
    )

    directives.widget(providers=CheckBoxFieldWidget)
    providers = schema.List(
        title=_(u'Optional content'),
        default=list(),
        required=False,
        value_type=schema.Choice(
            source=optionalProvidersSource,
        )
    )

    tos = schema.Bool(title=u"TOS", required=False)


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

    @property
    def subscriber(self):
        uuid = self.request.form.get('uuid')
        value = None
        if uuid:
            value = getattr(self, '_v_subscriber', None)
            soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
            for s in soup.query(uuid=uuid):
                self._v_subscriber = value = s
                break
        return value

    def getContent(self):
        result = dict(context=self.context)
        if self.subscriber:
            result.update(self.subscriber.__dict__)
        return result

    def update(self):
        super(SubscriberForm, self).update()
        self.request.set('disable_border', 1)

    def updateFields(self):
        super(SubscriberForm, self).updateFields()
        if not self.subscriber:
            self.fields['tos'].field.title = self.context.subscription_tos_text
            if self.context.subscription_require_tos:
                self.fields['tos'].field.constraint = validateAccept

    def updateWidgets(self):
        super(SubscriberForm, self).updateWidgets()
        context = aq_inner(self.context)
        pstate = getMultiAdapter((context, self.request), name='plone_portal_state')
        cstate = getMultiAdapter((context, self.request), name='plone_context_state')
        subscriber = self.subscriber
        if subscriber or not context.subscription_require_tos:
            self.widgets['tos'].mode = 'hidden'

        if not optionalProvidersSource(context):
            self.widgets['providers'].mode = 'hidden'

        if pstate.anonymous():
            self.widgets['for_member'].mode = 'hidden'
        else:
            if not cstate.is_editable():
                # Editor can modify subscribers
                self.widgets['for_member'].mode = 'display'
                self.widgets['email'].mode = 'display'
                self.widgets['fullname'].mode = 'display'

    def updateActions(self):
        super(SubscriberForm, self).updateActions()
        self.actions["subscribe"].addClass("context")
        self.actions["unsubscribe"].addClass("context")
        subscriber = self.subscriber

        if subscriber:
            if subscriber.active:
                del self.actions['subscribe']
            if not subscriber.active:
                del self.actions['unsubscribe']
        else:
            del self.actions['unsubscribe']

    @button.buttonAndHandler(_(u"subscribe", default=_(u"Subscribe")),
                             name='subscribe')
    def handleSubscribe(self, action):
        """ This form should be used for anonymous subscribers only (not for portal users currently) """
        context = self.context
        data, errors = self.extractData()
        ptool = getToolByName(self.context, 'plone_utils')
        level = 'info'
        msg = ''
        res = None
        if context.subscription_require_tos:
            if not data.get('tos'):
                msg = _(u'You must accept terms of service')

        if not msg:
            subs = getMultiAdapter((self.context, self.request), interface=IGazetteSubscription)
            if 'email' in data:
                res = subs.subscribe(data['email'], data['fullname'], providers=data['providers'], salutation=data['salutation'])
            else:
                msg = _(u'Invalid form data.')
                level = 'error'

            if res == config.ALREADY_SUBSCRIBED:
                msg = _(u'This subscription already exists.')
                ptool.addPortalMessage(msg, level)
            elif res == config.WAITING_FOR_CONFIRMATION:
                msg = _(u'Subscription confirmation email has been sent. Please follow instruction in the email.')
                ptool.addPortalMessage(msg, level)
                self.request.response.redirect(self.context.absolute_url())

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
        self.request.response.redirect(self.context.absolute_url())


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
