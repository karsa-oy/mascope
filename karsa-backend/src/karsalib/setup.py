import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsalib",
    version="0.3.0",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa Utils Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    #packages=setuptools.find_packages(),
    packages=['karsalib', 'karsalib/molmass'],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'dask[array]',
        'datetime_glob',
        'numpy==1.20',	# this is due to numba requirement: numpy<1.21,>=1.17
        'pandas',
        'python-socketio',
        'pyyaml',
        'scipy',
        'sparse',
        'xarray',
        'asynctest',
        'decorator',
        'watchdog'
    ]
)

