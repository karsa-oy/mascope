import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsa_hw_interfaces",
    version="0.3.0",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa mass spec hardware interfaces",
    long_description=long_description,
    long_description_content_type="text/markdown",
#    packages=setuptools.find_packages(),
    packages=['karsaorbi', 'karsatof', 'karsavlm', ],
    include_package_data=True,
    python_requires=">=3.6, !=3.9.*",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
	'colorcet',
        'dask[complete]',
        'datashader',
        'datetime_glob',
        'h5py',
        'h5sparse',
        'numpy',
        'pandas',
	'Pillow',
        'pythonnet',
        'scikit-learn',
        'scipy',
        'sparse',
        'xarray',
    ]
)

