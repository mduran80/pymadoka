from setuptools import setup, find_packages

setup(
    name='pymadoka',
    version='0.2.6',
    py_modules=['pymadoka'],
    author = "Manuel Durán",
    author_email = "manuelduran@gmail.com",
    description = ("A library to control Daikin BRC1H (Madoka) thermostats"),
    license = "MIT",
    url = "https://github.com/mduran80/pymadoka",
    keywords = "thermostat homeautomation bluetooth",
    packages=find_packages()+ find_packages(where="./features"),
    install_requires=[
        'click',
        'bleak',
        'pyyaml',
        'asyncio-mqtt'
    ],
    entry_points='''
        [console_scripts]
        pymadoka=pymadoka.cli:cli
        pymadoka-mqtt=pymadoka.mqtt:run
    ''',
)