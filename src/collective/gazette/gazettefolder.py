# -*- coding: utf8 -*-
from plone.formwidget.contenttree import PathSourceBinder
from collective.gazette.issue import IGazetteIssue
from plone.z3cform.textlines.textlines import TextLinesFieldWidget
from plone.supermodel.model import Fieldset
from plone.supermodel.interfaces import FIELDSETS_KEY
from Products.CMFPlone.i18nl10n import ulocalized_time
from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName
from zope.interface import Invalid
from plone.app.textfield import RichText
from collective.gazette import gazetteMessageFactory as _
from plone.directives import form
from zope import schema
from z3c.relationfield.schema import RelationChoice
from collective.gazette.utils import checkEmail
from collective.gazette.utils import FieldWidgetFactory
from cornerstone.soup.interfaces import ISoupAnnotatable
from five import grok


def validateEmail(value):
    if value and not checkEmail(value):
        raise Invalid(_(u"Invalid email format"))
    return True


TextFieldWidgetRows15 = FieldWidgetFactory(TextLinesFieldWidget,
                            rows=15)


class IGazetteFolder(form.Schema, ISoupAnnotatable):

    test_mail = schema.ASCIILine(
        title=_('Test email'),
        description=_(u'Testing email address'),
        required=False,
        constraint=validateEmail,
    )

    subscription_prolog = RichText(
        required=False,
        title=_('Subscription prolog'),
        description=_('Please enter text displayed on subscription page '
                      'before fields for fullname and email.'),
        default=u"",
    )

    subscription_require_tos = schema.Bool(
        required=False,
        default=True,
        title=_('Require confirmation of TOS on the subscription screen?'),
    )

    subscription_tos_text = schema.TextLine(
        required=False,
        title=_('Subscription TOS text'),
        description=_('Please enter text displayed on subscription page '
                      'as a label for Terms of Service checkbox.'),
        default=u"I accept your TOS",
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

    form.mode(most_recent_issue='display')
    most_recent_issue = RelationChoice(
        title=_(u'label_most_recent_issue', default=u'Most recent issue of this gazette. This field is set automatically.'),
        required=False,
        source=PathSourceBinder(object_provides=IGazetteIssue.__identifier__)
    )

    auto_enabled = schema.Bool(
        title=_(u'label_auto_enabled', default=u'Enable automated newsletters'),
        default=False,
    )

    auto_subject = schema.TextLine(
        title=_('Automated issue email subject'),
        description=_(u'Enter email subject. You can use any strftime compatible '
                      u'formatting. The current date and time will be used to format date/time.'),
        default=u'New issue at %-d.%-m.%Y',
        required=False,
    )

    auto_text = RichText(
        title=_(u'label_auto_text', default=u'Body Text (for automated newsletters)'),
        description=_(u'help_auto_text', default=u'Initial body text for automated '
                                                 u'newsletters. See also "Providers" field below. '
                                                 u'Text may contain strftime formatting.'),
        required=False,
    )

    auto_providers = schema.List(
        required=False,
        title=_(u'Providers (for automated newsletters)'),
        default=list(),
        value_type=schema.Choice(
            vocabulary='collective.gazette.ProvidersVocabulary',
        )
    )

    form.widget(auto_template='collective.gazette.gazettefolder.TextFieldWidgetRows15')
    auto_template = schema.Text(
        required=False,
        default=u"""<!doctype html>
<html>
<head>
<meta http-equiv="content-type" content="text/html; charset=utf-8" />
</head>
<body>
${body}
</body>
</html>
""",
        title=_(u'title_auto_template', default=u'HTML template for PDF version of the automated issue'),
        description=_(u'help_auto_template', default=u'This field contains base of HTML file which will be '
                      u'used for generating PDF version of the newsletter.'
                      u'It must contain ${body} element which will be replaced by actual issue HTML code.'),
    )

IGazetteFolder.setTaggedValue(FIELDSETS_KEY,
                                [Fieldset('automated', fields=['auto_enabled', 'auto_subject',
                                                               'auto_text', 'auto_providers',
                                                               'auto_template'],
                                          label=_('fieldset_label_auto_issues', default=u"Automated issues"),
                                          description=_('fieldset_help_auto_issues', u'Settings for automated issues. '
                                                      u'If you want to automatically generate issues, for example from cron '
                                                      u'every week, check this field and set text and providers fields below. '
                                                      u'Call @@auto-issue browser view in regular intervals on this GazetteFolder. '
                                                      u'Issues will be created automatically and marked as sent every time you call '
                                                      u'the @@auto-issue page.')
                                          )])


class View(grok.View):
    grok.context(IGazetteFolder)
    grok.require('zope2.View')
    grok.name('view')

    def issues(self):
        context = aq_inner(self.context)
        path = '/'.join(context.getPhysicalPath())
        result = []
        ctool = getToolByName(context, 'portal_catalog')
        for brain in ctool(portal_type='gazette.GazetteIssue',
                           path=path,
                           sort_on='start',
                           sort_order='reverse'):
            result.append(dict(
                title=brain.Title,
                url=brain.getURL(),
                date=ulocalized_time(brain.start, 0, context=context)
            ))
        return result
