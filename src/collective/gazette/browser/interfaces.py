from zope.interface import Interface


class ISubscribeView(Interface):

    def subscribe(email, fullname):
        """ subscribe user """

    def unsubscribe(email):
        """ unsubscribe user """


class ISubscribersView(Interface):
    """ """

    def count():
        """ Returns count of active and inactive subscribers as a dictionary """

    def search(query):
        """ Search subscribers by given query. Recommended search params are
            SearchableText and active """
