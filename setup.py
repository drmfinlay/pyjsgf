from setuptools import setup

setup(
    name='pyjsgf',
    description='JSpeech Grammar Format (JSGF) compiler, matcher and parser '
                'package for Python.',
    long_description='''
        pyjsgf can be used to construct JSGF rules and grammars, compile them into
        strings or files, and find grammar rules that match speech hypothesis
        strings. Matching speech strings to tags is also supported. There are also
        parsers for grammars, rules and rule expansions.
    ''',
    url='https://github.com/Danesprite/pyjsgf',
    license='MIT',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Operating System :: OS Independent',
        'Topic :: Multimedia :: Sound/Audio :: Speech',
        'Topic :: Software Development :: Libraries',
    ],
    author='Dane Finlay',
    author_email='Danesprite@gmail.com',
    version='1.5.0',
    packages=['jsgf', 'jsgf.ext'],
    install_requires=['pyparsing', 'six']
)
