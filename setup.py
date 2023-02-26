import setuptools

def get_description():
    with open('README.rst', 'r', encoding='utf-8') as f:
        return f.read()

setuptools.setup(
    name="aiotubes",
    version="2.0",
    license='MIT',
    author="sheldy",
    description="Asynchronous Youtube API",
    url="https://github.com/sheldygg/aiotube",
    packages=setuptools.find_packages(),
    long_description_content_type='text/markdown',
    long_description=get_description(),
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10"
    ],
    install_requires=[
        "aiohttp",
        "pydantic"
    ],)