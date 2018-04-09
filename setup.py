from setuptools import setup

setup(
    name='pyjsgf',
    description='Java Speech Grammar Format (JSGF) compiler and matcher for Python',
    long_description="""
        pyjsgf can be used to construct JSGF rules and grammars, compile them into 
        strings or files, and match speech text to the matching rule objects used 
        to compile the grammars. Speech text can be from a recognition engine's 
        speech hypothesis, for example.
    """,
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Software Development :: Libraries",
    ],
    author='Dane Finlay',
    author_email='Danesprite@gmail.com',
    version='1.2.0',
    packages=['jsgf', 'jsgf.ext'],
    install_requires=["pyparsing"]
)
