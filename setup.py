from distutils.core import setup

setup(
    name='roam_to_git',
    packages=['roam_to_git'],
    version='0.1',
    license='MIT',
    description='Automatic RoamResearch backup to Git',
    author='Matthieu Bizien',  # Type in your name
    author_email='oao2005@gmail.com',  # Type in your E-Mail
    url='https://github.com/MatthieuBizien/roam-to-git',
    download_url='https://github.com/MatthieuBizien/roam-to-git/archive/v0.1.tar.gz',
    keywords=['ROAMRESEARCH', 'GIT', 'BACKUP'],
    install_requires=[
        'gitpython',
        'pyppeteer',
        'python-dotenv',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content :: Wiki',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
