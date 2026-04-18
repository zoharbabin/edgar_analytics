# setup.py

import setuptools
from pathlib import Path

def read_long_description():
    here = Path(__file__).parent
    with open(here / "README.md", encoding="utf-8") as fh:
        return fh.read()

setuptools.setup(
    name="edgar-analytics",
    version="1.0.3",
    author="Zohar Babin",
    author_email="z.babin@gmail.com",
    description="A library and CLI tool for analyzing SEC EDGAR filings with financial metrics and forecasting.",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/zoharbabin/edgar_analytics",
    packages=setuptools.find_packages(),
    include_package_data=True,
    python_requires=">=3.10",
    install_requires=[
        "pandas>=1.5,<4",
        "numpy>=1.23,<3",
        "edgartools>=5.0,<6",
        "click>=8.0,<9",
        "rich>=12.0,<15",
    ],
    extras_require={
        "forecast": [
            "statsmodels>=0.13,<1",
        ],
        "valuation": [
            "yfinance>=0.2,<1",
        ],
        "cache": [
            "diskcache>=5.6,<6",
        ],
        "parquet": [
            "pyarrow>=12.0,<18",
        ],
        "test": [
            "pytest",
            "pytz",
            "pytest-xdist",
            "pytest-timeout",
            "statsmodels>=0.13,<1",
        ],
    },
    entry_points={
        "console_scripts": [
            "edgar-analytics=edgar_analytics.cli:main",
        ],
    },
    classifiers=[
        # ------------------------------------------
        # Updated and expanded PyPI Trove Classifiers
        # ------------------------------------------
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
