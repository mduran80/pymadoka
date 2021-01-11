from setuptools import setup

setup(
    name='pymadoka',
    version='0.1',
    py_modules=['pymadoka'],
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