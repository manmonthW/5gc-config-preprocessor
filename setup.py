"""
Setup script for 5GC Config Preprocessor
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding='utf-8')

# Read requirements
requirements = (this_directory / "requirements.txt").read_text().splitlines()

setup(
    name="5gc-config-preprocessor",
    version="1.0.0",
    author="5GC Config Preprocessor Team",
    author_email="support@example.com",
    description="A comprehensive preprocessing tool for 5G Core Network configuration files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/5gc-config-preprocessor",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/5gc-config-preprocessor/issues",
        "Documentation": "https://yourusername.github.io/5gc-config-preprocessor/",
        "Source Code": "https://github.com/yourusername/5gc-config-preprocessor",
    },
    packages=find_packages(where=".", include=["src*"]),
    package_dir={"": "."},
    package_data={
        "": ["config.yaml", "*.md"],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Telecommunications Industry",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=3.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.950",
            "pylint>=2.13.0",
            "bandit>=1.7.0",
        ],
        "docs": [
            "mkdocs>=1.3.0",
            "mkdocs-material>=8.2.0",
            "mkdocs-mermaid2-plugin>=0.6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "5gc-preprocess=src.preprocessor:main",
            "config-preprocess=src.preprocessor:main",
        ],
    },
    keywords=[
        "5g",
        "5gc",
        "configuration",
        "preprocessing",
        "desensitization",
        "network",
        "telecom",
        "config-management",
    ],
)
