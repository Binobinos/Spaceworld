# Guide to Contributing to the SpaceWorld CLI

Thank you for your interest in participating in the development of SpaceWorld! This is a Python CLI framework, and we
welcome your help.

## How to contribute

### Error message

1. Check [existing issues](https://github.com/Binobinos/Spaceworld/issues ) to avoid duplication
2. Create a new issue with:
- A clear description of the problem
- Steps to reproduce
- Expected and actual behavior

### Functionality requests

1. Open the issue marked "[Feature Request]" in the header
2. Describe the functionality and its advantages
3. Provide usage examples.

### Participation in the development

1. Make a fork of the repository
2. Create a new branch ('git checkout -b feature/your-feature` or `fix/your-bugfix')
3. Make commits with clear messages
4. Push the changes to your fork
5. Open the Pull Request

## Setting up the development environment

### Requirements

- Python 3.12+
- pip

### Installation

1. Clone your fork:
   ```bash
   git clone https://github.com/Binobinos/Spaceworld.git
   cd SpaceWorld

Create and activate a virtual environment:

```shell
python -m venv venv

$ source venv/bin/activate # MacOS and Linux

$ venv\Scripts\activate.bat # Windows
```

### Coding standards

- Follow PEP 8

- Use type hints for the new code

- Document public methods using docstrings (Google style)

Before sending the PR, follow these steps:

```
mypy spaceworld --strict
```

### Documentation

When adding new features:

- Update README.md
- Check for type hints and docstring

### The code review process

PR will be checked by maintainers

Changes may be requested.

After the approval, the PR will be immediately

# Thank you for your contribution to SpaceWorld! 🧡