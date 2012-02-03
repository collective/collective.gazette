# -*- coding: utf-8 -*-
"""
This module contains the tool of collective.gazette
"""
import os
from setuptools import setup, find_packages

version = '0.1'

setup(name='collective.gazette',
      version=version,
      description="Yet another newsletter product for Plone",
      long_description=open("README.txt").read() + "\n" +
                       open(os.path.join("docs", "HISTORY.txt")).read(),
      # Get more strings from
      # http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        'Framework :: Plone',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
      keywords='newsletter gazette plone',
      author='Radim Novotny',
      author_email='novotny.radim@gmail.com',
      url='http://pypi.python.org/pypi/collective.gazette',
      license='GPL',
      packages=find_packages('src', exclude=['ez_setup']),
      package_dir={'': 'src'},
      namespace_packages=['collective', ],
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
                        "Plone >=4.0",
                        "Zope2 >=2.12",
                        'Products.CMFCore',
                        'plone.app.dexterity',
                        "zope.i18nmessageid",
                        "zope.interface",
                        "cornerstone.soup",
                        'Acquisition',
                        'zope.interface',
                        'zope.component',
                        # 'zope.catalog',  # z3c.autoinclude includes zcml and it causes
                        #                  # ConfigurationError: ('Invalid directive', u'factory')
                        'zope.i18nmessageid',
                        'plone.app.z3cform',
                        'plone.stringinterp',
                        'xlrd',
                        ],
      extras_require={
        'test': ['plone.app.testing'],
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
