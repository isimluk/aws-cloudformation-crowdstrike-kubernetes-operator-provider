from glob import glob
from os.path import basename, splitext
from setuptools import find_packages, setup


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="cloudformation-crowdstrike-kubernetes-operator-provider",
    version="0.0.1",
    author="CrowdStrike",
    maintainer="Simon Lukasik",
    description="CloudFormation type provider CrowdStrike::Kubernetes::Operator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/isimluk/aws-cloudformation-crowdstrike-kubernetes-operator-provider",
    packages=find_packages("src"),
    package_dir={"": "src"},
    py_modules=[splitext(basename(path))[0] for path in glob("src/crowdstrike_kubernetes_operator/*.py")],
    include_package_data=True,
    install_requires=[
        'cloudformation-cli-python-lib>=2.1.9',
        'ruamel.yaml>=0.17.4',
        'awscli',
        'kubernetes'
    ],
    extras_require={
        'devel': [
            'flake8',
            'pylint',
            'pytest',
            'bandit',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Operating System :: Unix",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: The Unlicense (Unlicense)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
