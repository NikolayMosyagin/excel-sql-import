# Import Excel

Инструмент для импорта данных из Excel-файлов (`.xls`, `.xlsx`) в Microsoft SQL Server на основе TOML-конфигурации.

## Основные возможности
- Импорт Excel-файлов форматов `.xls` и `.xlsx`;
- Выполнение нескольких импортов за один запуск;
- Режимы обновления данных: `replace`, `append`, `upsert`, `replace_by_columns`;
- Сопоставление названий колонок Excel с колонками SQL-таблицы;
- Преобразование строковых дат с помощью `date_formats`;
- Проверка структуры Excel-файлов и SQL-таблиц перед импортом;
- Выполнение всех импортов одного запуска в единой транзакции;
- Ручной запуск и запуск в scheduled-режиме;
- Логирование в scheduled-режиме;
- Поддержка относительных и абсолютных путей;
- Запуск как Python-приложения, так и собранного `.exe`.

## Требования
- Python 3.11+
- Microsoft SQL Server
- доступ к целевой базе данных

Основные зависимости проекта перечислены в `requirements.txt`:
- `pandas`
- `openpyxl`
- `xlrd`
- `python-dotenv`
- `mssql-python`

Зависимости, необходимые для разработки, тестирования и сборки приложения, перечислены в `requirements-dev.txt`: 
- `pytest`
- `pyinstaller`

## Установка из исходников
Скачайте проект из GitHub:

```powershell
git clone https://github.com/NikolayMosyagin/excel-sql-import.git
cd excel-sql-import
```

Создайте и активируйте виртуальное окружение:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установите зависимости приложения:

```powershell
pip install -r requirements.txt
```

Для разработки, запуска тестов и сборки `.exe` дополнительно установите зависимости из `requirements-dev.txt`

```powershell
pip install -r requirements-dev.txt
```

## Подключение к SQL Server

Для подключения к SQL Server необходимо создать файл `.env`:
- При запуске из исходников файл должен лежать в корне проекта
- При запуске собранного приложения - рядом с `.exe`

В файле `.env` задается строка подключения к SQL Server:

`SQL_CONNECTION_STRING=<SQL Server connection string>`

Для запуска integration и E2E тестов дополнительно используется отдельная переменная:

`TEST_SQL_CONNECTION_STRING=<test SQL Server connection string>`

`TEST_SQL_CONNECTION_STRING` должна указывать на отдельную тестовую базу данных.

Файл .env может содержать данные для доступа к базе данных и не должен добавляться в Git.

## Конфигурация

Для описания импортов одного запуска используется TOML-файл.
Каждая секция `[[imports]]` описывает один импорт.  
Пример конфигурации:
```toml
[[imports]]
name = "Products"
file = "data/products.xlsx"
sheet = "Products"
schema = "dbo"
table = "Products"
mode = "append"
```
| Параметр | Обязательный | Описание |
|---|---|---|
| `name` | Да | Название импорта |
| `file` | Да | Путь к Excel-файлу |
| `sheet` | Да | Название листа в Excel-файле |
| `schema` | Да | Схема целевой таблицы в SQL Server |
| `table` | Да  | Имя целевой таблицы в SQL Server |
| `mode` | Нет | Режим импорта. По умолчанию — `replace` |
| `key_columns` | Для `upsert` | Колонки, определяющие ключ строки при обновлении данных |
| `replace_columns` | Для `replace_by_columns` | Колонки, определяющие группы строк для замены |
| `column_mapping` | Нет | Сопоставление названий колонок Excel с колонками SQL |
| `date_formats` | Нет | Форматы строковых дат |

### Режимы импорта
#### `replace`
Полностью очищает целевую таблицу и записывает данные из Excel-файла. Если параметр `mode` не указан, используется режим `replace`.
```toml
mode = "replace"
```
#### `append ` 
Добавляет данные из Excel-файла в целевую таблицу, сохраняя уже существующие строки.
```toml
mode = "append"
```
#### `upsert`  
Сопоставляет строки Excel с существующими строками целевой таблицы по колонкам, указанным в `key_columns`. Если строка с таким ключом уже существует, её данные обновляются. Если строки нет — она добавляется.
```toml
mode = "upsert"
key_columns = ["ProductID"]
```
Можно использовать составной ключ:
```toml
mode = "upsert"
key_columns = ["ProductID", "WarehouseID"]
```
Колонки из `key_columns` не должны содержать пустые значения. Комбинация ключевых значений должна однозначно определять строку.

#### `replace_by_columns`  
Перед импортом удаляет из целевой таблицы строки, значения которых совпадают с уникальными комбинациями колонок, указанных в `replace_columns`. После этого все данные из Excel-файла добавляются в целевую таблицу.  
Например:
```toml
mode = "replace_by_columns"
replace_columns = ["ReportDate"]
```
Для нескольких колонок: 
```toml
mode = "replace_by_columns"
replace_columns = ["ReportDate", "DepartmentID"]
```
Колонки из `replace_columns` не должны содержать пустые значения.

