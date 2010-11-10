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

class GazetteView(BrowserView):

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

    # def _render_gazette_for(self, email, fullname):
    # 
    def send_gazette(self):
        context = aq_inner(self.context)
        parent = aq_parent(context)
        CheckAuthenticator(self.request)
        ptool = getToolByName(self.context, 'plone_utils')
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        text = context.getText()
        subject = context.Title()
        url = parent.absolute_url() + '/subscription?form.widgets.email=%s'
        footer_text = parent.getFooter().replace('${url}', '$url')            
        footer_text = footer_text.replace('$url', url)
        count = 0
        for s in soup.query(active=True):
            footer = footer_text % s.email
            mail_text = "%s<p>------------<br />%s</p>" % (text, footer)
            try:
                if utils.send_mail(context, None, s.email, s.fullname, subject, mail_text):
                    count += 1
            except (SMTPException, SMTPRecipientsRefused):
                pass
        ptool.addPortalMessage(_(u'Gazette sent to $count recipients', mapping={'count':count}))
        self.request.response.redirect(context.absolute_url())
        
    def test_send(self):
        context = aq_inner(self.context)
        parent = aq_parent(context)
        email = parent.test_mail
        ptool = getToolByName(self.context, 'plone_utils')
        if not email:
            ptool.addPortalMessage(_(u'No test email set. Please check Gazette folder settings.'), 'error')
        else:
            text = context.getText()
            subject = context.Title() 
            url = parent.absolute_url() + '/subscription?form.widgets.email=%s'
            footer_text = parent.getFooter().replace('${url}', '$url')            
            footer_text = footer_text.replace('$url', url)
            footer = footer_text % email
            mail_text = "%s<p>------------<br />%s</p>" % (text, footer)
            try:
                utils.send_mail(context, None, email, 'Tester', subject, mail_text)
            except (SMTPException, SMTPRecipientsRefused):
                pass
            ptool.addPortalMessage(_(u'Gazette test sent to $email', mapping={'email':email}))
        self.request.response.redirect(context.absolute_url())
