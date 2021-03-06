import os
from os import path
import setuptools

README = open(path.join(path.dirname(__file__), 'README.md')).read()

# allow setup.py to be run from any path
os.chdir(path.normpath(path.join(path.abspath(__file__), os.pardir)))

setuptools.setup(
    name='django-knockout',
    version='0.4.0',  # major.minor[.patch][sub]
    packages=['knockout'],
    install_requires=['django'],
    include_package_data=True,
    license='MIT License',
    description='Generate knockout.js View Models from Django Models.',
    long_description=README,
    url='https://github.com/AntycSolutions/django-knockout',
    author='Rich Jones, Andrew Charles',
    author_email='andrew.charles@antyc.ca',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.4',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
