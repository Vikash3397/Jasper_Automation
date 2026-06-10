# Functional specifications

Business-facing specs live here as Word documents; agents and pipelines consume the paired Markdown export.

## Formats

| Format | Audience | Use |
|--------|----------|-----|
| `.docx` | Business / review in Word | Author and edit the spec |
| `.md` | Agents, CI, pipelines | Generate Jasper templates |

Combined specs use two major parts: **Part 1 — Functional** (layout and business rules first), then **Part 2 — Technical** (JRXML, SQL, bands, validation).

## What the spec drives

From each `.md` spec, generators and agents derive:

- **Layout** — sections (H1, H2, D1, F1…), bands, groups, columns, business rules, SQL/views
- **Output file names** — `.jrxml` paths and `jasperReport` `name` attributes (via `parse_spec_outputs.py`)
- **Subreport wiring** — main report loads `{detail_stem}.jasper` from the resolved detail output name

Do not hardcode output filenames in scripts or rules; always resolve from the active spec.

## Converters

**Word → Markdown** (required before generation):

```powershell
.venv\Scripts\python.exe scripts\docx_spec_to_md.py functional_spec\Invoice_Functional_Template.docx
```

Output: `Invoice_Functional_Template.md` next to the `.docx` (or pass a second path for the `.md`).

Re-run when:

- The paired `.md` is missing
- The `.docx` is newer than the `.md`
- Word content was edited

**Markdown → Word** (for reviewers):

```powershell
.venv\Scripts\python.exe scripts\md_spec_to_docx.py functional_spec\Invoice_Functional_Template.md
```

Optional watch mode (reconvert on save):

```powershell
.venv\Scripts\python.exe scripts\docx_spec_to_md.py --watch functional_spec
```

Close Word if you see *Permission denied* when reading or writing files.

## Output file name resolution

Preview names before generating:

```powershell
.venv\Scripts\python.exe scripts\parse_spec_outputs.py functional_spec\Invoice_Functional_Template.md
```

| Priority | Source in spec | Result |
|----------|----------------|--------|
| 1 | **Output files** / **JRXML output** table with `.jrxml` filenames | Use listed names exactly |
| 2 | Template title (e.g. *National Invoice Usage Template*) + **Page** table | `{base}_main.jrxml` for Cover page, `{base}_detail.jrxml` for Detail page |
| 3 | Spec filename stem minus `_Functional_Template` | `snake_case` base + page suffixes |

Example for `Invoice_Functional_Template.md`:

| File | Jasper `name` |
|------|---------------|
| `national_invoice_usage_main.jrxml` | `national_invoice_usage_main` |
| `national_invoice_usage_detail.jrxml` | `national_invoice_usage_detail` |

To override defaults, add an explicit output table to the Word spec and re-run `docx_spec_to_md.py`.

## Suggested workflow

1. Edit **`Invoice_Functional_Template.docx`** in Word (or edit `.md` for git-friendly diffs).
2. Run **`docx_spec_to_md.py`** so the `.md` is current.
3. Run **`parse_spec_outputs.py`** to confirm output filenames.
4. Generate templates (`/generate-jasper-template` or `gen_national_invoice.py`) — files land in `output/`.
5. Run **`validate_jrxml.py output\`** before loading in iReport.
6. Commit `.docx` and `.md`, or commit `.md` only and regenerate from Word in CI.

Full pipeline details: [../README.md](../README.md).
