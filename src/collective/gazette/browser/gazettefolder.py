from Acquisition import aq_inner
from Products.CMFPlone.i18nl10n import ulocalized_time
from Products.Five import BrowserView
from Products.CMFCore.utils import getToolByName

class GazetteFolderView(BrowserView):
    
    def gazettes(self):
        context = aq_inner(self.context)
        path = '/'.join(context.getPhysicalPath())
        result = []
        ctool = getToolByName(context, 'portal_catalog')
        for brain in ctool(portal_type='Gazette', 
                           path=path, 
                           sort_on='start', 
                           sort_order='reverse'):
            result.append(dict(
                title = brain.Title,
                url = brain.getURL(),
                date = ulocalized_time(brain.start, 0, context=context)
            ))
        return result
            