#!/usr/bin/env python3
"""
SpaceWorld CLI Framework Benchmark Tool
"""

import argparse
import asyncio
import cProfile
import json
import os
import platform
import pstats
import statistics
import sys
import timeit
import traceback
import tracemalloc
from contextlib import contextmanager
from datetime import datetime
from importlib.metadata import version
from typing import Dict, List, Callable, Any, Optional, Set

import click
import cloup
import fire
import typer


from rich.box import ROUNDED
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

import spaceworld

# Конфигурация по умолчанию
DEFAULT_RUNS = 30
DEFAULT_WARMUP = 5
DEFAULT_OUTPUT = "benchmark_results.json"
LIBRARY_COLORS = {
    'click': 'yellow',
    'typer': 'magenta',
    'spaceworld': 'cyan',
    'testfunc': 'green',
    'argparse': 'blue',
    'fire': 'red',
    'cloup': 'white'
}

console = Console()


class TestScenario:
    """Класс для описания тестового сценария"""

    def __init__(
            self,
            name: str,
            command: str,
            description: str = "",
            complexity: str = "simple"
    ):
        self.name = name
        self.command = command
        self.description = description
        self.complexity = complexity


# Исправленные тестовые сценарии
DEFAULT_SCENARIOS = [
    TestScenario(
        name="simple_command",
        command="hello 10",
        description="Простая команда с одним аргументом"
    ),
    TestScenario(
        name="subcommand",
        command="subcmd 10 --verbose",
        description="Команда с подкомандой и флагом",
        complexity="medium"
    )
]


class BenchmarkResult:
    """Класс для хранения результатов одного теста"""

    def __init__(self):
        self.times: List[float] = []
        self.memory_usage: List[int] = []
        self.profile_data: Optional[Dict] = None

    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0

    @property
    def avg_memory(self) -> float:
        return statistics.mean(self.memory_usage) if self.memory_usage else 0

    @property
    def peak_memory(self) -> float:
        return max(self.memory_usage) if self.memory_usage else 0


class BenchmarkLibrary:
    """Класс для представления тестируемой библиотеки"""

    def __init__(
            self,
            name: str,
            setup_func: Callable,
            execute_func: Callable,
            enabled: bool = True
    ):
        self.name = name
        self.setup_func = setup_func
        self.execute_func = execute_func
        self.enabled = enabled
        self.color = LIBRARY_COLORS.get(name, 'white')
        self.version = self._get_version()
        self.results: Dict[str, BenchmarkResult] = {}

    def _get_version(self) -> str:
        """Получает версию библиотеки"""
        if self.name == 'testfunc':
            return '1.0'
        elif self.name == 'spaceworld':
            return spaceworld.__version__
        try:
            return version(self.name)
        except:
            return 'unknown'

    def run_test(
            self,
            scenario: TestScenario,
            runs: int,
            warmup: int,
            measure_memory: bool
    ) -> BenchmarkResult:
        """Запускает тест для конкретного сценария"""
        result = BenchmarkResult()
        env = self.setup_func()

        # Прогрев (если нужно)
        # for _ in range(warmup):
        # self.execute_func(env, scenario.command)

        # Замер времени (делаем 'runs' повторов с 1 выполнение в каждом)
        timer = timeit.Timer(
            lambda: self.execute_func(env, scenario.command))
        result.times = timer.repeat(repeat=runs, number=1)

        # Замер памяти (отдельно, так как tracemalloc влияет на производительность)
        if measure_memory:
            for _ in range(runs):
                tracemalloc.start()
                self.execute_func(env, scenario.command)
                _, peak = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                result.memory_usage.append(peak)

        self.results[scenario.name] = result
        return result

    def run_profiling(
            self,
            scenario: TestScenario,
            runs: int = 1
    ) -> Dict[str, Any]:
        """Улучшенное профилирование с фильтрацией SpaceWorld функций"""
        env = self.setup_func()
        profiler = cProfile.Profile(timeunit=False, subcalls=False)

        # Включаем профилирование с игнорированием встроенных функций
        profiler.enable()
        self.execute_func(env, scenario.command)
        profiler.disable()

        stats = pstats.Stats(profiler)
        stats.sort_stats(pstats.SortKey.TIME)
        top_functions = []

        # Собираем и фильтруем результаты
        for func, (cc, nc, tt, ct, callers) in stats.stats.items():
            file, line, func_name = func

            # Фильтруем по:
            # 1. Функциям SpaceWorld (по имени файла)
            # 2. Игнорируем системные и встроенные вызовы
            # Нормализуем время на количество прогонов
            normalized_time = ct / runs

            top_functions.append({
                'function': func_name,
                'location': f"{os.path.basename(file)}:{line}",
                'time': normalized_time,
                'time_str': format_time(normalized_time),
                'calls': nc  # Добавляем количество вызовов
            })

        # Сортируем по убыванию времени и берем топ-15
        sorted_functions = sorted(top_functions, key=lambda x: -x['time'])

        # Добавляем общую статистику
        total_time = sum(f['time'] for f in sorted_functions)
        total_calls = sum(f['calls'] for f in sorted_functions)

        return {
            'top_functions': sorted_functions,
            'total_time': total_time,
            'total_time_str': format_time(total_time),
            'total_calls': total_calls
        }


