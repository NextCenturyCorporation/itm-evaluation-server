import sys
from setuptools import setup, find_packages

NAME = "swagger_server"
VERSION = "0.6.3"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = [
    "connexion>=2.0.2",
    "swagger-ui-bundle>=0.0.2",
    "python_dateutil>=2.6.0"
]

setup(
    name=NAME,
    version=VERSION,
    description="ITM TA3 API",
    author_email="",
    url="",
    keywords=["Swagger", "ITM TA3 API"],
    install_requires=REQUIRES,
    packages=find_packages(),
    package_data={'': ['swagger/swagger.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['swagger_server=swagger_server.__main__:main']},
    long_description="""\
    This is the specification of the TA3 API for In The Moment (ITM).  Currently, the Evaluation API for TA2 supports functionality for the Phase 2 Evaluations.  The API is based on the OpenAPI 3.0.3 specification.
    """
)
