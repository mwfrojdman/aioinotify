import re
import os
from setuptools import setup, find_packages


# read version from aioinotify.version
_version_py_path = os.path.join(os.path.dirname(__file__), 'aioinotify', 'version.py')
_version_pattern = re.compile(r'''^__version__ = '([^']*)'\s*(?:#.*)?$''')
with open(_version_py_path, 'r') as version_py_fob:
    for line in version_py_fob:
        match = _version_pattern.match(line)
        if match is None:
            continue
        aioinotify_version = match.group(1)
        break
    else:
        raise ValueError('Could not find any __version__ in {}'.format(_version_py_path))


setup(
    name = 'aioinotify',
    description = 'inotify library for Python3 asyncio',
    keywords = 'inotify asyncio fs',
    version = aioinotify_version,
    url = 'https://github.com/mwfrojdman/aioinotify',
    author = 'Mathias Fröjdman',
    author_email = 'mwf@iki.fi',
    license = 'Apache License 2.0',
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        # TODO: check if it works on python 3.3 and if it does, add extras_require 3.3 -> asyncio
        # and entry on this line
        'Programming Language :: Python :: 3.4',
        # TODO: check it works on Python 3.5 too
        'Operating System :: POSIX :: Linux'],
    packages = find_packages(),
    install_requires = [],
    tests_require = [])

