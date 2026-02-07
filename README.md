# wee - High-Performance Jinja2 → HTML → WeasyPrint → PDF Renderer

A fast CLI tool for rendering Jinja2 templates to PDF with instant hot-reload capabilities.

Built for developers who need to quickly prototype and iterate on PDF templates.

**Note:** This script uses PEP 723 inline script metadata for dependency management.

## Features

- Near-instant hot-reloads with optimized file watching (100ms debounce)
- Template environment folder support for template extending
- External context.json file monitoring with automatic reloading
- High-performance caching with Jinja2 template caching
- Professional CLI interface with comprehensive help system
- Configurable performance settings (debounce timing, etc.)
- Cross-platform support with automatic PDF opening

## Installation

This script declares its dependencies inline using PEP 723. You have several options:

### Option 1: Traditional pip (Manual)

```bash
pip install jinja2 weasyprint watchdog
```

### Option 2: Using uv (Recommended - Automatic)

If you have [uv](https://github.com/astral-sh/uv) installed:

```bash
uv run wee.py
```

uv will automatically create an isolated environment and install dependencies.

### Option 3: Using pipx (Automatic)

```bash
pipx run wee.py
```

pipx will handle dependencies automatically in an isolated environment.

### WeasyPrint System Dependencies

WeasyPrint requires some system libraries. Install them based on your OS:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info
```

**macOS:**
```bash
brew install cairo pango gdk-pixbuf libffi
```

**Windows:**
WeasyPrint provides pre-built wheels, so usually `pip install weasyprint` is sufficient.

## Quick Start

### Show Help

```bash
uv run wee.py
```

### Basic Usage

```bash
# Render a template once
uv run wee.py -t template.html

# Use external context file
uv run wee.py -t template.html -c context.json

# Use template directory for extending
uv run wee.py -t template.html -d templates/

# Watch for changes with hot-reload
uv run wee.py -t template.html -w

# Full example with all features
uv run wee.py -t invoice.html -d templates/ -c data.json -w -o invoice.pdf
```

## Command Line Options

```
usage: wee [-h] [-t TEMPLATE] [-d TEMPLATE_DIR] [-c CONTEXT] [-o OUTPUT] [-w] [--no-open] [--debounce DEBOUNCE]

High-performance Jinja2 template to PDF renderer with hot-reload

options:
  -h, --help            show this help message and exit
  -t, --template TEMPLATE
                        Template file to render
  -d, --template-dir TEMPLATE_DIR
                        Template directory for extending templates
  -c, --context CONTEXT
                        Context JSON file (monitored in watch mode)
  -o, --output OUTPUT   Output PDF file (default: output.pdf)
  -w, --watch           Watch for changes and auto-regenerate
  --no-open             Do not automatically open PDF after generation
  --debounce DEBOUNCE   Debounce time in milliseconds for file changes (default: 100)
```

## Advanced Features

### Template Extending

Create a base template in your templates directory:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f0f0f0; padding: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ title }}</h1>
    </div>
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

Then extend it in your main template:

```html
<!-- invoice.html -->
{% extends "base.html" %}

{% block content %}
<h2>Invoice Details</h2>
<p>{{ description }}</p>

<table>
    <tr><th>Item</th><th>Quantity</th><th>Price</th></tr>
    {% for item in items %}
    <tr>
        <td>{{ item.name }}</td>
        <td>{{ item.quantity }}</td>
        <td>${{ item.price }}</td>
    </tr>
    {% endfor %}
</table>
{% endblock %}
```

### External Context Files

Create a `context.json` file:

```json
{
  "title": "Professional Invoice",
  "date": "2026-02-07",
  "author": "Your Company",
  "description": "Monthly service invoice",
  "items": [
    {"name": "Web Development", "quantity": 40, "price": 150.00},
    {"name": "Design Services", "quantity": 20, "price": 100.00},
    {"name": "Hosting", "quantity": 1, "price": 50.00}
  ]
}
```

The context file is automatically monitored in watch mode and will trigger re-renders when changed.

### Performance Tuning

Adjust debounce timing for your workflow:

```bash
# Faster reloads (50ms debounce)
uv run wee.py -t template.html -w --debounce 50

# Slower but more stable (500ms debounce)
uv run wee.py -t template.html -w --debounce 500
```

## Development Workflow

### Recommended Setup

1. **Create your template structure:**
   ```
   project/
   ├── wee.py
   ├── templates/
   │   ├── base.html
   │   └── components/
   ├── context.json
   └── invoice.html
   ```

2. **Start development with watch mode:**
   ```bash
   uv run wee.py -t invoice.html -d templates/ -c context.json -w
   ```

3. **Edit files:**
   - Modify `invoice.html` for layout changes
   - Update `context.json` for data changes
   - Edit templates in `templates/` for reusable components

4. **Automatic hot-reload:**
   - Changes to any watched file trigger instant re-render
   - PDF opens automatically in your default viewer
   - HTML file saved for debugging

### Debugging

- Check the generated HTML file (e.g., `output.html`) to debug styling issues
- Use `--no-open` flag to prevent automatic PDF opening during debugging
- Adjust debounce timing if you experience too frequent re-renders

## Template Features

The renderer supports all Jinja2 features:

- **Variables:** `{{ variable }}`
- **Loops:** `{% for item in items %}`
- **Conditionals:** `{% if condition %}`
- **Template extending:** `{% extends "base.html" %}`
- **Blocks:** `{% block content %}`
- **Includes:** `{% include "partial.html" %}`
- **Filters:** `{{ items|length }}`, `{{ price|round(2) }}`
- **Macros:** `{% macro input(name) %}`
- **Inheritance:** Full template inheritance support

## Tips for PDF Templates

1. **Use watch mode for development**: Start with `python wee.py --watch` for instant feedback
2. **Use absolute units**: Use `px`, `pt`, `cm`, `mm` instead of relative units
3. **Page breaks**: Use CSS `page-break-before`, `page-break-after`, `page-break-inside`
4. **Margins**: Set page margins with `@page { margin: 2cm; }`
5. **Fonts**: Embed fonts or use web-safe fonts
6. **Test HTML first**: Check `output.html` to debug styling issues

## Performance Features

### Caching

- **Template caching:** Jinja2 templates are cached for fast re-rendering
- **Modification time checking:** Only re-renders when files actually change
- **Efficient file watching:** Monitors only relevant directories

### Debouncing

- **Default 100ms debounce:** Prevents excessive re-renders during rapid saves
- **Configurable timing:** Adjust based on your workflow needs
- **Smart filtering:** Only watches files that affect the output

## Examples

### Simple Report

```bash
uv run wee.py -t report.html -c report_data.json -w
```

### Invoice Generator

```bash
uv run wee.py -t invoice.html -d templates/ -c invoice_data.json -o client_invoice.pdf -w
```

### Documentation Generator

```bash
uv run wee.py -t docs.html -d templates/ -w --debounce 200 --no-open
```

## What is PEP 723?

This script uses [PEP 723](https://peps.python.org/pep-0723/) inline script metadata to declare its dependencies directly in the script file. This means:

- No separate `requirements.txt` needed
- Dependencies are documented in the script itself
- Works with modern tools like `uv` and `pipx` for automatic dependency installation
- Still works with traditional `pip install` if you prefer

## Troubleshooting

**"Watch mode requires 'watchdog' package":**
```bash
pip install watchdog
```

**Template not found:**
- Check file paths and current working directory
- Use absolute paths if needed
- Verify template directory structure

**Context file errors:**
- Ensure JSON is valid
- Check file permissions
- Verify file path is correct

**WeasyPrint errors:**
- Install system dependencies (see Installation section)
- Check CSS for unsupported features
- Validate HTML structure

**Performance issues:**
- Increase debounce timing: `--debounce 500`
- Check for large template files
- Monitor system resources