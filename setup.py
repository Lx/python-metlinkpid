from pathlib import Path
from sys import argv

import setuptools

README = Path(__file__).parent / 'README.rst'
needs_pytest = {'pytest', 'test', 'ptr'}.intersection(argv)

setuptools.setup(
    name='metlinkpid',
    version='1.0.2',
    description='Metlink LED passenger information display driver',
    long_description=README.read_text(),
    url='https://github.com/Lx/python-metlinkpid',
    author='Alex Peters',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Typing :: Typed',
    ],
    py_modules=['metlinkpid'],
    python_requires='~=3.6',
    setup_requires=['pytest-runner'] if needs_pytest else [],
    install_requires=[
        'attrs',
        'dlestxetx',
        'crccheck',
        'pyserial',
    ],
    tests_require=[
        'pytest',
    ],
    extras_require={
        'docs': [
            'sphinx~=2.1.1',
            'sphinx-rtd-theme~=0.4.3',
        ]
    },
)
