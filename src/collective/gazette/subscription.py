# -*- coding: utf8 -*-
from five import grok
from plone import api
import hashlib
import random
from zope.interface import implements
from zope.component import adapts
from zope.publisher.interfaces.http import IHTTPRequest
from cornerstone.soup import getSoup
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.stringinterp.interfaces import IStringInterpolator
from collective.gazette.subscribers import Subscriber
from collective.gazette.gazettefolder import IGazetteFolder
from collective.gazette.interfaces import IGazetteSubscription
from collective.gazette import utils
from collective.gazette import config
from collective.gazette import gazetteMessageFactory as _


def GenerateSecret(length=64):
    secret = ""
    for i in range(length):
        secret += chr(random.getrandbits(8))

    return hashlib.sha1(secret).hexdigest()


class SubscriptionAdapter(object):
    adapts(IGazetteFolder, IHTTPRequest)
    implements(IGazetteSubscription)

    activation_template = ViewPageTemplateFile('browser/activation.pt')
    deactivation_template = ViewPageTemplateFile('browser/deactivation.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def activation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.activation_template(key=subscriber.key))
        subject = _(u"Please activate your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def deactivation_mail(self, subscriber):
        mail_text = IStringInterpolator(self.context)(self.deactivation_template(key=subscriber.key))
        subject = _(u"Please confirm deactivation of your subscription")
        utils.send_mail(self.context, None, subscriber.email, subscriber.fullname, subject, mail_text)

    def status(self, email):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(email=email)]
        if results:
            return results[0].active
        return False

    def subscribe(self, email, fullname, username=u'', send_activation_mail=True, wait_for_confirmation=True, **kwargs):
        # find if there is existing subscription
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        email = email.strip()
        if username:
            # ignore everything
            user = api.user.get(username='admin')
            if user:
                email = user.getProperty('email', '')
                if email:
                    # subscribe as portal user
                    # is username is set, subscription is considered as subscription of portal member
                    # override fullname, if any
                    fullname = user.getProperty('fullname', fullname)

        if not email:
            return config.INVALID_DATA
        results = [r for r in soup.query(email=email)]
        _marker = object()
        if results:
            s = results[0]
            s.email = email
            s.fullname = fullname
            if s.active:
                send_activation_mail = False
                if wait_for_confirmation:
                    s.key = GenerateSecret()
                    result = config.WAITING_FOR_CONFIRMATION
                else:
                    result = config.ALREADY_SUBSCRIBED
            else:
                s.active = True
                result = config.SUBSCRIPTION_SUCCESSFULL
            for k, v in kwargs.items():
                has_attr = getattr(s, k, _marker)
                if has_attr is not _marker:
                    setattr(s, k, v)
            soup.reindex([s])
            if send_activation_mail:
                # Do not send if user is editor and has different email address
                self.activation_mail(s)
            return result
        else:
            # new subscriber
            s = Subscriber(email=email, fullname=fullname, active=False, username=username)
            if wait_for_confirmation:
                s.key = GenerateSecret()
                result = config.WAITING_FOR_CONFIRMATION
            else:
                s.active = True
                result = config.SUBSCRIPTION_SUCCESSFULL
            for k, v in kwargs.items():
                has_attr = getattr(s, k, _marker)
                if has_attr is not _marker:
                    setattr(s, k, v)
            soup.add(s)
            if send_activation_mail:
                self.activation_mail(s)
            return result

    def unsubscribe(self, email, send_deactivation_mail=True, wait_for_confirmation=True):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(email=email)]
        if results:
            if not results[0].active:
                return config.ALREADY_UNSUBSCRIBED
            else:
                s = results[0]
                if wait_for_confirmation:
                    s.key = GenerateSecret()
                    result = config.WAITING_FOR_CONFIRMATION
                else:
                    s.active = False
                    result = config.UNSUBSCRIBED
                soup.reindex([s])
                if send_deactivation_mail:
                    self.deactivation_mail(s)
                return result
        else:
            return config.NO_SUCH_SUBSCRIPTION

    def update(self, uuid, **kwargs):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        results = [r for r in soup.query(uuid=uuid)]
        _marker = object()
        if results:
            s = results[0]
            for k, v in kwargs.items():
                if k == 'uuid':
                    continue
                has_attr = getattr(s, k, _marker)
                if has_attr is not _marker:
                    setattr(s, k, v)
        else:
            return config.NO_SUCH_SUBSCRIPTION

grok.global_adapter(SubscriptionAdapter)
