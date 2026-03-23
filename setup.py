"""EvoForge setup configuration."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="evoforge",
    version="0.1.0",
    author="EvoForge AI",
    author_email="contact@evoforge.ai",
    description="Self-Evolving AI Agent Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/johnnykang101/evoforge",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "black>=23.0",
            "isort>=5.12",
            "mypy>=1.0",
        ],
        "benchmark": [
            "matplotlib>=3.7",
            "seaborn>=0.12",
            "pandas>=2.0",
            "jupyter>=1.0",
        ],
    },
)
