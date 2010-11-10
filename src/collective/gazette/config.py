"""Common configuration constants
"""

PROJECTNAME = 'collective.gazette'

# see configure.zcml as well - there is soup id hardcoded.
SUBSCRIBERS_SOUP_ID = 'collective.gazette.subscribers'

KEYRING_ID = u'gazette.subscribers'
KEYRING_SIZE = 200

ADD_PERMISSIONS = {
    # -*- extra stuff goes here -*-
    'GazetteFolder': 'collective.gazette: Add GazetteFolder',
    'Gazette': 'collective.gazette: Add Gazette',
}

