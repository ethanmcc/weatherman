try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(
    name='weatherman',
    version='0.16',
    description='Elastic Beanstalk Stack Launcher',
    author='Ethan McCreadie',
    author_email='ethanmcc@gmail.com',
    url='https://github.com/ethanmcc/weatherman',
    py_modules=['weatherman'],
    test_suite='tests',
    install_requires=[
        'awsebcli>=3.3.2',
    ],
    entry_points={
        'console_scripts': [
            'weatherman = weatherman:dispatch',
        ],
    },
)
