# Boilerplates Directory

This directory contains custom boilerplate templates for PyScaffold.

## Structure

Each boilerplate should be in its own subdirectory:

```
datasets/boilerplates/
├── sample-template/
│   ├── src/
│   │   └── main.py
│   ├── requirements.txt
│   └── README.md
├── django-template/
│   ├── manage.py
│   ├── requirements.txt
│   └── ...
└── custom-template/
    └── ...
```

## Usage

Boilerplates in this directory will be automatically detected by PyScaffold and can be used with the `--use-boilerplate` option.

## Creating Custom Boilerplates

1. Create a new directory with your template name
2. Add all the files and folders you want in your template
3. PyScaffold will copy the entire directory structure to the new project

## Example

```bash
# Use a custom boilerplate
python run.py create my-project --use-boilerplate sample-template
```