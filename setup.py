import setuptools
    
setuptools.setup(
    name="aiotubes",
    version="1.3",
    license='MIT',
    author="sheldy",
    description="Asynchronous Youtube API",
    url="https://github.com/sheldygg/aiotube",
    packages=setuptools.find_packages(),
    long_description_content_type='text/markdown',
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10"
    ],
    install_requires=[
        "aiohttp",
        "pydantic"
    ],)