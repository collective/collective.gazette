from datetime import datetime
from zope.component import queryUtility
from Products.CMFCore.utils import getToolByName
from Acquisition import aq_parent
from Acquisition import aq_inner
from zope.component import getMultiAdapter
from Products.Five import BrowserView
from plone.memoize import view
from plone.protect import CheckAuthenticator
from smtplib import SMTPRecipientsRefused
from smtplib import SMTPException

from cornerstone.soup import getSoup
from collective.gazette import gazetteMessageFactory as _
from collective.gazette import config
from collective.gazette import utils
from collective.gazette.interfaces import IGazetteTextProvider


class GazetteIssueView(BrowserView):

    @view.memoize_contextless
    def tools(self):
        """ returns tools view. Available items are all portal_xxxxx
            For example: catalog, membership, url
            http://dev.plone.org/plone/browser/plone.app.layout/trunk/plone/app/layout/globals/tools.py
        """
        return getMultiAdapter((self.context, self.request), name=u"plone_tools")

    @view.memoize_contextless
    def portal_state(self):
        """ returns
            http://dev.plone.org/plone/browser/plone.app.layout/trunk/plone/app/layout/globals/portal.py
        """
        return getMultiAdapter((self.context, self.request), name=u"plone_portal_state")

    def count(self):
        """ Number of subscribers """
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        return len([x for x in soup.lazy(active=True)])

    def _providers(self):
        context = aq_inner(self.context)
        providers = []
        for name in context.providers:
            util = queryUtility(IGazetteTextProvider, name=name)
            if util is not None:
                providers.append(util)
        return providers

    def send_gazette(self):
        context = aq_inner(self.context)
        parent = aq_parent(context)
        now = datetime.now()
        CheckAuthenticator(self.request)
        ptool = getToolByName(self.context, 'plone_utils')
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        providers = self._providers()
        subject = context.Title()
        import pdb; pdb.set_trace()
        url = parent.absolute_url() + '/subscription?uuid=%(uuid)s'
        footer_text = parent.footer.output.replace('${url}', '$url')
        footer_text = footer_text.replace('$url', url)
        count = 0
        text = context.text.output + '\n'
        for p in providers:
            text += p.get_gazette_text(parent, context)
        for s in soup.query(active=True):
            # returns email and fullname taken from memberdata if s.username is set and member exists
            subscriber_info = s.get_info(context)
            footer = footer_text % subscriber_info
            mail_text = "%s<p>------------<br />%s</p>" % (text, footer)
            try:
                if utils.send_mail(context, None, subscriber_info['email'], subscriber_info['fullname'], subject, mail_text):
                    count += 1
            except (SMTPException, SMTPRecipientsRefused):
                pass
        context.sent_at = now
        parent.most_recent_issue = context
        ptool.addPortalMessage(_(u'Gazette has been sent to $count recipients', mapping={'count': count}))
        self.request.response.redirect(context.absolute_url())

    def test_send(self):
        context = aq_inner(self.context)
        parent = aq_parent(context)
        email = parent.test_mail
        ptool = getToolByName(self.context, 'plone_utils')
        if not email:
            ptool.addPortalMessage(_(u'No test email set. Please check Gazette folder settings.'), 'error')
        else:
            text = context.text.output + '\n'
            providers = self._providers()
            for p in providers:
                text += p.get_gazette_text(parent, context)
            subject = context.Title()
            url = parent.absolute_url() + '/subscription?uuid=' # NOT SET - just testing
            footer_text = parent.footer.output.replace('${url}', '$url')
            footer_text = footer_text.replace('$url', url)
            footer = footer_text
            mail_text = "%s<p>------------<br />%s</p>" % (text, footer)
            try:
                utils.send_mail(context, None, email, 'Tester', subject, mail_text)
            except (SMTPException, SMTPRecipientsRefused):
                pass
            ptool.addPortalMessage(_(u'Gazette test has been sent to $email', mapping={'email': email}))
        self.request.response.redirect(context.absolute_url())
