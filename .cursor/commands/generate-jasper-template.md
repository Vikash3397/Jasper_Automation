# generate-jasper-template

Orchestrate the full JasperReports generation pipeline by delegating to three agents **in sequence**:

1. **`jasper-spec-converter`** - Word `.docx` -> Markdown `.md`
2. **`jasper-spec-architect`** - resolve output names, verify the spec, design the layout (read-only)
3. **`jasper-report-author`** - author the `.jrxml` from the design

Do not skip or reorder these steps. Each agent's output feeds the next.

Steps:

1. **Locate the spec** in `functional_spec/`. Default pair: **`Invoice_Functional_Template.docx`** / **`Invoice_Functional_Template.md`**. If more than one spec exists and the user did not name one, ask which to use.

2. **Convert (delegate to `jasper-spec-converter`).** Pass the chosen `.docx`. The agent decides whether the `.md` is stale (missing, older than the `.docx`, or freshly edited) and runs `scripts/docx_spec_to_md.py`. If it reports *Permission denied*, ask the user to close Word and retry. **Do not proceed until a current `.md` exists.**

3. **Verify and design (delegate to `jasper-spec-architect`, read-only).** Pass the `.md` spec path. The agent:
   - resolves output names via `scripts/parse_spec_outputs.py` (rules §6) - `outputs[].file` and `outputs[].jasper_name`,
   - extracts formatting rules via `scripts/parse_spec_formatting.py` (General Instructions from the spec — not a hardcoded checklist),
   - verifies the spec is implementable (flagging BLOCKERs and AMBIGUITYs - e.g. fields used but not queried, conditional sections, TBD placeholders, unmapped format rules),
   - returns a **layout design** (outputs, global formatting table, per-report query/fields/groups, band map, subreport wiring, assumptions).

   If it reports BLOCKERs, resolve them with the user (or fix the `.docx` and re-run step 2 via `jasper-spec-converter`) before continuing.

4. **Author the template (delegate to `jasper-report-author`).** Pass the `.md` spec path, the resolved output file list from step 3, **and the layout design from step 3**. The author reads `.cursor/rules/jasper-rules.md` and the `sample_template/` files for technical house style (namespace/version, `P_` parameters, `SNAKE_CASE` fields, `<style>` elements, `BigDecimal`/`Double` types, `#,##0.00;-#,##0.00`, `dd-MMM-yyyy`, parameterized paths) and implements the design. Layout (sections, bands, groups, labels, columns, subreports) must match the design and the functional spec - never copy sample band/group layout. Document required parameters in a header comment; carry the design's assumptions and call out spec vs sample conflicts.

5. **Write the output.** Save to `output/` (create if missing) using the **spec-derived** `.jrxml` names from step 3. Do not modify `sample_template/` or `functional_spec/`.

6. **Verify and report.** Run `.venv\Scripts\python.exe scripts\validate_jrxml.py output\` (duplicates, built-in params, layout attrs on `reportElement`, UUIDs, field/expression consistency, subreport wiring). Confirm well-formed XML; list resolved output files, iReport checks (margins, band heights, overflow, `printWhenExpression`, formatting, subreport alignment in summary band).
