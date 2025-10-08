# Installation

## TL;DR

```bash
pip install hilt
```

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install via pip](#install-via-pip)
3. [Install via Poetry](#install-via-poetry)
4. [Install from Source](#install-from-source)
5. [Optional Dependencies](#optional-dependencies)

## Prerequisites

- Python ≥ 3.10
- Recommended: virtual environment (venv, Poetry, or Conda)

## Install via pip

```bash
python -m pip install --upgrade pip
pip install hilt
```

## Install via Poetry

```bash
poetry add hilt
```

To include optional extras:

```bash
poetry add "hilt[parquet,langchain]"
```

## Install from Source

```bash
git clone https://github.com/hilt-format/hilt-python.git
cd hilt-python
poetry install
```

or with pip:

```bash
pip install -e .
```

## Optional Dependencies

HILT ships with extras for ecosystem integrations:

| Extra        | Packages              | Purpose                        |
|--------------|-----------------------|--------------------------------|
| `parquet`    | `pyarrow`             | Parquet conversion             |
| `langchain`  | `langchain`           | LangChain callback handler     |

Install via:

```bash
pip install "hilt[parquet,langchain]"
```

Refer to [Integrations](integrations.md) for usage examples.
