# -*- coding: utf8 -*-
from DateTime import DateTime
from plone.app.textfield import RichText
from plone.indexer import indexer
from zope.lifecycleevent.interfaces import IObjectRemovedEvent

from zope import schema
from plone.directives import form
from five import grok
from collective.gazette import gazetteMessageFactory as _


class IGazetteIssue(form.Schema):

    text = RichText(
        title=_(u'label_body_text', default=u'Body Text. Please note, title of this item is used as email subject.'),
        required=False,
    )

    form.mode(providers='display')
    providers = schema.List(
        required=False,
        title=_(u'Providers'),
        value_type=schema.TextLine()
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
    if obj.sent_at:
        return obj.sent_at
    else:
        return DateTime()
grok.global_adapter(start_indexer, name="start")


@grok.subscribe(IGazetteIssue, IObjectRemovedEvent)
def issue_removed(obj, event):
    parent = obj.__parent__
    if parent is not None:
        if parent.most_recent_issue == obj:
            parent.most_recent_issue = None

