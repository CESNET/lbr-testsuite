import setuptools

long_description = "Package includes following modules:\n" \
    "- common | module with useful functions for testing in python\n" \
    "- ipconfigurer | API for ip configuration using pyroute2 library\n" \
    "- spirent, spirentlib | API for Spirent Test Center (STC)\n" \
    "- TRex tools | tools to simplify basic TRex operations"

setuptools.setup(
    name="lbr_testsuite",
    version_config={
        "template": "{tag}",
        "dev_template": "{tag}.post{ccount}+git.{sha}",
        "dirty_template": "{tag}.post{ccount}+git.{sha}.dirty",
        "starting_version": "1.0.0",
    },
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
        "Framework :: Pytest"
    ],
    install_requires=[
        'pyroute2>=0.6.2,<1.',
        'lbr_trex_client',
        'stcrestclient',
        'pytest'
    ],
    python_requires='>=3.6',
    entry_points={
        "pytest11": [
            "lbr_testsuite = lbr_testsuite.pytest.plugin",
            "lbr_keyboard_interrupt = lbr_testsuite.pytest.keyboard_interrupt.plugin",
        ],
    },
)
