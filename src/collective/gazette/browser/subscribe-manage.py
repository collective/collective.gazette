# -*- coding: utf-8 -*-
from zope.component import getMultiAdapter
from five import grok
from zope import schema
from zope.interface import Invalid
from plone.autoform import directives
from plone.directives import form
from plone.supermodel import model
from z3c.form import button
from cornerstone.soup import getSoup
from Products.CMFCore.utils import getToolByName
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from collective.gazette.utils import checkEmail
from collective.gazette import config
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteLayer
from collective.gazette.interfaces import IGazetteSubscription
from collective.gazette import gazetteMessageFactory as _
from collective.gazette.vocabulary import optionalProvidersSource


def validateEmail(value):
    if value and not checkEmail(value):
        raise Invalid(_(u"Invalid email format"))
    return True


class IManageSubscriberSchema(model.Schema):
    form.widget('email', size=40)
    email = schema.TextLine(title=_(u"Email"), constraint=validateEmail)

    form.widget('fullname', size=40)
    fullname = schema.TextLine(title=_(u"Fullname"), required=False)

    active = schema.Bool(title=_(u"Active - receives emails"))

    directives.mode(username='display')
    username = schema.Bool(title=u"Username, if member")

    directives.mode(uuid='hidden')
    uuid = schema.TextLine(title=u"UIID")

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


class SubscriberForm(form.SchemaForm):
    grok.context(IGazetteFolder)
    grok.name('subscription-manage')
    grok.layer(IGazetteLayer)
    grok.require('cmf.ModifyPortalContent')

    schema = IManageSubscriberSchema

    ignoreContext = False
    ignoreRequest = False
    label = _(u"Manage subscription form")

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

    # def update(self):
    #     super(SubscriberForm, self).update()
    #     self.request.set('disable_border', 1)

    def updateActions(self):
        super(SubscriberForm, self).updateActions()
        self.actions["update"].addClass("standalone")

    @button.buttonAndHandler(_(u"update", default=_(u"Update")),
                             name='update')
    def handleUpdate(self, action):
        data, errors = self.extractData()
        ptool = getToolByName(self.context, 'plone_utils')

        subs = getMultiAdapter((self.context, self.request), interface=IGazetteSubscription)
        uuid = data['uuid']
        del data['uuid']
        subs.update(uuid, **data)
        ptool.addPortalMessage(_(u'The subscription has been updated.'))
        self.request.response.redirect(self.action + '?uuid=' + uuid)
