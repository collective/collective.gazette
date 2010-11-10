import email
import logging
from smtplib import SMTPRecipientsRefused
from smtplib import SMTPException

from zope.component import getUtility
from Products.CMFCore.interfaces import IPropertiesTool

logger = logging.getLogger('collective.gazette.utils')

def _from_address(name, mail):
    properties = getUtility(IPropertiesTool)
    charset = properties.site_properties.getProperty('default_charset', 'utf-8')

    if not isinstance(name, unicode):
        name = name.decode(charset)
    if not isinstance(mail, unicode):
        # mail has to be be ASCII!!
        mail = mail.decode(charset).encode('us-ascii', 'replace')

    return email.Utils.formataddr((str(email.Header.Header(name, charset)), mail))


def send_mail(context, mfrom, mto, mto_fullname, subject, mail_text):
    email_charset = 'utf-8'

    if mfrom is None:
        mfrom = _from_address(context.email_from_name,
                              context.email_from_address)    

    if mto_fullname:
        mto = _from_address(mto_fullname, mto)    

    # If mail_text is not decoded here, no text is displayed in Thunderbird or Outlook
    if isinstance(mail_text, unicode):
        mail_text = mail_text.encode(email_charset)

    subMsg=email.Message.Message()
    subMsg.add_header("Content-Type", "text/html", charset=email_charset)
    # add header to correctly set payload
    subMsg.add_header("Content-Transfer-Encoding", "base64")
    subMsg.set_payload(mail_text, email_charset)
    # remove header, because encode_base64 sets it again and it would be twice there
    del subMsg["Content-Transfer-Encoding"]
    email.encoders.encode_base64(subMsg)

    mail_text = subMsg.as_string()

    mail_text = 'From: %s\nTo: %s\nSubject: %s\n%s' % (mfrom, mto, subject, mail_text)

    # If mail_text is not decoded here, host.send fails with "No message recipient"
    if isinstance(mail_text, unicode):
        mail_text = mail_text.encode(email_charset)
    
    host = context.MailHost
    try:
        host.send( mail_text )
        return True
    except SMTPRecipientsRefused:
        # Don't disclose email address on failure
        raise SMTPRecipientsRefused('Recipient address rejected by mail server')
    except Exception, e:
        logger.error("There was an error when sending email. Error message: %s" % str(e))
        raise SMTPException("There was an error when sending email. Error: %s" % str(e))
