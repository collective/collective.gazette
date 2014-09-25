# -*- coding: utf8 -*-
import os
import tempfile
import subprocess
import shutil
from Products.CMFPlone.utils import safe_unicode
from Products.CMFCore.utils import getToolByName
from datetime import datetime
from Acquisition import aq_inner
from smtplib import SMTPException
from smtplib import SMTPRecipientsRefused
from plone.app.textfield.value import RichTextValue

from zope.component import queryUtility
from zope.component import getMultiAdapter
from cornerstone.soup import getSoup
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteTextProvider
from collective.gazette import utils
from collective.gazette import config
from five import grok
import logging
logger = logging.getLogger('gazette')


class AutomatedTestView(grok.View):
    grok.name('auto-issue-test')
    grok.require('collective.gazette.IssueAutomatedNewsletter')
    grok.context(IGazetteFolder)

    def render(self):
        view = getMultiAdapter((self.context, self.request), name='auto-issue')
        return view.render(test_mode=True)


class AutomatedView(grok.View):
    grok.name('auto-issue')
    grok.require('collective.gazette.IssueAutomatedNewsletter')
    grok.context(IGazetteFolder)

    def _providers(self):
        context = aq_inner(self.context)
        providers = []
        for name in context.auto_providers:
            util = queryUtility(IGazetteTextProvider, name=name)
            if util is not None:
                providers.append(util)
        return providers

    def make_pdf(self, htmlbody, html_only=False):
        """ htmlbody is everything inside html <body> element (without body element itself) """
        # wrap htmlbody with provided HTML template
        template = self.context.auto_template
        template = template.replace(u'${body}', htmlbody)
        if html_only:
            return template
        try:
            tempdir = tempfile.mkdtemp()
            # attachemnts saved. Let's save generated HTML
            fullpath = os.path.join(tempdir, 'issue.html')
            fp = open(fullpath, 'w')
            fp.write(template.encode('utf-8'))
            fp.close()
            # Run wkhtmltopdf and generate the PDF
            targetpath = os.path.join(tempdir, 'issue.pdf')
            result = subprocess.call(["wkhtmltopdf", '-q', 'file://%s' % fullpath, '%s' % targetpath])
            if result == 0:
                return open(targetpath, 'rb').read()
            else:
                return ''
        finally:
            shutil.rmtree(tempdir, ignore_errors=True)

    def render(self, test_mode=False, html_only=False):
        """ This method does all the hard work """
        context = aq_inner(self.context)
        if not context.auto_enabled:
            return 'N/A'

        now = datetime.now()
        wtool = getToolByName(context, 'portal_workflow')
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        # strftime accepts any text, not only strftime characters
        subject = now.strftime(context.auto_subject.encode('utf-8'))
        url = context.absolute_url() + '/subscription?uuid=%(uuid)s'
        footer_text = context.footer.output.replace('${url}', '$url')
        footer_text = footer_text.replace('$url', url)
        count = 0
        base_text = ''
        if context.auto_text:
            base_text += now.strftime(context.auto_text.output.encode('utf-8')) + '\n'
        providers = self._providers()
        gid = 'issue-%s' % now.strftime("%Y-%m-%d-%H-%M-%S.%f")
        idx = 0
        while context.check_id(gid):  # python script in skins
            idx += 1
            gid = 'issue-%s-%d' % (now.strftime("%Y-%m-%d-%H-%M-%S.%f"), idx)
        # create anonymous issue text to be stored to portal
        text = safe_unicode(base_text)
        auto_text = u''
        provider_names = []

        for p in providers:
            auto_text += safe_unicode(p.get_gazette_text(context, None))
            provider_names.append(repr(p))

        if not auto_text:
            # There is no automatically geenrated text. Discard sending of newsletter.
            return 'Nothing to send'

        text = text + auto_text
        # Create PDF version of the newsletter using wkhtml2pdf as archive of the issue
        pdf_raw = self.make_pdf(text, html_only)
        if not pdf_raw:
            logger.warning('Unable to create PDF of automatically issued gazette.')
        if not test_mode:
            # create Gazette object representing this issue
            gid = context.invokeFactory('gazette.GazetteIssue', gid)
            gazette = context[gid]
            # Fill the newly create Gazette object with generated data
            gazette.title = subject
            gazette.text = RichTextValue(text, mimeType='text/html', outputMimeType='text/html')
            gazette.providers = provider_names
            gazette.sent_at = now
            try:
                # ignore if there is no publish option for now
                wtool.doActionFor(gazette, 'publish')
            except:
                pass
            # Attach PDF to gazette but only if it is not HTML only mode
            if pdf_raw and not html_only:
                fid = gazette.invokeFactory('File', gid + '.pdf')
                file_pdf = gazette[fid]
                file_pdf.setTitle(gazette.title)
                file_pdf.setFile(pdf_raw, mimetype='application/pdf')
                file_pdf.processForm()

            for s in soup.query(active=True):
                # returns email and fullname taken from memberdata if s.username is set and member exists
                subscriber_info = s.get_info(context)
                footer = footer_text % subscriber_info
                mail_text = ""
                if subscriber_info['salutation']:
                    mail_text += "%s<br /><br />" % subscriber_info['salutation']
                mail_text += "%s------------<br />%s" % (text, footer)
                try:
                    if utils.send_mail(context, None, subscriber_info['email'], subscriber_info['fullname'], subject, mail_text):
                        count += 1
                except (SMTPException, SMTPRecipientsRefused):
                    pass
            context.most_recent_issue = gazette
        else:
            if html_only:
                self.request.response.setHeader('Content-Type', 'text/html;charset=utf-8')
            else:
                self.request.response.setHeader('Content-Type', 'application/pdf')
            return pdf_raw

        return str(count)
