from zope.interface import Interface
from plone.theme.interfaces import IDefaultPloneLayer


class IGazetteLayer(IDefaultPloneLayer):
    """ A layer specific to this product.
        Is registered using browserlayer.xml
    """


class IGazetteOrderProvider(Interface):
    """
        Allows to define order of gazette text providers.
        If some providers are not returned by this utility,
        they are discarded!
    """

    def providers():
        """ Return ordered list of provider utilities """


class IGazetteTextProvider(Interface):
    """ Provider of part of gazette text. You can register any number
        of providers you want as named utilities.

        <utility factory=".myprovider.MyGazetteProvider"
                 name="myprovider" />
        <utility factory=".myprovider.AnotherGazetteProvider"
                 name="anotherprovider" />

        Providers are rendered in order of registration or
        in order defined by IGazetteProviderOrder utility (if exists)

        Provider can access gazettefolder or gazette items. Gazette parameter
        may be None in case of automated newsletter. Gazette folder contains
        most_recent_issue relation to the latest issue of the gazette (usually
        this will be a week, month or so old gazette issue)
    """

    def __repr__(self):
        """ String representation of the provider (will be shown in the vocabulary """

    def get_gazette_text(gazette_folder, gazette, username=u''):
        """ returns HTML code with text for particular user
            @username is portal username or empty string
        """