class BenchmarkRunner:
    """Основной класс для управления процессом тестирования"""

    def __init__(self):
        self.libraries: Dict[str, BenchmarkLibrary] = {}
        self.scenarios: List[TestScenario] = DEFAULT_SCENARIOS
        self.results: Dict[str, Dict[str, BenchmarkResult]] = {}
        self.config = {
            'runs': DEFAULT_RUNS,
            'warmup': DEFAULT_WARMUP,
            'output': DEFAULT_OUTPUT,
            'memory': True,
            'profile': False
        }

    def add_library(self, library: BenchmarkLibrary) -> None:
        """Добавляет библиотеку для тестирования"""
        self.libraries[library.name] = library

    def add_scenario(self, scenario: TestScenario) -> None:
        """Добавляет тестовый сценарий"""
        self.scenarios.append(scenario)

    def run_benchmarks(self) -> None:
        """Запускает все тесты"""
        with Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(bar_width=50),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                console=console
        ) as progress:
            total = len(self.libraries) * len(self.scenarios)
            task = progress.add_task("Running benchmarks", total=total)

            for scenario in self.scenarios:
                for lib_name, library in self.libraries.items():
                    if not library.enabled:
                        continue

                    progress.update(
                        task,
                        description=f"[{library.color}]Testing {lib_name} - {scenario.name}"
                    )

                    try:
                        result = library.run_test(
                            scenario,
                            self.config['runs'],
                            self.config['warmup'],
                            self.config['memory']
                        )

                        if self.config['profile']:
                            profile_data = library.run_profiling(scenario)
                            result.profile_data = profile_data

                        self.results.setdefault(scenario.name, {})[lib_name] = result

                    except Exception as e:
                        console.print(f"[red]Error testing {lib_name}: {e}")
                        traceback.print_exc()

                    progress.update(task, advance=1)

    def print_results(self) -> None:
        """Выводит результаты в удобном формате с улучшенной визуализацией"""
        console.print()
        console.rule("[bold magenta]📊 Comprehensive Benchmark Results[/]", style="bold magenta")

        # Информация о системе
        self._print_system_info()

        # Сводная таблица по всем сценариям
        self._print_summary_table()

        # Детальные результаты по каждому сценарию
        for scenario in self.scenarios:
            if scenario.name not in self.results:
                continue

            console.print()
            console.rule(
                f"[bold]Scenario: [cyan]{scenario.name}[/] - {scenario.description}",
                style="bold blue"
            )

            # Таблица времени выполнения
            self._print_time_table(scenario)

            # Таблица памяти
            if self.config['memory']:
                self._print_memory_table(scenario)

            # Профилирование
            if self.config['profile']:
                self._print_profiling_results(scenario)

    def _print_system_info(self) -> None:
        """Выводит информацию о системе и версиях библиотек"""
        sys_info = Table.grid(padding=(0, 2))
        sys_info.add_column(style="bold")
        sys_info.add_column()

        sys_info.add_row("🖥️ System:", f"{platform.system()} {platform.release()}")
        sys_info.add_row("🐍 Python:", sys.version.split()[0])
        sys_info.add_row("📅 Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        sys_info.add_row("🏃 Runs:", str(self.config['runs']))
        sys_info.add_row("🔥 Warmup:", str(self.config['warmup']))

        console.print(Panel.fit(
            sys_info,
            title="⚙️ System Information",
            border_style="yellow"
        ))

        # Версии библиотек
        libs_table = Table(
            title="📚 Tested Libraries",
            box=ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        libs_table.add_column("Library")
        libs_table.add_column("Version")
        libs_table.add_column("Status")

        for lib in self.libraries.values():
            status = "[green]✓" if lib.enabled else "[red]✗"
            libs_table.add_row(
                f"[{lib.color}]{lib.name}[/]",
                lib.version,
                status
            )

        console.print()
        console.print(libs_table)

    def _print_summary_table(self) -> None:
        """Выводит сводную таблицу с улучшенным форматированием"""
        summary_table = Table(
            title="🏆 Performance Summary (All Scenarios)",
            box=ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )

        summary_table.add_column("Library", style="bold", width=12)
        summary_table.add_column("Time (μs)", justify="right", width=12)
        summary_table.add_column("Memory", justify="right", width=12)
        summary_table.add_column("Time Factor", justify="right", width=12)
        summary_table.add_column("Efficiency", justify="right", width=12)
        summary_table.add_column("Performance", justify="left")

        # Собираем средние значения по всем сценариям
        lib_results = {}
        for lib_name in self.libraries:
            if not self.libraries[lib_name].enabled:
                continue

            total_time = 0
            total_memory = 0
            count = 0

            for scenario in self.scenarios:
                if scenario.name in self.results and lib_name in self.results[scenario.name]:
                    result = self.results[scenario.name][lib_name]
                    total_time += result.avg_time
                    total_memory += result.avg_memory
                    count += 1

            if count > 0:
                lib_results[lib_name] = {
                    "avg_time": total_time / count,
                    "avg_memory": total_memory / count
                }

        # Находим лучшие показатели
        best_time = min(result["avg_time"] for result in lib_results.values())
        best_memory = min(result["avg_memory"] for result in lib_results.values())

        for lib_name, result in sorted(
                lib_results.items(),
                key=lambda x: x[1]["avg_time"]
        ):
            lib = self.libraries[lib_name]

            # Рассчитываем показатели эффективности
            time_factor = result["avg_time"] / best_time
            memory_factor = result["avg_memory"] / best_memory if best_memory > 0 else 1
            efficiency = (1 / time_factor + 1 / memory_factor) / 2

            # Генерируем индикатор
            perf_indicator = self._generate_performance_indicator(time_factor)

            summary_table.add_row(
                f"[bold {lib.color}]{lib_name}[/]",
                f"[cyan]{result['avg_time'] * 1e6:.2f}[/]",
                f"[green]{format_memory(result['avg_memory'])}[/]",
                f"[yellow]{time_factor:.1f}x[/]",
                f"[bold]{efficiency:.1%}[/]",
                perf_indicator
            )

        console.print()
        console.print(summary_table)
        console.print("\n[dim]Time Factor: Relative to fastest library (lower is better)")
        console.print("[dim]Efficiency: Combined metric of speed and memory (higher is better)")

    def _print_time_table(self, scenario: TestScenario) -> None:
        """Выводит таблицу времени с улучшенным форматированием"""
        time_table = Table(
            title="⏱️ Execution Time",
            box=ROUNDED,
            show_header=True,
            header_style="bold green"
        )

        time_table.add_column("Library", style="bold", width=12)
        time_table.add_column("Avg (μs)", justify="right", width=10)
        time_table.add_column("Min (μs)", justify="right", width=10)
        time_table.add_column("Max (μs)", justify="right", width=10)
        time_table.add_column("Std Dev", justify="right", width=10)
        time_table.add_column("Factor", justify="right", width=8)
        time_table.add_column("Performance", justify="left")

        scenario_results = self.results[scenario.name]
        if not scenario_results:
            return

        # Находим самое быстрое время
        fastest_time = min(result.avg_time for result in scenario_results.values())

        for lib_name, result in sorted(
                scenario_results.items(),
                key=lambda x: x[1].avg_time
        ):
            lib = self.libraries[lib_name]

            # Рассчитываем относительную производительность
            relative = result.avg_time / fastest_time if fastest_time > 0 else 1
            performance_bar = self._generate_performance_bar(relative)

            # Рассчитываем стандартное отклонение
            if len(result.times) > 1:
                std_dev = statistics.stdev(result.times)
                std_dev_str = f"{std_dev * 1e6:.2f} μs"
            else:
                std_dev_str = "N/A"

            time_table.add_row(
                f"[{lib.color}]{lib_name}[/]",
                f"{result.avg_time * 1e6:.2f}",
                f"{min(result.times) * 1e6:.2f}",
                f"{max(result.times) * 1e6:.2f}",
                std_dev_str,
                f"{relative:.1f}x",
                performance_bar
            )

        console.print()
        console.print(time_table)

    def _print_memory_table(self, scenario: TestScenario) -> None:
        """Выводит таблицу памяти с улучшенным форматированием"""
        if not self.config['memory']:
            return

        mem_table = Table(
            title="🧠 Memory Usage",
            box=ROUNDED,
            show_header=True,
            header_style="bold blue"
        )

        mem_table.add_column("Library", style="bold", width=12)
        mem_table.add_column("Avg", justify="right", width=12)
        mem_table.add_column("Peak", justify="right", width=12)
        mem_table.add_column("Factor", justify="right", width=8)
        mem_table.add_column("Efficiency", justify="left")

        scenario_results = self.results[scenario.name]
        if not scenario_results:
            return

        # Находим минимальное использование памяти
        min_memory = min(result.avg_memory for result in scenario_results.values())

        for lib_name, result in sorted(
                scenario_results.items(),
                key=lambda x: x[1].avg_memory
        ):
            lib = self.libraries[lib_name]

            # Рассчитываем относительное использование памяти
            relative = result.avg_memory / min_memory if min_memory > 0 else 1
            efficiency_bar = self._generate_efficiency_bar(relative)

            mem_table.add_row(
                f"[{lib.color}]{lib_name}[/]",
                format_memory(result.avg_memory),
                format_memory(result.peak_memory),
                f"{relative:.1f}x",
                efficiency_bar
            )

        console.print()
        console.print(mem_table)

    def _generate_performance_indicator(self, factor: float) -> str:
        """Генерирует текстовый индикатор для сводной таблицы"""
        if factor <= 1.5:
            return "[bold green]★★★★★[/] Exceptional"
        elif factor <= 3:
            return "[green]★★★★☆[/] Excellent"
        elif factor <= 10:
            return "[yellow]★★★☆☆[/] Good"
        elif factor <= 50:
            return "[orange]★★☆☆☆[/] Fair"
        else:
            return "[red]★☆☆☆☆[/] Poor"

    def _generate_performance_bar(self, relative: float) -> str:
        """Генерирует текстовую полосу производительности"""
        if relative <= 1.2:
            return "[green]▰▰▰▰▰▰▰▰▰▰[/]"
        elif relative <= 2:
            return "[green]▰▰▰▰▰▰▰▰▱▱[/]"
        elif relative <= 5:
            return "[yellow]▰▰▰▰▰▰▱▱▱▱[/]"
        elif relative <= 20:
            return "[yellow]▰▰▰▰▱▱▱▱▱▱[/]"
        elif relative <= 100:
            return "[orange]▰▰▱▱▱▱▱▱▱▱[/]"
        else:
            return "[red]▰▱▱▱▱▱▱▱▱▱[/]"

    def _generate_efficiency_bar(self, relative: float) -> str:
        """Генерирует текстовую полосу эффективности"""
        if relative <= 1.2:
            return "[green]▰▰▰▰▰▰▰▰▰▰[/]"
        elif relative <= 2:
            return "[green]▰▰▰▰▰▰▰▰▱▱[/]"
        elif relative <= 5:
            return "[yellow]▰▰▰▰▰▰▱▱▱▱[/]"
        elif relative <= 10:
            return "[yellow]▰▰▰▰▱▱▱▱▱▱[/]"
        elif relative <= 20:
            return "[orange]▰▰▱▱▱▱▱▱▱▱[/]"
        else:
            return "[red]▰▱▱▱▱▱▱▱▱▱[/]"

    def _print_profiling_results(self, scenario: TestScenario) -> None:
        """Выводит результаты профилирования"""
        if not self.config['profile']:
            return

        console.print()
        console.rule("[bold magenta]📊 Profiling Results[/]", style="bold magenta")

        for lib_name, result in self.results[scenario.name].items():
            if not result.profile_data:
                continue

            lib = self.libraries[lib_name]

            profile_table = Table(
                title=f"[{lib.color}]{lib_name}[/] - Top Functions",
                box=ROUNDED,
                show_header=True,
                header_style=f"bold {lib.color}"
            )

            profile_table.add_column("Function", style="bold")
            profile_table.add_column("Location", style="dim")
            profile_table.add_column("Time", justify="right")

            for func in result.profile_data['top_functions']:
                profile_table.add_row(
                    func['function'],
                    func['location'],
                    func['time_str']
                )

            console.print()
            console.print(profile_table)

    def save_results(self, filename: str = None) -> None:
        """Сохраняет результаты в JSON файл"""
        filename = filename or self.config['output']
        results = {
            'config': self.config,
            'scenarios': [s.__dict__ for s in self.scenarios],
            'results': {
                scenario: {
                    lib: {
                        'times': res.times,
                        'memory_usage': res.memory_usage
                    }
                    for lib, res in scenario_res.items()
                }
                for scenario, scenario_res in self.results.items()
            },
            'system': {
                'platform': platform.platform(),
                'python': sys.version,
                'timestamp': datetime.now().isoformat()
            }
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)

        console.print(f"\n[green]✓ Results saved to {filename}")

    def load_results(self, filename: str) -> None:
        """Загружает результаты из файла"""
        with open(filename, 'r') as f:
            data = json.load(f)
            self.config = data['config']
            self.scenarios = [TestScenario(**s) for s in data['scenarios']]
            self.results = {
                scenario: {
                    lib: BenchmarkResult() for lib in lib_res.keys()
                }
                for scenario, lib_res in data['results'].items()
            }

        console.print(f"\n[green]✓ Results loaded from {filename}")


def format_time(seconds: float) -> str:
    """Форматирует время для отображения"""
    if seconds < 1e-6:
        return f"{seconds * 1e9:.2f} ns"
    elif seconds < 1e-3:
        return f"{seconds * 1e6:.2f} μs"
    elif seconds < 1:
        return f"{seconds * 1e3:.2f} ms"
    return f"{seconds:.4f} s"


def format_memory(bytes_val: int) -> str:
    """Форматирует объем памяти для отображения"""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 ** 2:
        return f"{bytes_val / 1024:.2f} KB"
    elif bytes_val < 1024 ** 3:
        return f"{bytes_val / (1024 ** 2):.2f} MB"
    return f"{bytes_val / (1024 ** 3):.2f} GB"


def print_welcome(scenarios: List[TestScenario], libraries: Set[str]) -> None:
    """Выводит приветственное сообщение"""
    console.clear()
    console.rule("[bold blue]🚀 CLI Framework Benchmark Tool[/]", style="bold blue")

    # ASCII арт
    rocket = Text("""
          /\\
         /  \\
        /____\\
        |    |
        |SPW |
       /|____|\\
      /_|____|_\\
        |    |
        |    |
        |    |
       /      \\
      /        \\
    """, style="cyan")

    # Описание сценариев
    scenarios_text = "\n".join(
        f"• [bold]{s.name}[/]: {s.description} ([{get_complexity_color(s.complexity)}]{s.complexity}[/])"
        for s in scenarios
    )

    # Описание библиотек
    libs_text = " ".join(
        f"• [{LIBRARY_COLORS.get(lib, 'white')}]{lib}[/]"
        for lib in libraries
    )

    info = Panel.fit(
        f"[b]Welcome to SpaceWorld Benchmark![/b]\n\n"
        f"[b]Test Scenarios:[/b]\n{scenarios_text}\n\n"
        f"[b]Libraries:[/b]\n{libs_text}\n\n"
        f"[b]Metrics:[/b]\n"
        "• ⏱️ Execution time\n"
        "• 🧠 Memory usage\n"
        "• 🔍 Function profiling",
        title="[green]Test Configuration[/]",
        border_style="green"
    )

    console.print(Columns([rocket, info], padding=2))
    console.print(Rule(style="blue"))


def get_complexity_color(complexity: str) -> str:
    """Возвращает цвет для уровня сложности"""
    return {
        'simple': 'green',
        'medium': 'yellow',
        'complex': 'red'
    }.get(complexity, 'white')


def setup_click() -> Any:
    """Настройка Click"""

    @click.group()
    def cli():
        pass

    @cli.command()
    @click.argument('num', type=int)
    def hello(num):
        pass

    @cli.command()
    @click.argument('num', type=int)
    @click.option('--verbose', is_flag=True)
    def subcmd(num, verbose):
        pass

    @cli.command()
    @click.argument('value', type=int)
    @click.option('--min', type=int, default=0)
    @click.option('--max', type=int, default=100)
    @click.option('--name', type=str)
    def validate(value, min, max, name):
        pass

    return cli


def setup_typer() -> Any:
    """Настройка Typer"""
    app = typer.Typer()

    @app.command()
    def hello(num: int):
        pass

    @app.command()
    def subcmd(num: int, verbose: bool = False):
        pass

    @app.command()
    def validate(
            value: int,
            min_val: int = typer.Option(0, "--min"),
            max_val: int = typer.Option(100, "--max"),
            name: str = typer.Option("", "--name")
    ):
        pass

    return app


def setup_spaceworld() -> Any:
    """Настройка SpaceWorld"""
    app = spaceworld.SpaceWorld()

    @app.command()
    def hello(num: int):
        pass

    @app.command()
    def subcmd(num: int, verbose: bool = False):
        pass

    @app.command()
    def validate(
            value: int,
            min: int = 0,
            max: int = 100,
            name: str = ""
    ):
        pass

    return app


def setup_argparse() -> Any:
    """Настройка argparse"""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Команда hello
    hello_parser = subparsers.add_parser('hello')
    hello_parser.add_argument('num', type=int)

    # Команда subcmd
    subcmd_parser = subparsers.add_parser('subcmd')
    subcmd_parser.add_argument('num', type=int)
    subcmd_parser.add_argument('--verbose', action='store_true')

    # Команда validate
    validate_parser = subparsers.add_parser('validate')
    validate_parser.add_argument('value', type=int)
    validate_parser.add_argument('--min', type=int, default=0)
    validate_parser.add_argument('--max', type=int, default=100)
    validate_parser.add_argument('--name', type=str, default="")

    return parser


def setup_fire() -> Any:
    """Настройка Fire"""

    class FireApp:
        def hello(self, num: int):
            pass

        def subcmd(self, num: int, verbose: bool = False):
            pass

        def validate(
                self,
                value: int,
                min: int = 0,
                max: int = 100,
                name: str = ""
        ):
            pass

    return FireApp()


def execute_click(cli: Any, command: str) -> None:
    """Выполнение команды Click"""
    with mock_argv(["cli", *command.split()]):
        cli(standalone_mode=False)


def execute_typer(app: Any, command: str) -> None:
    """Выполнение команды Typer"""
    with mock_argv(["cli", *command.split()]):
        try:
            app()
        except SystemExit:
            pass


def execute_spaceworld(cns: Any, command: str) -> None:
    """Выполнение команды SpaceWorld"""
    with mock_argv(["cli", *command.split()]):
        try:
            cns()
        except SystemExit:
            pass


def execute_argparse(parser: Any, command: str) -> None:
    """Выполнение команды argparse"""
    with mock_argv(["cli", *command.split()]):
        parser.parse_args()


def execute_fire(FireApp: Any, command: str) -> None:
    """Выполнение команды Fire"""
    with mock_argv(["cli", *command.split()]):
        try:
            fire.Fire(FireApp)
        except SystemExit:
            pass


def setup_cloup() -> Any:
    """Настройка Cloup"""

    @cloup.group()
    def cli():
        pass

    @cli.command()
    @cloup.argument('num', type=int)
    def hello(num):
        pass

    @cli.command()
    @cloup.argument('num', type=int)
    @cloup.option('--verbose', is_flag=True)
    def subcmd(num, verbose):
        pass

    @cli.command()
    @cloup.argument('value', type=int)
    @cloup.option('--min', type=int, default=0)
    @cloup.option('--max', type=int, default=100)
    @cloup.option('--name', type=str)
    def validate(value, min, max, name):
        pass

    return cli


def execute_cloup(cli: Any, command: str) -> None:
    """Выполнение команды Cloup"""
    with mock_argv(["cli", *command.split()]):
        try:
            cli.main()
        except SystemExit:
            pass


@contextmanager
def mock_argv(args: List[str]):
    """Контекстный менеджер для подмены sys.argv"""
    original = sys.argv
    sys.argv = args
    try:
        yield
    finally:
        sys.argv = original


def main():
    """Основная функция"""
    try:
        # Инициализация тестера
        runner = BenchmarkRunner()

        # Добавление библиотек
        runner.add_library(BenchmarkLibrary(
            "spaceworld",
            setup_spaceworld,
            execute_spaceworld
        ))
        runner.add_library(BenchmarkLibrary(
            "argparse",
            setup_argparse,
            execute_argparse
        ))

        runner.add_library(BenchmarkLibrary(
            "click",
            setup_click,
            execute_click
        ))
        runner.add_library(BenchmarkLibrary(
            "typer",
            setup_typer,
            execute_typer
        ))

        runner.add_library(BenchmarkLibrary(
            "cloup",
            setup_cloup,
            execute_cloup
        ))
        runner.add_library(BenchmarkLibrary(
            "fire",
            setup_fire,
            execute_fire
        ))
        # Настройка параметров
        runner.config.update({
            'runs': 1,
            'warmup': 1,
            'memory': True,
            'profile': False
        })

        # Показать приветствие
        print_welcome(runner.scenarios, set(runner.libraries.keys()))

        # Запуск тестов
        runner.run_benchmarks()

        # Вывод результатов
        runner.print_results()

        # Сохранение результатов
        # runner.save_results()

    except Exception as e:
        console.print(f"\n[red]Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
