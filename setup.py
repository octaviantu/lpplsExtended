from setuptools import setup, find_packages
from setuptools import Command
import subprocess
from typing import List


class FormatCode(Command):
    description = "Formats the code using Black"
    user_options: List[str] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.run(["black", ".", "--line-length", "100"])


class TypeCheck(Command):
    description = "Run mypy type checking"
    user_options: List[str] = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.run(["mypy", "."])


with open("README.md", "r") as fh:
    long_description = fh.read()


print(f"find_packages: {find_packages()}")

setup(
    name="lppls",
    version="0.7",
    description="A Python module for fitting the LPPLS model to data.",
    packages=find_packages(),
    author="Octavian Tuchila",
    author_email="octaviantuchila14@gmail.com",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/octaviantu/lpplSornettePython",
    python_requires=">=3.10",
    install_requires=[
        "pandas",
        "matplotlib",
        "scipy",
        "xarray",
        "cma",
        "tqdm",
        "numba",
        "black",
        "statsmodels",
        "mypy",
        "typeguard",
        "ta",
    ],
    zip_safe=False,
    cmdclass={
        "format": FormatCode,
        "typecheck": TypeCheck,
    },
)
