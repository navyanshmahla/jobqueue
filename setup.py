from setuptools import setup, find_packages

setup(
    name="jobqueue",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=6.0",
        "schedule>=1.2.0",
        "click>=8.1.0",
        "psutil>=5.9.0",
        "nvidia-ml-py3>=7.352.0",
        "rich>=13.0.0",
    ],
    entry_points={
        "console_scripts": [
            "jobq=jobqueue.cli:main",
        ],
    },
    author="Navyansh Mahla",
    author_email="navyanshmahla17@gmail.com",
    description="A job queue manager for deep learning workloads",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/navyanshmahla/jobqueue",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
) 