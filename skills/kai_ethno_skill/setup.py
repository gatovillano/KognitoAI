"""
Setup para KAI-Ethno - Investigación Antropológica Aumentada
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="kai-ethno",
    version="1.0.0",
    author="KognitoAI",
    author_email="contact@kognito.ai",
    description="Investigación antropológica aumentada mediante arquitectura multi-agente",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kognitoai/kai-ethno",
    packages=find_packages(exclude=["tests", "tests.*", "examples", "references"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "ruff>=0.1.0",
            "mypy>=1.5.0",
        ],
        "neo4j": [
            "neo4j>=5.0.0",
        ],
        "local-llm": [
            "transformers>=4.30.0",
            "torch>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "kai-ethno=scripts.orchestrator:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
