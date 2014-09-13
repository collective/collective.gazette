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

    def get_gazette_text(gazette_folder, gazette):
        """ returns HTML code
        """


class IGazetteSubscription(Interface):
    """ simple adapter to IGazetteFolder which allows to subscribe and unsubscribe
        users
    """
    def subscribe(email, fullname, username=u'', send_activation_mail=True, wait_for_confirmation=True, **kwargs):
        """
            Subscribe anonymous or portal member.
            if @username is set, ignore email and fullname and subscribe user with his
            email/fullname read from member properties.
            If send_activation_mail is True, request for activation email is sent.
            If wait_for_confirmation is not set, user is immediatelly unsubscribed, even if
            activation email is sent.
            Optional kwargs are set as a Subscriber object attributes

            Returns integer code according to config.py constants.
        """

    def unsubscribe(email, send_deactivation_mail=True, wait_for_confirmation=True):
        """
            Unsubscribe user by email.
            If send_deactivation_mail is True, request for deactivation email is sent.
            If wait_for_confirmation is not set, user is immediatelly unsubscribed, even if
            deactivation email is sent.

            Returns integer code according to config.py constants.
        """

    def status(email):
        """ Returns True if the subscription is active """
