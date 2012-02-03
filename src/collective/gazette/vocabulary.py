from collective.gazette.interfaces import IGazetteTextProvider
from zope.component import getAllUtilitiesRegisteredFor

from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm


def providersVocabularyFactory(context):
    providers = getAllUtilitiesRegisteredFor(IGazetteTextProvider)
    items = [x.__name__ for x in providers]
    items = [SimpleTerm(i, i, i) for i in items]
    return SimpleVocabulary(items)
