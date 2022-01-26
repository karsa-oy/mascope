import setuptools


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsa_tools",
    version="0.1.0",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa Tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
#    packages=setuptools.find_packages(),
    packages=['sample_mover', ],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    # install_requires=[
    #     'karsalib',
    #     ...
    # ],
    extras_require={
        'sample_mover': [
        ],
        'all': [
        ],
    },
    entry_points={
        'console_scripts': [
            'karsa-sample-mover = sample_mover.SampleMover:run',
        ],
    }
)

