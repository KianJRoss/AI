"""Setup file for ai-kernel project."""

from setuptools import setup, find_packages

setup(
    name="ai-kernel",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        "pyyaml",
        "pytest",
    ],
)
