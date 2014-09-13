# -*- coding: utf-8 -*-
from plone import api
import uuid
from datetime import datetime
from zope.interface import implements
from zope.catalog.catalog import Catalog
from zope.catalog.field import FieldIndex
from zope.catalog.text import TextIndex
from cornerstone.soup.interfaces import ICatalogFactory
from cornerstone.soup import Record


class Subscriber(Record):

    email = u''
    fullname = u''
    active = True
    timestamp = None
    key = u''
    username = u''
    salutation = u''
    providers = None
    uuid = u''

    def __init__(self, email, fullname=u'', active=True, username=u'', salutation=u'', providers=None):
        assert email
        self.email = email
        if fullname is None:
            fullname = u''
        self.fullname = fullname
        self.active = active
        self.timestamp = datetime.now()
        self.key = u''
        self.username = username
        self.salutation = salutation
        if providers is None:
            self.providers = []
        else:
            self.providers = providers
        self.uuid = str(uuid.uuid3(uuid.NAMESPACE_URL, email.encode('utf-8')))

    def SearchableText(self):
        return self.email + ' ' + self.fullname + ' ' + self.username

    def get_info(self, context):
        result = dict(
            email=self.email,
            fullname=self.fullname,
            salutation=self.salutation,
            uuid=self.uuid
        )
        if self.username:
            user = api.user.get(username=self.username)
            if user is not None:
                result['email'] = user.getProperty('email')
                result['fullname'] = user.getProperty('fullname')
        return result


class SubscribersCatalog(object):

    implements(ICatalogFactory)

    def __call__(self):
        catalog = Catalog()
        catalog[u'SearchableText'] = TextIndex(field_name='SearchableText',
                                               field_callable=True)
        catalog[u'email'] = FieldIndex(field_name='email',
                                       field_callable=False)
        catalog[u'username'] = FieldIndex(field_name='username',
                                          field_callable=False)
        # activation key
        catalog[u'key'] = FieldIndex(field_name='key',
                                       field_callable=False)
        catalog[u'active'] = FieldIndex(field_name='active',
                                       field_callable=False)
        catalog[u'uuid'] = FieldIndex(field_name='uuid',
                                      field_callable=False)
        return catalog
