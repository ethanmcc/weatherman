try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='weatherman',
    version='0.1',
    description='Elastic Beanstalk Stack Launcher',
    author='Ethan McCreadie',
    author_email='ethanmcc@gmail.com',
    url='https://github.com/ethanmcc/weatherman',
    modules=['weatherman'],
    install_requires=[
        'awsebcli>=3.3.2',
        'ConfigArgParse==0.9.3',
    ],
    entry_points={
        'console_scripts': [
            'weatherman = weatherman:dispatch',
        ],
    },
)