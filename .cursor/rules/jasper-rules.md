---
description: Conventions for JasperReports (.jrxml) template authoring and edits
globs: "**/*.jrxml"
alwaysApply: false
---

# JasperReports template rules

These rules apply when creating or editing **JasperReports** templates (`.jrxml`).

**Source of truth split (mandatory):**

| Concern | Authoritative source |
|--------|----------------------|
| **Layout** — sections, labels, band set, group structure, field placement, page flow, subreport split (cover vs detail, etc.) | **Functional specification** (`functional_spec/*.md`; default `Invoice_Functional_Template.md`. Regenerate from `.docx` via `scripts/docx_spec_to_md.py` when Word is edited.) |
| **Technical house style** — parameter names (`P_` prefix), field `SNAKE_CASE`, variable names, `<style>` definitions, number/date patterns, types, query parameterization, resource path parameters | **Sample templates** (`sample_template/`) — **reference only** |

Do **not** copy band positions, group lists, or section content from sample templates when they differ from the functional spec. Samples are not layout blueprints.

---

## 1. Structure and validity

- Produce **well-formed XML** compatible with JasperReports JRXML schema; keep the root `jasperReport` namespace and version consistent with sibling templates in the project when available.
- Prefer **one concern per subreport**: main report for layout shell; repeating sections (line items, nested lists) in **subreports** with clear parameter passing.
- Use **parameters** for runtime values (paths, tenant, locale, report title); use **fields** for query/bean data rows. Do not hardcode environment-specific URLs, credentials, or file paths—use parameters or resource bundles.

---

## 2. Bands (dynamic — derived from the functional spec)

- **Do not hardcode a fixed band set.** The sub agent must **derive which bands are required from the functional specification** for the report being built, then create only those bands with appropriate heights and content. Omit bands the spec does not need; add bands (e.g. `background`, `title`, `pageHeader`, `columnHeader`, `detail`, `columnFooter`, `pageFooter`, `lastPageFooter`, `summary`, `noData`) only when the spec or layout logic requires them.
- Use these semantics when a band is included:
  - **Title / background**: one-time branding or document shell (optional if duplicated elsewhere).
  - **Page header**: page-level headers that repeat each page only when `printWhenExpression` / report property requires it.
  - **Column header**: table column labels for tabular detail.
  - **Detail**: one row per data record; keep logic simple; heavy grouping belongs in **group headers/footers** or variables.
  - **Summary**: totals, taxes, grand totals, legal/footer blocks that apply once at end of report; **all subreports must be invoked from the summary band** (not from detail, group footer, or page header). Pass parameters and data sources explicitly from the main report.
- **No page header** for content that should appear only once unless the spec explicitly requires repetition.
- If band placement is ambiguous in the spec, **call it out** and keep the band set minimal.

---

## 3. Report groups (dynamic, decided by the sub agent from the functional spec)

- **Do not hardcode a fixed group list.** The sub agent must **derive the groups from the functional specification** for the report being built, then create matching `<group>` elements with the appropriate group header/footer bands and reset variables (`resetType="Group"`, `resetGroup="..."`, `calculation="Sum"`).
- Name each group after the concern it represents; use sample group naming **style** (e.g. `Invoice Total`, `Detail Type`) only when it matches a spec-driven grouping—do not import sample groups that the spec does not need.
- Map spec sections (H1, H2, D1, F1, etc.) to bands and groups explicitly; do not mirror the sample template’s group/band diagram.
- For each group that produces a subtotal, define a `Sum` variable reset to that group and surface it in the group footer (or summary band for grand totals), following the band rules above.
- If the spec does not require a particular grouping, **omit it**—keep the group set minimal and driven strictly by the spec. When a grouping choice is ambiguous, call it out.

---

## 4. Naming and data contract (from samples; layout from spec)

- **Parameters:** use the `P_` prefix and names from sample templates where applicable (e.g. `P_TRANS_ID`, `P_SIGNATURE`, `TEMPLATE_FILE_DIRECTORY`, `REPORT_CONNECTION`). Add spec-only parameters with the same `P_` convention.
- **Fields:** `SNAKE_CASE` matching the sample query/view columns (e.g. `DOCUMENT_TYPE`, `FRN_NAME`, `NET_AMOUNT`).
- **Variables:** reuse sample variable **names and reset patterns** when the same aggregation applies; create new variables only when the spec requires a total or flag not covered by samples.
- **Styles:** reuse sample `<style>` elements (e.g. `Alternate Row Colour`) and the same font/pattern conventions (`Calibri`, `#,##0.00;-#,##0.00`, `dd-MMM-yyyy`) unless the spec mandates otherwise.
- Document **required parameters** in comments at the top of the JRXML.
- Align **types** with the data source (e.g. `java.math.BigDecimal` for money fields; `java.lang.Double` for sum variables per samples).

---

## 5. Styling and assets

- Reference images/fonts with **parameterized or relative paths** consistent with deployment (e.g. classpath resource vs. filesystem).
- Reuse **styles** (`style` elements) for fonts, borders, and padding instead of duplicating properties on every element when possible.

---

