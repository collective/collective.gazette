from gazettefolder import IGazetteFolder
from gazette import IGazette
from plone.theme.interfaces import IDefaultPloneLayer

class IGazetteLayer(IDefaultPloneLayer):
    """ A layer specific to this product. 
        Is registered using browserlayer.xml
    """