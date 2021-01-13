import setuptools

long_description = "Package includes following modules:\n" \
    "- ipconfigurer | API for ip configuration using pyroute2 library"

setuptools.setup(
    name="lbr_testsuite",
    version="1.0",
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
    python_requires='>=3.6',
)
