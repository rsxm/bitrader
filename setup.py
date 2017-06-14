"""A setuptools based setup module.
See:
https://packaging.python.org/en/latest/distributing.html
"""
from codecs import open
from os import chdir, pardir, path
# Always prefer setuptools over distutils
from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

# allow setup.py to be run from any path
chdir(path.normpath(path.join(path.abspath(__file__), pardir)))

setup(
    name='bitrader',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    # use_scm_version={
    #     'write_to': 'src/static/version.txt',
    # },
    version='0.9.1',

    description=(
        "Bitcoin Arbitrage tools"
    ),

    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/jr-minnaar/bitrader',

    # Author details
    author='JR Minnaar',
    author_email='jr.minnaar+pypi@gmail.com',

    # Choose your license
    license='MIT',

    # What does your project relate to?
    keywords='bitcoin trading arbitrage',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['docs', 'tests']),

    # Alternatively, if you want to distribute just a my_module.py, uncomment
    # this:
    #   py_modules=["my_module"],

    # If setuptools_scm is installed, this automatically adds everything in version control
    include_package_data=True,

    zip_safe=True,

    # setup_requires=['setuptools_scm'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'python-dotenv',
        'requests',
        'pandas',
        'pyTelegramBotAPI',
        'krakenex>=0.1.4',
        'notebook',
        'html5lib',
        'lxml',
        'BeautifulSoup4',
        # API tools
        'requests>=2',
        'requests-cache>=0.4.12',
        'requests-futures>=0.9.7',
    ],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': [
            'wheel>=0.29.0',
            'python-dotenv>=0.5.1',
        ],
        # 'test': [
        #     'coverage',
        # ],
    },

    # test_suite='nose.collector',
    # tests_require=['invoke'],

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    # package_data={
    #     'sample': ['package_data.dat'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'arbot=bitrader.main:main',
        ],
    },
)
