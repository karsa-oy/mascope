import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsa_services",
    version="0.0.1",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa Services",
    long_description=long_description,
    long_description_content_type="text/markdown",
#    packages=setuptools.find_packages(),
    packages=['services', ],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'asyncio',
        'dask[array]',
        'environs',
        'numpy',
        'openpyxl',
        'xarray',
        'zarr',
    ],
    entry_points={
        'console_scripts': [
            'karsa-fileio-service = services.FileIoService:run',
            'karsa-sample-service = services.SampleManagerService:run',
            'karsa-dataviz-service = services.DataVizService:run',
            'karsa-signal-service = services.SignalProcessorService:run',
            'karsa-h5-streamer = services.TWh5Streamer:run',
        ],
    }
)

