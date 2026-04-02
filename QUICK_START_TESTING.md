# Quick Start Guide - Testing Theme Upload & CLI

## Test 1: Web UI Theme Upload

### Step 1: Create a test theme ZIP file
```bash
# Create a test directory
mkdir -p /tmp/test-theme
cd /tmp/test-theme

# Create meta.json
cat > meta.json << 'EOF'
{
  "id": "my-test-theme",
  "name": "My Test Theme",
  "author": "Tester",
  "description": "A test theme for verification",
  "scenarios": ["letter", "article"]
}
EOF

# Create template.typ
cat > template.typ << 'EOF'
#let template(it) = {
  set page(number-align: center)
  it.body
}
EOF

# Create wrapper.typ.jinja
cat > wrapper.typ.jinja << 'EOF'
{%- set title = title | default("Document") -%}
{%- set author = author | default("Author") -%}

= {{ title }}

_by {{ author }}_

{{ content }}
EOF

# Create ZIP
zip -r test-theme.zip meta.json template.typ wrapper.typ.jinja
```

### Step 2: Run the web app
```bash
cd /workspaces/bubble-template-typst/app
source ../.venv/bin/activate  # if using venv
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Step 3: Test theme upload via HTTP
```bash
curl -F "theme_zip=@/tmp/test-theme/test-theme.zip" \
  http://localhost:8000/api/theme/upload
```

Expected response (200 OK):
```json
{
  "session_id": "uuid-here",
  "template": {
    "id": "custom-theme-...",
    "name": "My Test Theme",
    "author": "Tester",
    "description": "A test theme for verification",
    "scenarios": ["letter", "article"]
  }
}
```

---

## Test 2: CLI Theme Installation

### Step 1: List installed themes
```bash
cd /workspaces/bubble-template-typst
python3 app/cli.py list
```

Expected output:
```
📚 Installed themes in /workspaces/bubble-template-typst/app/templates_custom:
  • graceful-genetics (custom-graceful-genetics-c0df1549)
    A paper template with which to publish in journals and at conferences
```

### Step 2: Install a theme from GitHub (requires gh CLI)
First install gh CLI if needed:
```bash
# macOS
brew install gh

# Ubuntu/Debian  
sudo apt install gh

# Or visit: https://cli.github.com
```

Then authenticate:
```bash
gh auth login
```

Then install a theme:
```bash
cd /workspaces/bubble-template-typst
python3 app/cli.py install-github typst/packages
```

### Step 3: Install from local file
```bash
python3 app/cli.py install /tmp/test-theme/test-theme.zip
```

Expected output:
```
📝 Installing theme from test-theme.zip...
✅ Theme installed successfully!
   Name: My Test Theme
   ID: custom-theme-abc123
   Author: Tester
```

### Step 4: Verify it appears in the list
```bash
python3 app/cli.py list
```

The newly installed theme should now appear!

---

## Test 3: Verify Both Work Together

### In the same session, verify:

1. CLI-installed themes appear in Web UI:
```bash
# Install via CLI
python3 app/cli.py install /tmp/test-theme/test-theme.zip

# Query Web UI API
curl http://localhost:8000/api/templates | python3 -m json.tool | grep "my-test-theme"
```

2. Both types of themes (built-in, CLI-installed, Web-uploaded) work together:
```bash
curl http://localhost:8000/api/templates
```

Should show all three types of themes.

---

## Verification Checklist

- [ ] Web UI theme upload endpoint returns 200 OK
- [ ] Uploaded theme appears in template discovery
- [ ] CLI list command shows installed themes
- [ ] CLI install command succeeds
- [ ] Installed themes appear in Web UI discovery
- [ ] All three theme sources (built-in, CLI, Web UI) visible together

If all checkboxes pass, both features are working correctly!
