# -*- coding: utf-8 -*-

""" Subscibers are stored in cornerstone.soup storage """

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
    
    def __init__(self, email, fullname=u'', active=True):
        self.email = email
        if fullname is None:
            fullname = u''
        self.fullname = fullname
        self.active = active
        self.timestamp = datetime.now()
        self.key = u''
        
    def SearchableText(self):
        return self.email + ' ' + self.fullname

class SubscribersCatalog(object):

    implements(ICatalogFactory)

    def __call__(self):
        catalog = Catalog()
        catalog[u'SearchableText'] = TextIndex(field_name='SearchableText',
                                               field_callable=True)
        catalog[u'email'] = FieldIndex(field_name='email',
                                       field_callable=False)
        # activation key
        catalog[u'key'] = FieldIndex(field_name='key',
                                       field_callable=False)
        catalog[u'active'] = FieldIndex(field_name='active',
                                       field_callable=False)
        return catalog

