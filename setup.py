import setuptools
from setuptools import Command
import subprocess


class FormatCode(Command):
    description = "Formats the code using Black"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        subprocess.run(["black", ".", "--line-length", "100"])


with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="lppls",
    version="0.7",
    description="A Python module for fitting the LPPLS model to data.",
    packages=["lppls"],
    author="Octavian Tuchila, Josh Nielsen, Didier Sornette",
    author_email="josh@boulderinvestment.tech",
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
    ],
    zip_safe=False,
    include_package_data=True,
    package_data={"": ["data/*.csv"]},
    cmdclass={
        "format": FormatCode,
    },
)
