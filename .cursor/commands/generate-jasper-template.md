# generate-jasper-template

Generate a JasperReports `.jrxml` template from a functional specification, following the project rules and sample **technical** conventions only.

Steps:

1. **Locate the spec** in `functional_spec/`. Default pair: **`Invoice_Functional_Template.docx`** / **`Invoice_Functional_Template.md`**. If more than one spec exists and the user did not name one, ask which to use.

2. **Convert `.docx` → `.md` (required before authoring).** Run this **before** reading the spec or calling the subagent when **any** of the following is true:

   - The paired **`.md` file is missing**
   - The **`.docx` is newer** than the `.md` (compare last-modified times)
   - The user referenced or edited the **`.docx`**
   - The user did not specify a spec and the default `.docx` exists

   ```powershell
   .venv\Scripts\python.exe scripts\docx_spec_to_md.py functional_spec\<SPEC>.docx
   ```

   Default:

   ```powershell
   .venv\Scripts\python.exe scripts\docx_spec_to_md.py functional_spec\Invoice_Functional_Template.docx
   ```

   If conversion fails (e.g. *Permission denied*), ask the user to close Word and retry. **Do not** proceed to template generation until a current `.md` exists.

3. **Read the spec.** Open the generated `.md` file in full. Use its layout tables, business rules, data-source SQL, groups, variables, parameters, and **output file names** as the blueprint. **Do not** read `.docx` directly or use raw zip/XML extraction.

   **Resolve output names** before authoring (rules §6):

   ```powershell
   .venv\Scripts\python.exe scripts\parse_spec_outputs.py functional_spec\<SPEC>.md
   ```

   Use the JSON `outputs[].file` and `outputs[].jasper_name` for paths, `jasperReport name`, and subreport `.jasper` references — never hardcode template-specific filenames.

4. **Study house style (samples = naming only).** Read `.cursor/rules/jasper-rules.md` and both files in `sample_template/` (`standard_template_voice.jrxml`, `standard_voice_detail_page.jrxml`). Adopt namespace/version, `P_` parameters, `SNAKE_CASE` fields, variable naming, `<style>` elements, `BigDecimal`/`Double` types, `#,##0.00;-#,##0.00`, `dd-MMM-yyyy`, and parameterized resource paths. **Do not copy sample band/group layout** — that comes from the spec.

5. **Author the template.** Delegate to the **`jasper-report-author`** subagent. Pass the `.md` spec path **and the resolved output file list** from step 3. Layout (sections, bands, groups, labels, columns, subreports) must match the functional spec. Document required parameters in a header comment; call out spec vs sample conflicts.

6. **Write the output.** Save to `output/` (create if missing) using the **spec-derived** `.jrxml` names from step 3. Do not modify `sample_template/` or `functional_spec/`.

7. **Verify and report.** Run `.venv\Scripts\python.exe scripts\validate_jrxml.py output\` (duplicates, built-in params, layout attrs on `reportElement`, UUIDs). Confirm well-formed XML; list resolved output files, iReport checks (margins, band heights, overflow, `printWhenExpression`, formatting, subreport alignment in summary band).
