# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
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

    def __init__(self, email, fullname=u'', active=True, username=u''):
        self.email = email
        if fullname is None:
            fullname = u''
        self.fullname = fullname
        self.active = active
        self.timestamp = datetime.now()
        self.key = u''
        self.username = username

    def SearchableText(self):
        return self.email + ' ' + self.fullname + ' ' + self.username

    def get_info(self, context):
        result = dict(email=self.email, fullname=self.fullname)
        if self.username:
            acl = getToolByName(context, 'acl_users')
            user = acl.getUserByName(self.username)
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
        return catalog