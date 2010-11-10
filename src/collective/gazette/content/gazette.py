"""Definition of the Gazette content type
"""

from zope.interface import implements
from DateTime import DateTime

from Products.Archetypes import atapi
from Products.ATContentTypes.content import document
from Products.ATContentTypes.content import schemata
from Products.ATContentTypes.configuration import zconf

from collective.gazette import gazetteMessageFactory as _
from collective.gazette.interfaces import IGazette
from collective.gazette.config import PROJECTNAME

GazetteSchema = schemata.ATContentTypeSchema.copy() + atapi.Schema(
    (
        atapi.TextField('text',
                  required=True,
                  searchable=True,
                  primary=True,
                  storage = atapi.AnnotationStorage(migrate=True),
                  validators = ('isTidyHtmlWithCleanup',),
                  #validators = ('isTidyHtml',),
                  default_output_type = 'text/x-html-safe',
                  widget = atapi.RichWidget(
                            description = '',
                            label = _(u'label_body_text', default=u'Body Text'),
                            rows = 25,
                            allow_file_upload = zconf.ATDocument.allow_document_upload),
        ),
        atapi.DateTimeField('sent_at',
                            required=False,
                            default=None,
                            mode = "r",
                            storage = atapi.AnnotationStorage(),
                            widget=atapi.CalendarWidget(
                                label=_(u'Sent at'),
                                description=_(u'Date, when newsletter was sent'),
                            ),
        ),
    ),
    marshall=atapi.RFC822Marshaller(),
)

# Set storage on fields copied from ATContentTypeSchema, making sure
# they work well with the python bridge properties.

GazetteSchema['title'].storage = atapi.AnnotationStorage()
GazetteSchema['title'].widget.label=_(u'Subject')
GazetteSchema['title'].widget.description=_(u'Gazette subject (email subject)')
GazetteSchema['description'].storage = atapi.AnnotationStorage()
GazetteSchema['description'].widget.visible={'view': 'invisible', 'edit':'invisible'}

schemata.finalizeATCTSchema(GazetteSchema, moveDiscussion=False)


class Gazette(document.ATDocumentBase):
    """Issue of the newsletter"""
    implements(IGazette)

    meta_type = "Gazette"
    schema = GazetteSchema

    title = atapi.ATFieldProperty('title')
    description = atapi.ATFieldProperty('description')
    sent_at = atapi.ATFieldProperty('sent_at')

    def start(self):
        """ Re-use start index/metadata for sent_at """
        return self.sent_at or DateTime()

atapi.registerType(Gazette, PROJECTNAME)
