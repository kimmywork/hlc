#!/usr/bin/env python3
"""
HLC Code (Hexagonal Layered Code) - Python implementation

A progressive 2D graphical code system with layered architecture
"""

from setuptools import setup, find_packages
import os

# 读取版本号
with open(os.path.join("hlc", "__init__.py"), "r") as f:
    for line in f:
        if line.startswith("__version__"):
            version = line.split("=")[1].strip().strip('"')
            break
    else:
        version = "0.1.0"

# 读取 requirements.txt
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="hlc-code",
    version=version,
    description="HLC (Hexagonal Layered Code) - A progressive 2D graphical code system",
    long_description=open("README.md", "r", encoding="utf-8").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Mistral AI",
    author_email="",
    url="https://github.com/mistralai/hlc-code",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Image Recognition",
    ],
    keywords="2d-code barcode qrcode hexagonal layered-code",
    project_urls={
        "Bug Reports": "https://github.com/mistralai/hlc-code/issues",
        "Source": "https://github.com/mistralai/hlc-code",
    },
    entry_points={
        "console_scripts": [
            "hlc-encode=hlc.cli:encode_command",
            "hlc-decode=hlc.cli:decode_command",
        ],
    },
    include_package_data=True,
    package_data={
        "hlc": ["*.md", "*.txt"],
    },
)
