"""Definition of the GazetteFolder content type
"""

from zope.interface import implements

from Products.Archetypes import atapi
from Products.ATContentTypes.content import folder
from Products.ATContentTypes.content import schemata
from cornerstone.soup.interfaces import ISoupAnnotatable

from collective.gazette import gazetteMessageFactory as _
from collective.gazette.interfaces import IGazetteFolder
from collective.gazette.config import PROJECTNAME

GazetteFolderSchema = folder.ATFolderSchema.copy() + atapi.Schema((

    atapi.StringField('test_mail',
              required=False,
              searchable=False,
              validators = ('isEmail',),
              storage = atapi.AnnotationStorage(),
              widget=atapi.StringWidget(
                        label=_(u'Test email'),
                        description=_(u'Testing email address'),
                        size=40,
              ),
    ),
    atapi.TextField(
        name='footer',
        required=False,
        default="Unsubscribe at $url",
        storage = atapi.AnnotationStorage(migrate=True),
        validators = ('isTidyHtmlWithCleanup',),
        default_output_type = 'text/x-html-safe',
        widget=atapi.RichWidget(
                    label=_('Gazette footer text'),
                    description=_('Please enter text appended to each email '
                                  'sent to users. It should contain $url '
                                  'placeholder which will be replaced with '
                                  'unsubscription url link')
                    ),
                    rows = 15,
                    allow_file_upload = False,
        ),

))

GazetteFolderSchema['title'].storage = atapi.AnnotationStorage()
GazetteFolderSchema['description'].storage = atapi.AnnotationStorage()

schemata.finalizeATCTSchema(
    GazetteFolderSchema,
    folderish=True,
    moveDiscussion=False
)


class GazetteFolder(folder.ATFolder):
    """Folder for newsletters"""
    implements(IGazetteFolder, ISoupAnnotatable)

    meta_type = "GazetteFolder"
    schema = GazetteFolderSchema

    title = atapi.ATFieldProperty('title')
    description = atapi.ATFieldProperty('description')
    test_mail = atapi.ATFieldProperty('test_mail')

atapi.registerType(GazetteFolder, PROJECTNAME)
