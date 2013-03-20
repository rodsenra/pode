from setuptools import setup

setup(
    name='pode',
    version='0.0.2',
    py_modules=['uatu'],
    package_dir={'': 'src'},
    install_requires=['redis'],
)
