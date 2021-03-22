import setuptools

long_description = "Package includes following modules:\n" \
    "- ipconfigurer | API for ip configuration using pyroute2 library\n" \
    "- spirent, spirentlib | API for Spirent Test Center (STC)\n" \
    "- TRex tools | tools to simplify basic TRex operations"

setuptools.setup(
    name="lbr_testsuite",
    version_config=True,
    setup_requires=['setuptools-git-versioning'],
    author="CESNET",
    author_email="tran@cesnet.cz",
    description="Lbr_testsuite package contains various modules used by CESNET projects",
    long_description=long_description,
    long_description_content_type="text/plain",
    url="https://gitlab.liberouter.org/tmc/testsuite/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=[
        'pyroute2>=0.5.14',
        'lbr_trex_client',
        'stcrestclient',
    ],
    python_requires='>=3.6',
)
