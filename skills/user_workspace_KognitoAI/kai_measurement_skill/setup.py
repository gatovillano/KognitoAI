"""
Setup script para KAI Measurement Pipeline
"""

from setuptools import setup, find_packages

setup(
    name="kai_measurement",
    version="1.0.0",
    description="Pipeline de medición para KAI",
    packages=find_packages(),
    install_requires=[
        "aiohttp>=3.9.0",
        "statistics>=1.0.3.7"
    ],
    python_requires=">=3.10"
)
