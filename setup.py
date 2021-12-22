#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# PIVageant : setup data
# Copyright (C) 2021  BitLogiK


from setuptools import setup, find_packages
from _version import __version__


with open("README.md") as readme_file:
    readme = readme_file.read()


setup(
    name="PIVageant",
    version=__version__,
    description="Pageant SSH agent with PIV dongle",
    long_description=readme + "\n\n",
    long_description_content_type="text/markdown",
    keywords="SSH agent Pageant PIV Windows",
    author="BitLogiK",
    author_email="contact@bitlogik.fr",
    url="https://github.com/bitlogik/PIVageant",
    license="GPLv3",
    python_requires=">=3.6",
    install_requires=[
        "wxPython==4.1.1",
        "cryptography>=3.4.6",
        "pyscard==2.0.1",
    ],
    package_data={"res": ["pivageant.ico"]},
    include_package_data=False,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Office/Business :: Financial",
        "Topic :: Security :: Cryptography",
        "Topic :: System :: Hardware :: Universal Serial Bus (USB) :: Smart Card",
    ],
    packages=find_packages(),
    zip_safe=False,
)
