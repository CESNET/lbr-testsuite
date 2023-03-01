import setuptools


long_description = (
    "Package includes following modules:\n"
    "- common | module with useful functions for testing in python\n"
    "- ipconfigurer | API for ip configuration using pyroute2 library\n"
    "- spirent, spirentlib | API for Spirent Test Center (STC)\n"
    "- TRex tools | tools to simplify basic TRex operations\n"
    "- topology | module with implementation of our pytest topologies."
)

setuptools.setup(
    name="lbr_testsuite",
    setuptools_git_versioning={
        "enabled": True,
        "template": "{tag}",
        "dev_template": "{tag}.dev{ccount}+git.{sha}",
        "dirty_template": "{tag}.dev{ccount}+git.{sha}.dirty",
        "starting_version": "1.0.0",
    },
    setup_requires=["setuptools-git-versioning==1.8.1"],
    author="CESNET",
    author_email="tran@cesnet.cz",
    description="Lbr_testsuite package contains various modules used by CESNET projects",
    long_description=long_description,
    long_description_content_type="text/plain",
    url="https://gitlab.liberouter.org/tmc/testsuite/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Framework :: Pytest",
    ],
    install_requires=[
        "pyroute2>=0.6.2,<1",
        "lbr_trex_client>=2.0.1",
        "stcrestclient",
        "pytest",
    ],
    python_requires=">=3.8",
    entry_points={
        "pytest11": [
            "lbr_testsuite = lbr_testsuite._pytest_plugins.plugin",
            "lbr_keyboard_interrupt = lbr_testsuite._pytest_plugins.keyboard_interrupt.plugin",
            "lbr_renamer = lbr_testsuite._pytest_plugins.renamer.plugin",
            "lbr_topology = lbr_testsuite._pytest_plugins.topology.plugin",
        ],
    },
)