## 6. Output files (derived from the functional spec — never hardcode)

Do **not** hardcode `.jrxml` file names in rules, agents, or generators. Derive them from the **active functional spec** (the `.md` read for the current run).

**Resolution order** (same as `scripts/parse_spec_outputs.py`):

1. **Explicit table (preferred)** — If the spec contains an **Output files** / **JRXML output** table listing `.jrxml` filenames (columns such as File, Jasper name attribute, Role), use those names exactly. Set each root `jasperReport` `name` to the listed Jasper name (filename stem if omitted).
2. **Template title + page table (default)** — Parse the template title from the spec (first `**… Template**` or `# … Template` heading, e.g. *National Invoice Usage Template* → `national_invoice_usage`). For each row in the spec’s **Page** table (`| Page | Description |`), build `{base}_{role}.jrxml`:
   - Cover page → `{base}_main.jrxml` (main report / subreport host)
   - Detail page → `{base}_detail.jrxml` (detail subreport; compile to `.jasper`)
   - Other page labels → `{base}_{page_snake}.jrxml` (page name lowercased, spaces → `_`, trailing ` page` dropped)
3. **Spec filename fallback** — If no title: take the spec stem (e.g. `Invoice_Functional_Template`), strip `_Functional_Template`, `_Functional`, or `_Template`, convert to `snake_case`, then apply page suffixes as in step 2.

**Subreport wiring:** The main report’s `subreportExpression` must reference the detail output stem from the spec, e.g. `$P{TEMPLATE_FILE_DIRECTORY} + "<detail_stem>.jasper"` — never a hardcoded project-specific name.

**Before authoring or writing output**, resolve names:

```powershell
.venv\Scripts\python.exe scripts\parse_spec_outputs.py functional_spec\<SPEC>.md
```

Write files to `output/` using the resolved `file` values. If the spec is ambiguous (no table, no title, no page table), **call it out** and ask before inventing names.

**Example** (from `Invoice_Functional_Template.md` — title *National Invoice Usage Template*, Cover + Detail pages):

| File | Jasper `name` | Role |
|------|---------------|------|
| `national_invoice_usage_main.jrxml` | `national_invoice_usage_main` | Cover page — headers, traffic summary, footers, subreport host |
| `national_invoice_usage_detail.jrxml` | `national_invoice_usage_detail` | Detail page — line-level traffic; compiled to `.jasper` for subreport load |

---

## 7. Platform and XML

| Requirement | Value |
|-------------|-------|
| Schema | `http://jasperreports.sourceforge.net/jasperreports` + `jasperreport.xsd` |
| Page size | A4: 595 × 842 pt; column width 555; margins 20 pt |
| Encoding | UTF-8; `ireport.encoding` = UTF-8 |
| Scripting | Groovy-compatible expressions (project default; no JR 6-only features) |
| UUIDs | Every `reportElement` has unique `uuid` in 8-4-4-4-12 hex form |
| Layout attributes | `x`, `y`, `width`, `height`, `uuid`, `style`, `printWhenExpression` on `<reportElement>` only — not on `textField`, `staticText`, `image`, `line`, `rectangle`, or `subreport`. Attributes on the parent element cause `cvc-complex-type.3.2.2` schema errors in iReport 5.6.0. |
| Band sections | At most one `<band>` per section (`title`, `pageHeader`, `columnHeader`, `detail`, `pageFooter`, `lastPageFooter`, `summary`, etc.); stack rows with `y` offsets inside a single band |
| Band order (after all `<group>`) | `background` → `title` → `pageHeader` → `columnHeader` → `detail` → `columnFooter` → `pageFooter` → `lastPageFooter` → `summary` → `noData` (omit unused sections; never place `background` after `detail`/`lastPageFooter` — iReport error: invalid content starting with `background`) |
| Duplicates | Each parameter, field, variable, and group name once per file; duplicates cause `Duplicate declaration of parameter` (or field/variable) at load time |
| Built-in parameters | Do not declare `REPORT_CONNECTION`, `REPORT_DATA_SOURCE`, `REPORT_LOCALE`, `IS_IGNORE_PAGINATION`, etc. — iReport injects them automatically. Use `$P{REPORT_CONNECTION}` only in `connectionExpression`; see `scripts/validate_jrxml.py` |
| Sample parameter set | Main reports: typically `P_TRANS_ID` (+ spec-specific `P_*` and `TEMPLATE_FILE_DIRECTORY`) only. Detail subreports: `REPORT_CONNECTOR` **only if** the sample subreport does — never duplicate `REPORT_CONNECTION` |
| Validation | Before finishing generated templates, run: `.venv\Scripts\python.exe scripts\validate_jrxml.py output\` |

---

## 8. Agent output expectations

- When changing a report, return the **complete updated `.jrxml`** (or clearly separated files if adding subreports), not a fragment, unless the user explicitly asked for a snippet.
- After non-trivial layout changes, note **what to verify in Jaspersoft Studio** (margins, overflow, band height, subreport alignment).
- If requirements conflict with an existing sample, **call out the conflict** and follow the user’s stated priority.
- The template shall be compatible with iReport 5.6.0.
