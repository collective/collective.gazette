# -*- coding: utf8 -*-
import os
import tempfile
import subprocess
import shutil
from Products.CMFCore.utils import getToolByName
from datetime import datetime
from Acquisition import aq_inner
from smtplib import SMTPException
from smtplib import SMTPRecipientsRefused

from zope.component import queryUtility
from cornerstone.soup import getSoup
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteTextProvider
from collective.gazette import utils
from collective.gazette import config
from five import grok


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

    def make_pdf(self, htmlbody):
        """ htmlbody is everything inside html <body> element (without body element itself) """
        # wrap htmlbody with provided HTML template
        template = self.context.auto_template
        template = template.replace('${body}', htmlbody)
        try:
            tempdir = tempfile.mkdtemp()
            # attachemnts saved. Let's save generated HTML
            fullpath = os.path.join(tempdir, 'issue.html')
            fp = open(fullpath, 'w')
            fp.write(htmlbody)
            fp.close()
            # Run wkhtmltopdf and generate the PDF
            targetpath = os.path.join(tempdir, 'issue.pdf')
            result = subprocess.call(["wkhtmltopdf", 'file://%s' % fullpath, '%s' % targetpath])
            if result == 0:
                return open(targetpath, 'rb').read()
            else:
                return ''
        finally:
            # for debugging - logger.info('Temporary directory not removed: %s', tempdir)
            shutil.rmtree(tempdir, ignore_errors=True)

    def render(self):
        """ This method does all the hard work """
        context = aq_inner(self.context)
        if not context.auto_enabled:
            return 'N/A'

        now = datetime.now()
        wtool = getToolByName(context, 'portal_workflow')
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        subject = context.Title()
        url = context.absolute_url() + '/subscription?form.widgets.email=%s'
        footer_text = context.footer.output.replace('${url}', '$url')
        footer_text = footer_text.replace('$url', url)
        count = 0
        base_text = context.auto_text.output + '\n'
        providers = self._providers()
        gid = 'issue-%s' % now.strftime("%Y-%m-%d-%H-%M-%S.%f")
        idx = 0
        while context.check_id(gid):  # python script in skins
            idx += 1
            gid = 'issue-%s-%d' % (now.strftime("%Y-%m-%d-%H-%M-%S.%f"), idx)
        # create anonymous issue text to be stored to portal
        text = base_text
        for p in providers:
            text += p.get_gazette_text(context, None, '')

        # Create PDF version of the newsletter using wkhtml2pdf as archive of the issue
        pdf_raw = self.make_pdf(text)
        if not pdf_raw:
            return 'Unable to create PDF'
        # create Gazette object representing this issue
        gid = context.invokeFactory('gazette.Gazette', gid)
        gazette = context[gid]
        # Fill the newly create Gazette object with generated data
        gazette.title = ''  # FIXME
        gazette.text = text
        gazette.providers = ()
        gazette.sent_at = now
        try:
            # ignore if there is no publish option for now
            wtool.doActionFor(gazette, 'publish')
        except:
            pass
        # Attach it to gazette
        fid = gazette.invokeFactory('File', gid + '.pdf')
        file_pdf = gazette[fid]
        file_pdf.setTitle(gazette.title)
        file_pdf.setFile(pdf_raw, mimetype='application/pdf')
        file_pdf.processForm()

        for s in soup.query(active=True):
            text = base_text
            for p in providers:
                text += p.get_gazette_text(context, None, s.username)
            footer = footer_text % s.email
            mail_text = "%s<p>------------<br />%s</p>" % (text, footer)
            # returns email and fullname taken from memberdata if s.username is set and member exists
            subscriber_info = s.get_info(context)
            try:
                if utils.send_mail(context, None, subscriber_info['email'], subscriber_info['fullname'], subject, mail_text):
                    count += 1
            except (SMTPException, SMTPRecipientsRefused):
                pass
        return str(count)