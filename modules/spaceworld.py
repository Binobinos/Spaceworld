from base_module import BaseModule

module: BaseModule = BaseModule(name="spaceworld",
                                docs="Второй основной модуль консоли который предоставляет обширный набор команд")


@module.register_command(name="hello",
                         docs="Выводит приветственное сообщение",
                         confirm="Выводить сообщение в команде")
async def file_create(name: str):
    print(f"Привет {name}")


def register() -> BaseModule:
    return module
