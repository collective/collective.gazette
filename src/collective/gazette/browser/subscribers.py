from Products.CMFCore.utils import getToolByName
from cornerstone.soup import getSoup
from Products.Five import BrowserView
from zope.interface import implements
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from collective.gazette.browser.interfaces import ISubscribersView
from collective.gazette import gazetteMessageFactory as _
import xlrd
from collective.gazette import config
from collective.gazette.subscribers import Subscriber

class SubscribersView(BrowserView):
    implements(ISubscribersView)
    
    template = ViewPageTemplateFile('subscribers.pt')
    
    def count(self):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        result = dict()
        result['active'] = len([x for x in soup.lazy(active=True)])
        result['inactive'] = len([x for x in soup.lazy(active=False)])
        return result
        
    def search(self, **query):
        soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
        result = []
        ACTIVE = _(u'label_yes', default=u'Yes')
        INACTIVE = _(u'label_no', default=u'No')
        if query:
            rows = soup.query(**query)
        else:
            # all records
            rows = soup.data.values()
        for row in rows:
            result.append(dict(
                fullname = row.fullname,
                email = row.email,
                active = row.active and ACTIVE or INACTIVE,
            ))
        return result
        
    def __call__(self):
        result = []
        if self.request.get('form.submitted') == '1':
            query = {}
            fulltext = self.request.get('fulltext', '')
            if fulltext:
                query['SearchableText'] = fulltext
            active = self.request.get('active', '')
            if active == '1':
                query['active'] = True
            elif active == '0':
                query['active'] = False
            result = self.search(**query)
        if self.request.get('form.import.submitted') == '1':
            fp = self.request.get('subscribers')
            putil = getToolByName(self.context, 'plone_utils')
            book = xlrd.open_workbook(filename=fp.filename, file_contents=fp.read())
            sh = book.sheet_by_index(0)
            valid = 0
            invalid = 0
            duplicates = 0
            if sh.nrows > 0:
                email = sh.row(0)[0].value
                if putil.validateSingleEmailAddress(email): 
                    start = 0
                else:
                    start = 1
                soup = getSoup(self.context, config.SUBSCRIBERS_SOUP_ID)
                for rx in range(start, sh.nrows):
                    # [text:u'test2@test.com', text:u'Test 2', empty:'', empty:'', empty:'']
                    row = sh.row(rx)
                    email = row[0].value.strip()
                    fullname = row[1].value.strip()
                    if putil.validateSingleEmailAddress(email): 
                        if not [r for r in soup.lazy(email = email)]:
                            # subscribe
                            s = Subscriber(email = email, fullname = fullname, active = True)
                            soup.add(s)
                            valid += 1
                        else:
                            duplicates += 1
                    else:
                        invalid += 1
                putil.addPortalMessage(_("Imported subscribers: ${imported}, Invalid: ${invalid}, Duplicates: ${duplicates}", mapping={'imported': valid, 'duplicates': duplicates, 'invalid': invalid}))
            else:
                putil.addPortalMessage(_("XLS file is empty"))
            
        return self.template(searchresults = result)