### Сопоставление колонок
`column_mapping` используется, если названия колонок в Excel отличаются от названий колонок целевой SQL-таблицы.  
Например, Excel-файл имеет колонки: `Код товара | Наименование`, а SQL-таблица: `ProductID | Name`.
Тогда в конфигурации импорта необходимо указать:
```toml
[imports.column_mapping]
"Код товара" = "ProductID"
"Наименование" = "Name"
```
В `column_mapping` ключ — название колонки в Excel, значение — название соответствующей колонки в SQL-таблице.
### Форматы дат
`date_formats` используется, когда Excel-файл содержит даты в виде строк определённого формата. **Ключ** - наименование колонки, **значение** - формат даты.  
Например, для значений вида `16.10.2025`:
```toml
[imports.date_formats]
DocumentDate = "%d.%m.%Y"
```
Основные популярные обозначения:
- %d - день
- %m - месяц
- %Y - год из четырёх цифр
- %H - часы
- %M - минуты
- %S - секунды
### Несколько импортов
Один конфигурационный файл может содержать несколько секций `[[imports]]`. Каждая секция описывает отдельный импорт. В одном запуске можно использовать как разные Excel-файлы, так и разные листы одного файла.  
Пример:
```toml
[[imports]]
name = "Products"
file = "data.xlsx"
sheet = "Products"
schema = "dbo"
table = "Products"
mode = "append"

[[imports]]
name = "Categories"
file = "data.xlsx"
sheet = "Categories"
schema = "dbo"
table = "Categories"
mode = "append"
```
Перед записью данных приложение проверяет все импорты. После успешной валидации изменения в SQL Server выполняются в одной транзакции. Если во время записи одного из импортов возникает ошибка, изменения всех уже выполненных импортов этого запуска откатываются.
## Пути к файлам
Для файла конфигурации и Excel-файлов можно использовать как относительные, так и абсолютные пути.
### Путь к конфигурации
Если путь передан через `--config` или `-c`, относительный путь определяется относительно текущей рабочей директории. Например:  
```powershell
ImportExcel.exe --config "configs\test.toml"
```
Если команда запущена из: `C:\ImportExcel` будет использован файл: `C:\ImportExcel\configs\test.toml`  
Можно указать абсолютный путь:  
```powershell
ImportExcel.exe --config "C:\ImportExcel\configs\test.toml"
``` 
Если параметр `--config` не указан, используется конфигурация по умолчанию: `config\imports.toml`

### Пути к Excel-файлам
Путь, указанный в параметре `file` внутри TOML-конфигурации, определяется относительно директории самого файла конфигурации.  
Например, при структуре:
```
C:\ImportConfigs\  
├── imports.toml 
└── data\ 
    └── products.xlsx
```
в `imports.toml` можно указать:  
```toml
file = "data/products.xlsx"
```
и приложение будет использовать файл:
`C:\ImportConfigs\data\products.xlsx`  
Можно также указать абсолютный путь:
```toml
file = "C:/ImportData/products.xlsx"
```
## Запуск
Запустить данное приложение можно как с исходников, используя стандартную конфигурацию:
```powershell
python -m src.import_excel
```
или используя `.exe`:
```powershell
.\ImportExcel.exe
```
Для использования другого файла конфигурации укажите параметр `--config` или его сокращенную форму `-c`:
```powershell
.\ImportExcel.exe --config "C:\ImportConfigs\report.toml"
```
Также доступен запуск в `scheduled`-режиме:
```powershell
.\ImportExcel.exe --config "C:\ImportConfigs\report.toml" --scheduled
```
### Scheduled-режим
В `scheduled`-режиме исходные Excel-файлы перед обработкой перемещаются в:  
`processing/<run_id>`  
После успешного завершения импорта каталог запуска переносится в:  
`processed/<run_id>`  
Лог выполнения сохраняется в:  
`logs/import_<run_id>.log`  
Каталоги `processing`, `processed` и `logs` создаются рядом с используемым TOML-файлом конфигурации. Если ошибка возникает после перемещения файлов, архивирование в `processed` уже не выполняется, поэтому файлы остаются в `processing/<run_id>`.

## Валидация
Перед записью данных в SQL Server приложение проверяет:
- наличие исходных файлов;
- расширение Excel;
- существование указанного листа;
- наличие данных;
- существование целевой SQL-таблицы;
- соответствие колонок Excel целевым колонкам;
- типы данных;
- корректность конфигурации импорта;
- корректность настроек `key_columns`, `replace_columns` и `date_formats`.  
Если ошибка возникает во время записи данных, изменения текущей SQL-транзакции откатываются.
## Тесты
Для запуска всех тестов:
```powershell
python -m pytest
```
Integration- и E2E-тесты используют реальный SQL Server и требуют переменную окружения:  
`TEST_SQL_CONNECTION_STRING=<test SQL Server connection string>`  
Для integration- и E2E-тестов необходимо использовать отдельную тестовую базу данных.

## Сборка EXE
Для сборки приложения используется PowerShell-скрипт `build.ps1`, который запускает PyInstaller с конфигурацией из `ImportExcel.spec`. Запустите скрипт из корня проекта:  
```powershell
.\build.ps1
```
Файл `ImportExcel.spec` содержит параметры сборки приложения и хранится в репозитории вместе с `build.ps1`.

## Структура проекта
```
ImportExcel/
├── config/
│   └── imports.toml
├── src/
│   ├── import_excel.py
│   ├── config_loader.py
│   ├── excel_utils.py
│   ├── sql_data_import.py
│   └── ...
├── tests/
│   ├── integration/
│   └── e2e/
├── build.ps1
├── ImportExcel.spec
├── requirements.txt
├── requirements-dev.txt
└── README.md
```
Папка `src/` содержит основную логику приложения, `tests/` — unit, integration и E2E-тесты.
