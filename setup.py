from setuptools import setup, find_packages

setup(
    name='graph-gen',
    version='0.3',
    packages=find_packages(),
    install_requires=[
        'osmnx',
        'geopy'
    ],
    entry_points={
        'console_scripts': [
            'generate-graph=graph_gen.generate:main',
        ],
    },
    author='Raven van Ewijk',
    author_email='ravenvanewijk1@gmail.com',
    description='A package for generating OSM graphs',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/ravenvanewijk/graph-gen',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
