from setuptools import setup, find_packages

setup(
    name="facebook_ad_scraper",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'selenium>=4.0.0',
        'webdriver-manager>=3.8.0',
        'beautifulsoup4>=4.9.3',
        'python-dotenv>=0.19.0',
        'flask>=2.0.0',
        'urllib3>=1.26.0'
    ],
) 