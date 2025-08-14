# Module

В предыдущих разделах мы познакомились с вариантами создания команды, с аргументами и основами. 
В этом разделе мы поговорим о модулях и их подмодулях, а также о том, что с ними связано.
---
## Creating a module
### Option 1. Manual creation
Let's create a git module.
```python
from spaceworld import SpaceWorld, BaseModule
from pathlib import Path
console = SpaceWorld()
git = BaseModule(name="git", docs="version control system")

@git.command()
def add(path: Path):
    print(f"Adding {path.name}...")


if __name__ == '__main__':
    console()

``` 
