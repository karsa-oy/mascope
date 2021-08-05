import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="scenthound",
    version="0.3.0",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa MS Signal Processing Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
#    packages=setuptools.find_packages(),
    packages=['karsavlm', 'scenthound'],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'h5sparse',
        'lmfit',
        'numpy',
        'pandas',
        'scipy',
        'scikit-learn'
    ]
)