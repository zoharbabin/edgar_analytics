# setup.py

import setuptools
from pathlib import Path

def read_long_description():
    here = Path(__file__).parent
    with open(here / "README.md", encoding="utf-8") as fh:
        return fh.read()

setuptools.setup(
    name="edgar-analytics",
    version="0.1.0",
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
        "pandas",
        "numpy",
        "statsmodels",
        "edgartools",
        "click",
        "rich",
    ],
    extras_require={
        "test": [
            "pytest",
            "pytz",
            "pytest-xdist",
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
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
