from setuptools import setup

setup(
    name='trigev',
    version='0.1.0',
    py_modules=['trigev'],
    install_requires=[],
    entry_points='''
        [console_scripts]
        trigev=trigev:trigev
    ''',
)
