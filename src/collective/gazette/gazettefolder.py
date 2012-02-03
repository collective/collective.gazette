# -*- coding: utf8 -*-
from Products.CMFPlone.i18nl10n import ulocalized_time
from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from zope.interface import Invalid
from plone.app.textfield import RichText
from collective.gazette import gazetteMessageFactory as _
from plone.directives import form
from zope import schema
from collective.gazette.utils import checkEmail
from cornerstone.soup.interfaces import ISoupAnnotatable
from five import grok


def validateEmail(value):
    if value and not checkEmail(value):
        raise Invalid(u"Neplatný formát emailu")
    return True


class IGazetteFolder(form.Schema, ISoupAnnotatable):

    test_mail = schema.ASCIILine(
        title=_('Test email'),
        description=_(u'Testing email address'),
        required=False,
        constraint=validateEmail,
    )

    footer = RichText(
        required=False,
        title=_('Gazette footer text'),
        description=_('Please enter text appended to each email '
                      'sent to users. It should contain $url '
                      'placeholder which will be replaced with '
                      'unsubscription url link'),
        default=u"Unsubscribe at $url",
    )


class View(grok.View):
    grok.context(IGazetteFolder)
    grok.require('zope2.View')
    grok.name('view')

    def issues(self):
        context = aq_inner(self.context)
        path = '/'.join(context.getPhysicalPath())
        result = []
        ctool = getToolByName(context, 'portal_catalog')
        for brain in ctool(portal_type='gazette.Gazette',
                           path=path,
                           sort_on='start',
                           sort_order='reverse'):
            result.append(dict(
                title=brain.Title,
                url=brain.getURL(),
                date=ulocalized_time(brain.start, 0, context=context)
            ))
        return result
