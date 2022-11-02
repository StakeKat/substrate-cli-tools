from setuptools import setup, find_packages
from subtools import __version__

__long_description__ = """
SubTools leverages [py-substrate-interface](https://github.com/polkascan/py-substrate-interface) library to provide a
set of useful CLI commands but also to provide a library that can be reused to build your own commands quickly through
a higher level abstraction than the one provided by the main interface
"""

setup(
    name='substrate-cli-tools',
    version=__version__,
    description='A set of high level tools to connect and consume substrate based chains',
    url='https://github.com/StakeKat/substrate-cli-tools',
    author='Frank Monza',
    author_email='frank.bmonza@gmail.com',
    license='MIT',
    long_description=__long_description__,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
