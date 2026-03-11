# Scripts

This folder is reserved for small local developer helpers.

Suggested bootstrap flow:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

cd web
npm install
```

Add scripts here only when they remove repeated local setup or data-prep work.
