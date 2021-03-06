#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright 2017-2018 - Edoardo Morassutto <edoardo.morassutto@gmail.com>
# Copyright 2018 - Luca Versari <veluca93@gmail.com>

import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="terry",
    version="0.0.1",
    author="Edoardo Morassutto, Dario Ostuni, Luca Versari",
    author_email="edoardo.morassutto@gmail.com, dario.ostuni@gmail.com, veluca93@gmail.com",
    description="A simple to use backend for the regional phase of Olimpiadi Italiane di Informatica",
    license="MPL-2.0",
    keywords="informatics contests",
    url="https://github.com/algorithm-ninja/terry",
    packages=find_packages(exclude="test"),
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Natural Language :: English",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Scientific/Engineering",
    ],
    entry_points={
        "console_scripts": [
            "terr-server = terry.__main__:main",
            "terr-gen-password = terry.utility:gen_password_main",
            "terr-crypt-file = terry.utility:crypt_file_main",
            "terr-get-metadata = terry.utility:get_metadata_main",
        ]
    },
)
