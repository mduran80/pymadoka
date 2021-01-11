from setuptools import setup

setup(
    name='pymadoka',
    version='0.1',
    py_modules=['pymadoka'],
    author = "Manuel Durán",
    author_email = "manuelduran@gmail.com",
    description = ("A library to control Daikin BRC1H (Madoka) thermostats"),
    license = "MIT",
    keywords = "thermostat homeautomation bluetooth",
    install_requires=[
        'click',
        'bleak',
        'pyyaml'
    ],
    entry_points='''
        [console_scripts]
        pymadoka=pymadoka.cli:cli
    ''',
)