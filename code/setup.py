import sys
import ez_setup

ez_setup.use_setuptools()

from kontrol import __version__
from setuptools import setup, find_packages

if sys.version_info < (2, 7):
    raise NotImplementedError("python 2.7 or higher required")

setup(
    name='kontrol',
    version=__version__,
    packages=find_packages(),
    install_requires=
    [
        'pykka>=1.2.0',
        'python-etcd>=0.4.3'
    ],
    package_data={
        'kontrol':
            [
                'log.cfg'
            ]
    }
)

setup(
    name='automaton',
    version=__version__,
    packages=find_packages(),
    entry_points=
        {
            'console_scripts':
                [
                    'automaton = automaton.main:go'
                ]
        },
    package_data={
        'automaton':
            [
                'log.cfg'
            ]
    }
)
