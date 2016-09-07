from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='hanon',
    version='1.0.0',

    description='Record and evaluate Hanon piano exercises',
    long_description=long_description,

    url='https://github.com/bluekeyes/hanon',
    license='MIT',
    author='Billy Keyes',
    author_email='bluekeyes@gmail.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Education',
        'Topic :: Multimedia :: Sound/Audio :: MIDI',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5'
    ],
    keywords='hanon midi piano',

    packages=find_packages(),
    package_data={
        'hanon': ['exercises.json']
    },
    install_requires=[
        'mido'
    ],

    entry_points={
        'console_scripts': [
            'hanon=hanon:main'
        ]
    }
)
