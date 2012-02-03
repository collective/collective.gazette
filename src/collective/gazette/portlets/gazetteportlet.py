from zope.formlib import form
from zope.interface import implements
from zope import schema
from zope.component import getMultiAdapter

from plone.portlets.interfaces import IPortletDataProvider
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.memoize.compress import xhtml_compress
from plone.memoize.instance import memoize

from collective.gazette import gazetteMessageFactory as _
from collective.gazette.gazettefolder import IGazetteFolder

from plone.app.portlets.portlets import base
from plone.app.vocabularies.catalog import SearchableTextSourceBinder


class IGazettePortlet(IPortletDataProvider):
    gazette = schema.Choice(title=_(u"Gazette folder"),
                             description=_(u"Please select a gazette users will be subscribed to"),
                             required=True,
                             default=u'',
                             source=SearchableTextSourceBinder(
                                        query={'object_provides': IGazetteFolder.__identifier__},
                                        default_query=''),
                            )


class Assignment(base.Assignment):
    implements(IGazettePortlet)

    def __init__(self, gazette=u''):
        self.gazette = gazette

    @property
    def title(self):
        return _(u"Gazette")


class Renderer(base.Renderer):

    _template = ViewPageTemplateFile('gazetteportlet.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)

        portal_state = getMultiAdapter((self.context, self.request), name=u'plone_portal_state')
        # self.navigation_root_url = portal_state.navigation_root_url()
        self.portal = portal_state.portal()
        self.navigation_root_path = portal_state.navigation_root_path()

    @property
    def available(self):
        return not not self.gazette_content()

    def render(self):
        return xhtml_compress(self._template())

    @memoize
    def gazette_content(self):
        if not self.data.gazette:
            return None
        path = "%s%s" % (self.navigation_root_path, self.data.gazette)
        return self.portal.restrictedTraverse(path, None)


class AddForm(base.AddForm):
    form_fields = form.Fields(IGazettePortlet)
    label = _(u"Add Gazette portlet")
    description = _(u"This portlet displays gazette subscription box.")

    def create(self, data):
        return Assignment(gazette=data.get('gazette', ''))


class EditForm(base.EditForm):
    form_fields = form.Fields(IGazettePortlet)
    label = _(u"Edit Gazette Portlet")
    description = _(u"This portlet displays gazette subscription box.")
