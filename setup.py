# setup.py

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README.md
def read_long_description():
    here = Path(__file__).parent
    with open(here / "README.md", encoding="utf-8") as fh:
        return fh.read()


setup(
    name="edgar-analytics",
    version="0.1.0",
    author="Zohar Babin",
    author_email="z.babin@gmail.com",
    description="A library for analyzing SEC EDGAR filings with financial metrics and forecasting.",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/zoharbabin/edgar_analytics",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pandas",
        "numpy",
        "statsmodels",
        "edgartools",
        "click",  # For CLI functionality
    ],
    extras_require={
        "test": [
            "pytest",
            "pytz",
        ],
    },
    entry_points={
        "console_scripts": [
            "edgar-analytics=edgar_analytics.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.10',
)
