from collective.gazette.interfaces import IGazetteTextProvider
from zope.component import getUtilitiesFor

from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm


def providersVocabularyFactory(context):
    providers = getUtilitiesFor(IGazetteTextProvider)
    items = [SimpleTerm(name, name, repr(provider)) for name, provider in providers]
    return SimpleVocabulary(items)
