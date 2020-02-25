from setuptools import setup, find_packages
setup(
        name='corona19-notification',
        version='1.0',
        author='occidere',
        author_email='occidere@naver.com',
        url='https://github.com/occidere/corona19-notification',
        description='No Description',
        license='Apache 2.0',
        install_requires=[
            'requests',
            'line-bot-sdk',
            'pyyaml',
            'setuptools',
            'beautifulsoup4'
        ],
        packages=find_packages(exclude=['venv', 'doc', 'test']),
        python_requires='>=3.5',
        package_data={
            'resources': ['resources/*']
        },
        zip_safe=False,
        classifiers=[
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
            'Programming Language :: Python :: 3.7',
            'Programming Language :: Python :: 3.8',
        ]
)

