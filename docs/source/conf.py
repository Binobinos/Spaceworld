import os
import sys
from datetime import datetime

# Пути и настройки импорта
sys.path.insert(0, os.path.abspath('../..'))  # Путь к корню проекта

# -- Основные расширения ----------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',  # Автодокументирование Python кода
    'sphinx.ext.viewcode',  # Ссылки на исходный код
    'sphinx.ext.napoleon',  # Поддержка Google/Numpy стиля docstrings
    'sphinx.ext.autosummary',  # Авто-оглавления
    'sphinx.ext.intersphinx',  # Ссылки между документациями
    'sphinx.ext.coverage',  # Проверка покрытия документации
    'sphinx.ext.mathjax',  # Поддержка математических формул
    'sphinx_autodoc_typehints',  # Красивое отображение аннотаций типов
]

# -- Настройки проекта ------------------------------------------------------
project = 'SpaceWorld'
copyright = f'{datetime.now().year}, binobinos'
author = 'binobinos'
release = '0.1.0'
version = '0.1'

# -- Настройки autodoc ------------------------------------------------------
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__, __call__',
    'undoc-members': True,
    'exclude-members': '__weakref__, __dict__, __module__',
    'show-inheritance': True,
}

autodoc_typehints = 'description'
autodoc_typehints_description_target = 'documented'
autodoc_mock_imports = []  # Для внешних зависимостей

# -- Настройки Napoleon (Google/Numpy docstrings) ---------------------------
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = False
napoleon_use_keyword = True
napoleon_preprocess_types = True

# -- Настройки Intersphinx --------------------------------------------------
intersphinx_mapping = {}

# -- Общие настройки --------------------------------------------------------
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
source_suffix = '.rst'
master_doc = 'index'
language = 'en'
pygments_style = 'sphinx'

# -- Настройки HTML вывода --------------------------------------------------
html_theme = 'furo'  # Альтернативы: 'sphinx_rtd_theme', 'pydata_sphinx_theme'
html_static_path = ['_static']
html_logo = '_static/logo.png'  # Путь к логотипу (если есть)
html_favicon = '_static/favicon.ico'  # Путь к фавиконке
html_show_sourcelink = True
html_show_sphinx = False
html_show_copyright = True

# -- Настройки для PDF/LaTeX вывода -----------------------------------------
latex_elements = {
    'papersize': 'a4paper',
    'pointsize': '10pt',
    'figure_align': 'htbp',
}
latex_documents = [
    (master_doc, 'SpaceWorld.tex', 'SpaceWorld Documentation',
     author, 'manual'),
]

# -- Дополнительные настройки -----------------------------------------------
add_module_names = False  # Убирает имена модулей из заголовков
autosummary_generate = True  # Автогенерация summary
coverage_show_missing_items = True  # Показывает недостающую документацию
# Добавьте в конец conf.py:
html_css_files = [
    'custom.css',
]

html_js_files = [
    'custom.js',
]

# Для лучшего отображения типов
always_document_param_types = True
typehints_fully_qualified = False

html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_depth": 4,
    "source_repository": "https://github.com/your/repo",
    "source_branch": "main",
    "source_directory": "docs/",
}

