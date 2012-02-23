# -*- coding: utf8 -*-
from plone.app.textfield import RichText
from plone.indexer import indexer

from zope import schema
from plone.directives import form
from five import grok

from collective.gazette import gazetteMessageFactory as _


class IGazetteIssue(form.Schema):

    text = RichText(
        title=_(u'label_body_text', default=u'Body Text. Please note, title of this item is used as email subject.'),
        required=False,
    )

    providers = schema.List(
        required=False,
        title=_(u'Providers'),
        default=[],
        value_type=schema.Choice(
            vocabulary='collective.gazette.ProvidersVocabulary',
        )
    )

    form.mode(sent_at='display')
    sent_at = schema.Datetime(
        required=False,
        title=_(u'Sent at'),
        description=_(u'Date, when last newsletter was sent'),
    )


# Use catalog 'start' index for sent_at for Gazette
@indexer(IGazetteIssue)
def start_indexer(obj):
    return obj.sent_at
grok.global_adapter(start_indexer, name="start")
