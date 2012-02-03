from Acquisition import aq_base
from Products.MailHost.interfaces import IMailHost
from Products.CMFPlone.tests.utils import MockMailHost
from zope.component import getSiteManager
from plone.app.testing import PloneSandboxLayer
from plone.app.testing import applyProfile
from plone.app.testing import PLONE_FIXTURE
from plone.app.testing import IntegrationTesting, FunctionalTesting


class GazetteSuite(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        import collective.gazette
        self.loadZCML(package=collective.gazette)

    def setUpPloneSite(self, portal):
        # Install into Plone site using portal_setup
        applyProfile(portal, 'collective.gazette:default')

        # I put this code to test setUp but the mailhost was not mocked
        # If it is here in layer, it seems to be working fine.
        portal._original_MailHost = portal.MailHost
        portal.MailHost = mailhost = MockMailHost('MailHost')
        sm = getSiteManager(context=portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(mailhost, provided=IMailHost)

    def tearDownPloneSite(self, portal):
        portal.MailHost = portal._original_MailHost
        sm = getSiteManager(context=portal)
        sm.unregisterUtility(provided=IMailHost)
        sm.registerUtility(aq_base(portal._original_MailHost), provided=IMailHost)


GAZETTE_FIXTURE = GazetteSuite()
GAZETTE_INTEGRATION_TESTING = IntegrationTesting(
                                        bases=(GAZETTE_FIXTURE,),
                                        name="Gazette:Integration"
                                    )
GAZETTE_FUNCTIONAL_TESTING = FunctionalTesting(
                                        bases=(GAZETTE_FIXTURE,),
                                        name="Gazette:Functional"
                                    )