from five import grok
from zope.schema.interfaces import IContextSourceBinder
from collective.gazette.interfaces import IGazetteTextProvider
from collective.gazette.gazettefolder import IGazetteFolder
from zope.component import getUtilitiesFor

from zope.schema.vocabulary import SimpleVocabulary
from zope.schema.vocabulary import SimpleTerm


def providersVocabularyFactory(context):
    providers = getUtilitiesFor(IGazetteTextProvider)
    items = [SimpleTerm(name, name, repr(provider)) for name, provider in providers]
    return SimpleVocabulary(items)


@grok.provider(IContextSourceBinder)
def optionalProvidersSource(context):
    # context is result of 'getContent' method of SubscriberForm
    folder = IGazetteFolder(context.get('context'), None)
    if folder is not None:
        all_providers = providersVocabularyFactory(context)
        providers = folder.auto_optional_providers
        items = []
        for item in providers:
            try:
                items.append(all_providers.getTerm(item))
            except LookupError:
                pass
        return SimpleVocabulary(items)
    else:
        return SimpleVocabulary([])
