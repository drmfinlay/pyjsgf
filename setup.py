from distutils.core import setup

setup(
      name='pyjsgf',
      description='JSpeech Grammar Format (JSGF) compiler and matcher for Python',
      long_description="""
            pyjsgf can be used to construct JSGF rules and grammars, compile them into 
            strings or files, and match speech text to the matching rule objects used 
            to compile the grammars. Speech text can be from a recognition engine's 
            speech hypothesis, for example.
      """,
      maintainer='Dane Finlay',
      version='1.0',
      packages=['jsgf'])
