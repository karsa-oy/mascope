import setuptools
import os


with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="karsa_router_service",
    version="0.0.1",
    author='Karsa Oy',
    author_email='support@karsa.fi',
    description="Karsa Router Service",
    long_description=long_description,
    long_description_content_type="text/markdown",
#    packages=setuptools.find_packages(),
    packages=['router_service', ],
    include_package_data=True,
    python_requires=">=3.6",
    classifiers=[
        'Programming Language :: Python :: 3.6',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'aiohttp',
        'aiohttp_cors',
        'asyncio',
        'environs',
        'python-socketio<5',
    ],
    entry_points={
        'console_scripts': [
            'karsa-router-service = router_service.Router:run',
        ],
    }
)

