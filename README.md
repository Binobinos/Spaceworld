# SpaceWorld CLI
Spaceworld CLI - Это Cli Фреймворк нового поколения для удобной разработки своих
команд написанный на Python 3.11+ с поддержкой асинхронных команд

### Документация
- eng [English](eng)
- ru [Russian](ru)

## Возможности
- Создание модульной структуры команд и модулей
- Поддержка инъекции и валидации аргументов 
- Поддержка асинхронных команд
- Поддержка удобной настройки команд
- Добавление скрытых команд
- Собственные режимы команд для удобного управления
- Alias для команд
- Подтверждение опасных команд из коробки

# Простое использование

```python
from base_module import BaseModule
from space_world_api import SpaceWorld, MyWriter

module: BaseModule = BaseModule(name="sw",
                                docs="Базовые команды приложения SpaceWorld")


@module.register_command(name="help",
                         docs="Возвращает справку по командам",
                         activate_modes=["normal", "debug"])
def spaceworld_help(console: SpaceWorld, **kwargs):
    console.writer.write("\n".join(console.return_commands()))


@module.register_command(name="set",
                         docs="Устанавливает введенный режим",
                         example="set [MODE NAME] - set normal, set debug",
                         activate_modes=["all"])
def set(console: SpaceWorld, mode_name: str):
    console.set_mode(mode_name)
    console.writer.write(f"Установил {mode_name}")


@module.register_command(name="print_normal",
                         docs="Выводит сообщение в обычном режиме",
                         example="print_normal [MESSAGE] - print_normal spaceworld",
                         activate_modes=["normal"])
def print_normal(writer: MyWriter, message: str = "bino"):
    writer.write(message)


@module.register_command(name="print_debug",
                         docs="Выводит сообщение в debug режиме",
                         example="print_debug [MESSAGE] - print_debug spaceworld",
                         activate_modes=["debug"])
def print_debug(writer: MyWriter, message: str):
    writer.write(message)


def register() -> BaseModule:
    return module


```
# Документация
- [module](ru%2Fmodule) 
- - [Module.md](ru%2Fmodule%2FModule.md)
- [command](ru%2Fcommand)
- - [Command.md](ru%2Fcommand%2FCommand.md)
- [SpaceWorldAPI.md](ru%2FSpaceWorldAPI.md)
- --
## Лицензия
© Binobinos official. Все права защищены.
Лицензия MIT    
