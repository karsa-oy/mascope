import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsa_services",
    version="0.3.0",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa Services",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=['services'],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'dask[array]',
        'numpy',
        'xarray',
        'zarr',
    ],
    entry_points={
        'console_scripts': [
            'karsa-dataviz-service = services.visualization:run',
            'karsa-file-streamer = services.file_streaming:run',
            'karsa-fileio-service = services.file_io:run',
            'karsa-sample-service = services.sample:run',
            'karsa-signal-service = services.signal:run',
            'karsa-target-service = services.target:run'
        ],
    }
)

