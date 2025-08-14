from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as file:
    long_description = file.read()

setup(
    name="spaceworld",
    version="0.1.0",
    author="binobinos",
    author_email="binobinos.dev@gmail.com",
    description=(
        "Spaceworld - CLI фреймворк нового поколения для удобной разработки команд "
        "на Python 3.11+ с поддержкой асинхронных команд"
    ),
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Binobinos/spaceworld-sli",
    license="MIT",
    keywords="cli framework async di dependency-injection performance",

    packages=find_packages(include=["spaceworld*"]),
    package_data={"spaceworld": ["py.typed"]},
    include_package_data=True,

    python_requires=">=3.11",
    install_requires=[],

    entry_points={
        'spaceworld.plugins': [
            'hello = plugins.hello:hello_cmd',
        ],
    },

    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Utilities",
    ],
    project_urls={
        "Documentation": "https://github.com/Binobinos/SpaceWorld-SLI/tree/master/docs",
        "Bug Tracker": "https://github.com/Binobinos/spaceworld-sli/issues",
        "Source Code": "https://github.com/Binobinos/spaceworld-sli",
    },
    zip_safe=False,
    platforms=["any"],
)
