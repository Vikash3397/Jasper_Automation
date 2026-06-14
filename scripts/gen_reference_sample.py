#!/usr/bin/env python3
"""Emit the frozen National Invoice Usage reference templates.

NOTE: This is NOT a spec-driven generator. The layout (SQL, fields, bands,
groups, column positions) is hardcoded for the National Invoice Usage template;
only the OUTPUT FILE NAMES are derived from the spec via parse_spec_outputs.
It exists as a deterministic reference example. For any new or edited spec,
use the agent pipeline instead (`/generate-jasper-template`, which runs
jasper-spec-architect then jasper-report-author) so the layout tracks the spec.

Usage:
  .venv\\Scripts\\python.exe scripts/gen_reference_sample.py
  .venv\\Scripts\\python.exe scripts/gen_reference_sample.py functional_spec/Invoice_Functional_Template.md
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from parse_spec_outputs import DEFAULT_SPEC, derive_outputs  # noqa: E402

import uuid

OUT = ROOT / "output"


def uid():
    return str(uuid.uuid4())


ROOT_ATTR = (
    'xmlns="http://jasperreports.sourceforge.net/jasperreports" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xsi:schemaLocation="http://jasperreports.sourceforge.net/jasperreports '
    'http://jasperreports.sourceforge.net/xsd/jasperreport.xsd"'
)

def main_header(spec_path: Path) -> str:
    return f"""<!--
  Cover page (main report)
  Spec: {spec_path.as_posix()}
  Required parameters: P_TRANS_ID, P_SIGNATURE, TEMPLATE_FILE_DIRECTORY, P_CONTACT_USER, P_LOGO
  P_LOGO: full path to the branding logo image (default asset: sample_template/CSGI.jpg)
  Engine-provided (do not declare): REPORT_CONNECTION, REPORT_LOCALE, etc.
  Spec-only query fields (confirm in VW_DOCUMENT_TRANS_SUMMARY): FRN_TAX_REG_NO, OPR_TAX_REG_NO, OPR_CONTACT_NO, FRN_BANK_ACCOUNT_NAME
  Conflicts: Document labels Tax Invoice/Outbound Statement (spec) vs INVOICE/STATEMENT (sample).
  House style from sample_template/sample_invoice_main.jrxml and sample_invoice_detail.jrxml.
-->
"""


def detail_header(spec_path: Path) -> str:
    return f"""<!--
  Detail page (subreport)
  Spec: {spec_path.as_posix()}
  Required parameters: P_TRANS_ID, P_LOGO
  P_LOGO: full path to the branding logo image, passed from the main report (default asset: sample_template/CSGI.jpg)
  Engine-provided: REPORT_CONNECTION via connectionExpression only
  Spec-only query fields (confirm in VW_DOCUMENT_TRANS_DETAIL): RATING_COMPONENT, ORIGINATION, DESTINATION, RATE_UNIT, RATE, PRODUCT_GROUP
  Origination column TBD per spec - displays static TBD placeholder.
-->
"""

DOC_TYPE_EXPR = (
    '$F{DOCUMENT_TYPE}.equals(new String("INV")) ? "Tax Invoice" : '
    '$F{DOCUMENT_TYPE}.equals(new String("DEC")) ? "Outbound Statement" : '
    '$F{DOCUMENT_TYPE}'
)

INVOICE_TERMS_EXPR = (
    '$F{PAYMENT_DUE_DAYS} != null ? ("Net " + $F{PAYMENT_DUE_DAYS}.toString() + " days") : ""'
)

DATA_TYPE_LABEL = (
    '$F{DATA_TYPE} != null && $F{DATA_TYPE}.equals(new String("DOMESTIC")) ? "Domestic" : '
    '$F{DATA_TYPE} != null && $F{DATA_TYPE}.equals(new String("INTERNATIONAL")) ? "International" : '
    '$F{DATA_TYPE} != null && ($F{DATA_TYPE}.equals(new String("VBR")) || $F{DATA_TYPE}.equals(new String("SPECIAL"))) ? "Special Deal Adjustment" : '
    '"Interconnection Service"'
)


FONT = "Calibri"
FONT_SIZE = "8"


def report_element(x, y, w, h, u, print_when=None, style=None):
    u = u or uid()
    style_attr = f' style="{style}"' if style else ""
    if print_when:
        return (
            f'\t\t\t\t<reportElement x="{x}" y="{y}" width="{w}" height="{h}" uuid="{u}"{style_attr}>\n'
            f'\t\t\t\t\t<printWhenExpression><![CDATA[' + print_when + ']]></printWhenExpression>\n'
            f"\t\t\t\t</reportElement>"
        )
    return f'\t\t\t\t<reportElement x="{x}" y="{y}" width="{w}" height="{h}" uuid="{u}"{style_attr}/>'


def tf(x, y, w, h, expr, pattern=None, bold=False, align="Left", eval_time=None, print_when=None, u=None, style=None):
    u = u or uid()
    pat = f' pattern="{pattern}"' if pattern else ""
    ev = f' evaluationTime="{eval_time}"' if eval_time else ""
    bold_attr = ' isBold="true"' if bold else ""
    align_map = {"Left": "Left", "Right": "Right", "Center": "Center"}
    ta = align_map.get(align, "Left")
    re_elem = report_element(x, y, w, h, u, print_when, style)
    return (
        f'\t\t\t<textField{pat}{ev} isBlankWhenNull="true">\n'
        f"{re_elem}\n"
        f'\t\t\t\t<textElement textAlignment="{ta}" verticalAlignment="Middle">\n'
        f'\t\t\t\t\t<font fontName="{FONT}" size="{FONT_SIZE}"{bold_attr}/>\n'
        f"\t\t\t\t</textElement>\n"
        f'\t\t\t\t<textFieldExpression><![CDATA[' + expr + "]]></textFieldExpression>\n"
        f"\t\t\t</textField>"
    )


def st(x, y, w, h, text, bold=False, u=None, style=None):
    u = u or uid()
    bold_attr = ' isBold="true"' if bold else ""
    re_elem = report_element(x, y, w, h, u, style=style)
    return f"""\t\t\t<staticText>
{re_elem}
\t\t\t\t<textElement verticalAlignment="Middle">
\t\t\t\t\t<font fontName="{FONT}" size="{FONT_SIZE}"{bold_attr}/>
\t\t\t\t</textElement>
\t\t\t\t<text><![CDATA[{text}]]></text>
\t\t\t</staticText>"""


def img(x, y, w, h, expr, h_align="Left", u=None):
    # Branding logo. Layout attrs live on <reportElement> only (never on <image>);
    # scaleImage/hAlign are valid <image> attributes per the iReport 5.6.0 schema.
    u = u or uid()
    re_elem = report_element(x, y, w, h, u)
    return f"""\t\t\t<image scaleImage="RetainShape" hAlign="{h_align}">
{re_elem}
\t\t\t\t<imageExpression><![CDATA[{expr}]]></imageExpression>
\t\t\t</image>"""


def styles_block():
    return """\t<style name="Title" isDefault="false" fontName="Calibri" fontSize="10" isBold="true"/>
\t<style name="Label" isDefault="false" fontName="Calibri" fontSize="8" isBold="true"/>
\t<style name="Data" isDefault="false" fontName="Calibri" fontSize="8"/>
\t<style name="Alternate Row Colour" mode="Opaque" backcolor="#F0F0F0">
\t\t<conditionalStyle>
\t\t\t<conditionExpression><![CDATA[$V{REPORT_COUNT} % 2 == 0]]></conditionExpression>
\t\t\t<style mode="Opaque" backcolor="#F0F0F0"/>
\t\t</conditionalStyle>
\t</style>"""


def gen_main(main_name: str, detail_name: str, spec_path: Path):
    rid = uid()
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        main_header(spec_path),
        f'<jasperReport {ROOT_ATTR} name="{main_name}" language="groovy" pageWidth="595" pageHeight="842" '
        f'columnWidth="555" leftMargin="20" rightMargin="20" topMargin="20" bottomMargin="20" uuid="{rid}">',
        '\t<property name="ireport.scriptlethandling" value="0"/>',
        '\t<property name="ireport.encoding" value="UTF-8"/>',
        '\t<import value="net.sf.jasperreports.engine.*"/>',
        '\t<import value="java.util.*"/>',
        styles_block(),
        '\t<parameter name="P_TRANS_ID" class="java.lang.String"/>',
        '\t<parameter name="P_SIGNATURE" class="java.lang.String"/>',
        '\t<parameter name="TEMPLATE_FILE_DIRECTORY" class="java.lang.String"/>',
        '\t<parameter name="P_CONTACT_USER" class="java.lang.String"/>',
        '\t<parameter name="P_LOGO" class="java.lang.String"/>',
        '\t<queryString><![CDATA[SELECT',
        'TRANS.DOCUMENT_TYPE,',
        'TRANS.FRN_NAME,',
        'TRANS.FRN_ADDRESS_LINE1,',
        'TRANS.FRN_ADDRESS_LINE2,',
        'TRANS.FRN_ADDRESS_LINE3,',
        'TRANS.FRN_TAX_REG_NO,',
        'TRANS.FRN_BANK_NAME,',
        'TRANS.FRN_BANK_ACCOUNT_NAME,',
        'TRANS.FRN_BANK_ADDRESS_LINE1,',
        'TRANS.FRN_BANK_ACCOUNT_NO,',
        'TRANS.FRN_BANK_SWIFT_CODE,',
        'TRANS.FRN_TELEPHONE,',
        'TRANS.FRN_EMAIL,',
        'TRANS.OPR_NAME,',
        'TRANS.OPR_CONTACT_NO,',
        'TRANS.OPR_TAX_REG_NO,',
        'TRANS.CURRENCY,',
        'TRANS.BILLING_PERIOD,',
        'TRANS.DOCUMENT_DATE,',
        'TRANS.PAYMENT_DUE_DAYS,',
        'TRANS.PAYMENT_DUE_DATE,',
        'TRANS.DOCUMENT_NUMBER,',
        'TRANS.SERVICE_NAME,',
        'TRANS.TRAFFIC_PERIOD,',
        'TRANS.DATA_TYPE,',
        'TRANS.DETAIL_TYPE,',
        'TRANS.TRANS_TYPE,',
        'TRANS.CALL_COUNT,',
        'TRANS.USAGE,',
        'TRANS.NET_AMOUNT,',
        'TRANS.TAX_PCT,',
        'TRANS.TAX_AMOUNT,',
        'TRANS.TOTAL_AMOUNT,',
        'TRANS.AMOUNT_IN_WORDS',
        'FROM VW_DOCUMENT_TRANS_SUMMARY TRANS',
        'WHERE TRANS.ID = $P{P_TRANS_ID}',
        'AND TRANS.TOTAL_AMOUNT <> 0',
        'AND TRANS.DETAIL_TYPE = \'SERVICE\'',
        'ORDER BY TRANS.TRAFFIC_PERIOD, TRANS.DATA_TYPE, TRANS.SERVICE_NAME]]></queryString>',
    ]

    fields = [
        "DOCUMENT_TYPE", "FRN_NAME", "FRN_ADDRESS_LINE1", "FRN_ADDRESS_LINE2", "FRN_ADDRESS_LINE3",
        "FRN_TAX_REG_NO", "FRN_BANK_NAME", "FRN_BANK_ACCOUNT_NAME", "FRN_BANK_ADDRESS_LINE1",
        "FRN_BANK_ACCOUNT_NO", "FRN_BANK_SWIFT_CODE", "FRN_TELEPHONE", "FRN_EMAIL",
        "OPR_NAME", "OPR_CONTACT_NO", "OPR_TAX_REG_NO", "CURRENCY", "BILLING_PERIOD",
        "DOCUMENT_DATE", "PAYMENT_DUE_DAYS", "PAYMENT_DUE_DATE", "DOCUMENT_NUMBER",
        "SERVICE_NAME", "TRAFFIC_PERIOD", "DATA_TYPE", "DETAIL_TYPE", "TRANS_TYPE",
        "CALL_COUNT", "USAGE", "NET_AMOUNT", "TAX_PCT", "TAX_AMOUNT", "TOTAL_AMOUNT", "AMOUNT_IN_WORDS",
    ]
    money = {"CALL_COUNT", "USAGE", "NET_AMOUNT", "TAX_PCT", "TAX_AMOUNT", "TOTAL_AMOUNT", "PAYMENT_DUE_DAYS"}
    for f in fields:
        cls = "java.math.BigDecimal" if f in money else "java.lang.String"
        parts.append(f'\t<field name="{f}" class="{cls}"/>')

    vars_def = [
        ("LINE_NET_AMOUNT", "Service Name", "NET_AMOUNT"),
        ("LINE_TAX_AMOUNT", "Service Name", "TAX_AMOUNT"),
        ("LINE_TOTAL_AMOUNT", "Service Name", "TOTAL_AMOUNT"),
        ("GRP_NET_AMOUNT", "Data Type", "NET_AMOUNT"),
        ("GRP_TAX_AMOUNT", "Data Type", "TAX_AMOUNT"),
        ("GRP_TOTAL_AMOUNT", "Data Type", "TOTAL_AMOUNT"),
        ("TOTAL_INV_NET_AMOUNT", "Invoice Total", "NET_AMOUNT"),
        ("TOTAL_INV_TAX_AMOUNT", "Invoice Total", "TAX_AMOUNT"),
        ("TOTAL_INV_AMOUNT", "Invoice Total", "TOTAL_AMOUNT"),
    ]
    for vname, grp, fexpr in vars_def:
        parts.append(
            f'\t<variable name="{vname}" class="java.lang.Double" resetType="Group" resetGroup="{grp}" calculation="Sum">'
            f'\n\t\t<variableExpression><![CDATA[$F{{{fexpr}}}]]></variableExpression>\n\t</variable>'
        )

    # Groups: outer Invoice Total -> Tax -> Traffic Period -> Data Type -> Service Name
    inv_footer = f"""<groupFooter>
\t\t\t<band height="55" splitType="Stretch">
{st(300, 2, 120, 12, "Total Net Amount:", bold=True)}
{tf(420, 2, 120, 12, "$V{TOTAL_INV_NET_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
{st(300, 16, 120, 12, "Tax Amount:", bold=True)}
{tf(420, 16, 120, 12, "$V{TOTAL_INV_TAX_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
{st(300, 30, 120, 12, "Total Amount:", bold=True)}
{tf(420, 30, 120, 12, "$V{TOTAL_INV_AMOUNT}", "#,##0.00;-#,##0.00", bold=True, align="Right")}
{st(10, 40, 80, 12, "Amount In Words:", bold=True)}
{tf(90, 40, 450, 12, "$F{AMOUNT_IN_WORDS}", eval_time="Report")}
\t\t\t</band>
\t\t</groupFooter>"""

    tp_header = f"""<groupHeader>
\t\t\t<band height="16" splitType="Stretch">
{st(10, 2, 120, 12, "Traffic Period:", bold=True)}
{tf(130, 2, 200, 12, "$F{TRAFFIC_PERIOD}", bold=True)}
\t\t\t</band>
\t\t</groupHeader>"""

    dt_header = f"""<groupHeader>
\t\t\t<band height="14" splitType="Stretch">
{tf(10, 1, 300, 12, DATA_TYPE_LABEL, bold=True, print_when='!($F{DATA_TYPE} != null && ($F{DATA_TYPE}.equals(new String("VBR")) || $F{DATA_TYPE}.equals(new String("SPECIAL"))))')}
{tf(10, 1, 300, 12, DATA_TYPE_LABEL, bold=True, print_when='$F{DATA_TYPE} != null && ($F{DATA_TYPE}.equals(new String("VBR")) || $F{DATA_TYPE}.equals(new String("SPECIAL")))')}
\t\t\t</band>
\t\t</groupHeader>"""
    dt_footer = f"""<groupFooter>
\t\t\t<band height="14" splitType="Stretch">
{st(10, 1, 100, 12, "Section Subtotal:", bold=True)}
{tf(280, 1, 70, 12, "$V{GRP_NET_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
{tf(355, 1, 70, 12, "$V{GRP_TAX_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
{tf(430, 1, 70, 12, "$V{GRP_TOTAL_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
\t\t\t</band>
\t\t</groupFooter>"""

    sn_footer = f"""<groupFooter>
\t\t\t<band height="1" splitType="Stretch"/>
\t\t</groupFooter>"""

    groups = [
        ("Invoice Total", "$F{DOCUMENT_NUMBER}", inv_footer, None),
        ("Traffic Period", "$F{TRAFFIC_PERIOD}", None, tp_header),
        ("Data Type", '$F{TRAFFIC_PERIOD}+$F{DATA_TYPE}', dt_footer, dt_header),
        ("Service Name", '$F{TRAFFIC_PERIOD}+$F{DATA_TYPE}+$F{SERVICE_NAME}', sn_footer, None),
    ]
    for gname, gexpr, footer, header in groups:
        parts.append(f'\t<group name="{gname}">')
        parts.append(f'\t\t<groupExpression><![CDATA[{gexpr}]]></groupExpression>')
        if header:
            parts.append("\t\t" + header)
        if footer:
            parts.append("\t\t" + footer)
        parts.append("\t</group>")

    # columnHeader H1+H2+H3 + D1 column labels
    ch_elems = []
    # Branding logo top-right per requirement mockup (cover page).
    ch_elems.append(img(465, 0, 80, 40, "$P{P_LOGO}", h_align="Right"))
    ch_elems.append(tf(0, 0, 555, 20, DOC_TYPE_EXPR, bold=True, align="Center"))
    ch_elems.append(st(10, 24, 120, 10, "Franchise Name:", bold=True))
    ch_elems.append(tf(130, 24, 400, 10, "$F{FRN_NAME}"))
    ch_elems.append(st(10, 36, 120, 10, "Address:", bold=True))
    ch_elems.append(tf(130, 36, 400, 10, "$F{FRN_ADDRESS_LINE1}"))
    ch_elems.append(tf(130, 48, 400, 10, "$F{FRN_ADDRESS_LINE2}"))
    ch_elems.append(tf(130, 60, 400, 10, "$F{FRN_ADDRESS_LINE3}"))
    ch_elems.append(st(10, 72, 140, 10, "Tax Registration Number:", bold=True))
    ch_elems.append(tf(150, 72, 380, 10, "$F{FRN_TAX_REG_NO}"))
    ch_elems.append(st(10, 88, 120, 10, "Operator Name:", bold=True))
    ch_elems.append(tf(130, 88, 400, 10, "$F{OPR_NAME}"))
    ch_elems.append(st(10, 100, 120, 10, "Contact Number:", bold=True))
    ch_elems.append(tf(130, 100, 200, 10, '$F{OPR_CONTACT_NO} != null ? $F{OPR_CONTACT_NO} : $F{FRN_TELEPHONE}'))
    ch_elems.append(st(310, 100, 140, 10, "Tax Registration Number:", bold=True))
    ch_elems.append(tf(450, 100, 100, 10, "$F{OPR_TAX_REG_NO}"))
    ch_elems.append(st(10, 116, 90, 10, "Invoice Number:", bold=True))
    ch_elems.append(tf(100, 116, 120, 10, "$F{DOCUMENT_NUMBER}"))
    ch_elems.append(st(230, 116, 80, 10, "Invoice Period:", bold=True))
    ch_elems.append(tf(310, 116, 120, 10, "$F{BILLING_PERIOD}"))
    ch_elems.append(st(10, 128, 80, 10, "Invoice Date:", bold=True))
    ch_elems.append(tf(90, 128, 80, 10, "$F{DOCUMENT_DATE}", pattern="dd-MMM-yyyy"))
    ch_elems.append(st(180, 128, 90, 10, "Invoice Due Date:", bold=True))
    ch_elems.append(tf(270, 128, 80, 10, "$F{PAYMENT_DUE_DATE}", pattern="dd-MMM-yyyy"))
    ch_elems.append(st(360, 128, 80, 10, "Invoice Terms:", bold=True))
    ch_elems.append(tf(440, 128, 110, 10, INVOICE_TERMS_EXPR))
    ch_elems.append(st(10, 140, 90, 10, "Payment Curr:", bold=True))
    ch_elems.append(tf(100, 140, 60, 10, "$F{CURRENCY}"))
    ch_elems.append(f'\t\t\t<line>\n\t\t\t\t<reportElement x="10" y="154" width="535" height="1" uuid="{uid()}"/>\n\t\t\t</line>')
    ch_elems.append(st(10, 158, 160, 10, "Interconnection Service", bold=True))
    ch_elems.append(st(200, 158, 75, 10, "VAT Excl. Amount", bold=True))
    ch_elems.append(st(280, 158, 40, 10, "VAT%", bold=True))
    ch_elems.append(st(325, 158, 70, 10, "VAT Amount", bold=True))
    ch_elems.append(st(400, 158, 85, 10, "VAT Incl. Amount", bold=True))

    parts.append("\t<columnHeader>")
    parts.append('\t\t<band height="172" splitType="Stretch">')
    parts.extend(ch_elems)
    parts.append("\t\t</band>")
    parts.append("\t</columnHeader>")

    # detail rows
    d_elems = [
        tf(10, 1, 185, 12, "$F{SERVICE_NAME}", style="Alternate Row Colour"),
        tf(200, 1, 75, 12, "$F{NET_AMOUNT}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"),
        tf(280, 1, 40, 12, "$F{TAX_PCT}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"),
        tf(325, 1, 70, 12, "$F{TAX_AMOUNT}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"),
        tf(400, 1, 85, 12, "$F{TOTAL_AMOUNT}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"),
    ]
    parts.append("\t<detail>")
    parts.append('\t\t<band height="14" splitType="Stretch">')
    parts.extend(d_elems)
    parts.append("\t\t</band>")
    parts.append("\t</detail>")

    parts.append("\t<pageFooter>")
    parts.append('\t\t<band height="18" splitType="Stretch">')
    parts.append(tf(400, 2, 150, 12, '"Page " + $V{PAGE_NUMBER} + " of " + $V{PAGE_COUNT}', align="Right"))
    parts.append("\t\t</band>")
    parts.append("\t</pageFooter>")

    # summary: F1 bank, F2 contact, subreport
    sum_elems = [
        st(10, 5, 200, 12, "Bank Payment Details", bold=True),
        st(10, 20, 80, 10, "Account No:", bold=True),
        tf(90, 20, 150, 10, "$F{FRN_BANK_ACCOUNT_NO}", eval_time="Report"),
        st(250, 20, 70, 10, "Swift Code:", bold=True),
        tf(320, 20, 120, 10, "$F{FRN_BANK_SWIFT_CODE}", eval_time="Report"),
        st(10, 32, 90, 10, "Account Name:", bold=True),
        tf(100, 32, 200, 10, '$F{FRN_BANK_ACCOUNT_NAME} != null ? $F{FRN_BANK_ACCOUNT_NAME} : $F{FRN_BANK_NAME}', eval_time="Report"),
        st(10, 44, 70, 10, "Bank Name:", bold=True),
        tf(80, 44, 220, 10, "$F{FRN_BANK_NAME}", eval_time="Report"),
        st(10, 56, 80, 10, "Bank Address:", bold=True),
        tf(90, 56, 350, 10, "$F{FRN_BANK_ADDRESS_LINE1}", eval_time="Report"),
        st(10, 68, 70, 10, "Telephone:", bold=True),
        tf(80, 68, 150, 10, "$F{FRN_TELEPHONE}", eval_time="Report"),
        st(10, 85, 80, 10, "Contact No:", bold=True),
        tf(130, 85, 250, 10, '$P{P_CONTACT_USER} != null && $P{P_CONTACT_USER}.length() > 0 ? $P{P_CONTACT_USER} : "N/A"', eval_time="Report"),
    ]
    sub_uid = uid()
    parts.append("\t<summary>")
    parts.append('\t\t<band height="220" splitType="Stretch">')
    parts.extend(sum_elems)
    parts.append(
        f'\t\t\t<subreport>\n'
        f'\t\t\t\t<reportElement x="0" y="105" width="555" height="100" uuid="{sub_uid}"/>\n'
        f'\t\t\t\t<subreportParameter name="P_TRANS_ID">\n'
        f'\t\t\t\t\t<subreportParameterExpression><![CDATA[$P{{P_TRANS_ID}}]]></subreportParameterExpression>\n'
        f'\t\t\t\t</subreportParameter>\n'
        f'\t\t\t\t<subreportParameter name="P_LOGO">\n'
        f'\t\t\t\t\t<subreportParameterExpression><![CDATA[$P{{P_LOGO}}]]></subreportParameterExpression>\n'
        f'\t\t\t\t</subreportParameter>\n'
        f'\t\t\t\t<connectionExpression><![CDATA[$P{{REPORT_CONNECTION}}]]></connectionExpression>\n'
        f'\t\t\t\t<subreportExpression><![CDATA[$P{{TEMPLATE_FILE_DIRECTORY}} + "{detail_name}.jasper"]]></subreportExpression>\n'
        f'\t\t\t</subreport>'
    )
    parts.append("\t\t</band>")
    parts.append("\t</summary>")
    parts.append("</jasperReport>")
    return "\n".join(parts) + "\n"


def gen_detail(detail_name: str, spec_path: Path):
    rid = uid()
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        detail_header(spec_path),
        f'<jasperReport {ROOT_ATTR} name="{detail_name}" language="groovy" pageWidth="595" pageHeight="842" '
        f'columnWidth="555" leftMargin="20" rightMargin="20" topMargin="20" bottomMargin="20" uuid="{rid}">',
        '\t<property name="ireport.encoding" value="UTF-8"/>',
        '\t<import value="net.sf.jasperreports.engine.*"/>',
        styles_block(),
        '\t<parameter name="P_TRANS_ID" class="java.lang.String"/>',
        '\t<parameter name="P_LOGO" class="java.lang.String"/>',
        '\t<queryString><![CDATA[SELECT',
        'TRANS.TRAFFIC_PERIOD,',
        'TRANS.SERVICE_NAME,',
        'TRANS.RATING_COMPONENT,',
        'TRANS.ORIGINATION,',
        'TRANS.DESTINATION,',
        'TRANS.CALL_COUNT,',
        'TRANS.USAGE,',
        'TRANS.RATE_UNIT,',
        'TRANS.RATE,',
        'TRANS.NET_AMOUNT,',
        'TRANS.DETAIL_TYPE,',
        'TRANS.PRODUCT_GROUP,',
        'TRANS.FRN_NAME,',
        'TRANS.FRN_TAX_REG_NO,',
        'TRANS.OPR_NAME,',
        'TRANS.DOCUMENT_NUMBER,',
        'TRANS.BILLING_PERIOD,',
        'TRANS.DOCUMENT_DATE,',
        'TRANS.PAYMENT_DUE_DATE,',
        'TRANS.CURRENCY',
        'FROM VW_DOCUMENT_TRANS_DETAIL TRANS',
        'WHERE TRANS.ID = $P{P_TRANS_ID}',
        'AND TRANS.NET_AMOUNT <> 0',
        'ORDER BY TRANS.TRAFFIC_PERIOD, TRANS.PRODUCT_GROUP, TRANS.SERVICE_NAME]]></queryString>',
    ]
    fields = [
        ("TRAFFIC_PERIOD", "java.lang.String"),
        ("SERVICE_NAME", "java.lang.String"),
        ("RATING_COMPONENT", "java.lang.String"),
        ("ORIGINATION", "java.lang.String"),
        ("DESTINATION", "java.lang.String"),
        ("CALL_COUNT", "java.math.BigDecimal"),
        ("USAGE", "java.math.BigDecimal"),
        ("RATE_UNIT", "java.lang.String"),
        ("RATE", "java.math.BigDecimal"),
        ("NET_AMOUNT", "java.math.BigDecimal"),
        ("DETAIL_TYPE", "java.lang.String"),
        ("PRODUCT_GROUP", "java.lang.String"),
        ("FRN_NAME", "java.lang.String"),
        ("FRN_TAX_REG_NO", "java.lang.String"),
        ("OPR_NAME", "java.lang.String"),
        ("DOCUMENT_NUMBER", "java.lang.String"),
        ("BILLING_PERIOD", "java.lang.String"),
        ("DOCUMENT_DATE", "java.lang.String"),
        ("PAYMENT_DUE_DATE", "java.lang.String"),
        ("CURRENCY", "java.lang.String"),
    ]
    for fn, cls in fields:
        parts.append(f'\t<field name="{fn}" class="{cls}"/>')

    for vname, grp in [
        ("DETAIL_NET_AMOUNT", "Product Group"),
        ("DETAIL_CALL_COUNT", "Product Group"),
        ("DETAIL_USAGE", "Product Group"),
    ]:
        f = "CALL_COUNT" if "CALL" in vname else "USAGE" if "USAGE" in vname else "NET_AMOUNT"
        parts.append(
            f'\t<variable name="{vname}" class="java.lang.Double" resetType="Group" resetGroup="{grp}" calculation="Sum">'
            f'\n\t\t<variableExpression><![CDATA[$F{{{f}}}]]></variableExpression>\n\t</variable>'
        )

    tp_h = f"""<groupHeader>
\t\t\t<band height="16" splitType="Stretch">
{st(10, 2, 120, 12, "Traffic Period:", bold=True)}
{tf(130, 2, 250, 12, "$F{TRAFFIC_PERIOD}", bold=True)}
\t\t\t</band>
\t\t</groupHeader>"""
    pg_h = f"""<groupHeader>
\t\t\t<band height="12" splitType="Stretch">
{tf(10, 0, 300, 12, '$F{PRODUCT_GROUP} != null ? $F{PRODUCT_GROUP} : $F{SERVICE_NAME}', bold=True)}
\t\t\t</band>
\t\t</groupHeader>"""
    pg_f = f"""<groupFooter>
\t\t\t<band height="14" splitType="Stretch">
{st(10, 1, 120, 12, "Subtotal:", bold=True)}
{tf(300, 1, 50, 12, "$V{DETAIL_CALL_COUNT}", "#,##0;-#,##0", align="Right")}
{tf(355, 1, 50, 12, "$V{DETAIL_USAGE}", "#,##0.00;-#,##0.00", align="Right")}
{tf(480, 1, 65, 12, "$V{DETAIL_NET_AMOUNT}", "#,##0.00;-#,##0.00", align="Right")}
\t\t\t</band>
\t\t</groupFooter>"""

    for gname, gexpr, header, footer in [
        ("Traffic Period", "$F{TRAFFIC_PERIOD}", tp_h, None),
        ("Product Group", '$F{TRAFFIC_PERIOD}+$F{PRODUCT_GROUP}+$F{SERVICE_NAME}', pg_h, pg_f),
    ]:
        parts.append(f'\t<group name="{gname}">')
        parts.append(f'\t\t<groupExpression><![CDATA[{gexpr}]]></groupExpression>')
        if header:
            parts.append("\t\t" + header)
        if footer:
            parts.append("\t\t" + footer)
        parts.append("\t</group>")

    ph = []
    # Branding logo top-left per requirement mockup (detail page); franchise name
    # shifts right of the logo and left-aligns to match the layout.
    ph.append(img(10, 0, 90, 16, "$P{P_LOGO}", h_align="Left"))
    ph.append(tf(110, 0, 440, 16, "$F{FRN_NAME}", bold=True, align="Left"))
    ph.append(st(10, 18, 140, 10, "Tax Registration Number:", bold=True))
    ph.append(tf(150, 18, 380, 10, "$F{FRN_TAX_REG_NO}", eval_time="Report"))
    ph.append(st(10, 32, 50, 10, "Bill To:", bold=True))
    ph.append(tf(60, 32, 250, 10, "$F{OPR_NAME}", eval_time="Report"))
    ph.append(st(320, 32, 100, 10, "Invoice Reference:", bold=True))
    ph.append(tf(420, 32, 130, 10, "$F{DOCUMENT_NUMBER}", eval_time="Report"))
    ph.append(st(10, 44, 90, 10, "Invoice Period:", bold=True))
    ph.append(tf(100, 44, 150, 10, "$F{BILLING_PERIOD}", eval_time="Report"))
    ph.append(st(10, 56, 80, 10, "Invoice Date:", bold=True))
    ph.append(tf(90, 56, 90, 10, "$F{DOCUMENT_DATE}", pattern="dd-MMM-yyyy", eval_time="Report"))
    ph.append(st(200, 56, 95, 10, "Invoice Due Date:", bold=True))
    ph.append(tf(295, 56, 90, 10, "$F{PAYMENT_DUE_DATE}", pattern="dd-MMM-yyyy", eval_time="Report"))
    ph.append(st(400, 56, 80, 10, "Payment Curr:", bold=True))
    ph.append(tf(480, 56, 70, 10, "$F{CURRENCY}", eval_time="Report"))

    parts.append("\t<pageHeader>")
    parts.append('\t\t<band height="72" splitType="Stretch">')
    parts.extend(ph)
    parts.append("\t\t</band>")
    parts.append("\t</pageHeader>")

    cols = [
        (10, 140, "Product Description"),
        (145, 55, "Rating Component"),
        (205, 45, "Origination"),
        (255, 55, "Destination"),
        (315, 40, "Count"),
        (360, 45, "Usage"),
        (410, 35, "Unit"),
        (450, 40, "Rate"),
        (495, 55, "Amount"),
    ]
    parts.append("\t<columnHeader>")
    parts.append('\t\t<band height="16" splitType="Stretch">')
    for x, w, lbl in cols:
        parts.append(st(x, 2, w, 12, lbl, bold=True))
    parts.append("\t\t</band>")
    parts.append("\t</columnHeader>")

    parts.append("\t<detail>")
    parts.append('\t\t<band height="14" splitType="Stretch">')
    parts.append(tf(10, 1, 130, 12, "$F{SERVICE_NAME}", style="Alternate Row Colour"))
    parts.append(tf(145, 1, 55, 12, "$F{RATING_COMPONENT}", style="Alternate Row Colour"))
    parts.append(tf(205, 1, 45, 12, '$F{ORIGINATION} != null && $F{ORIGINATION}.length() > 0 ? $F{ORIGINATION} : "TBD"', style="Alternate Row Colour"))
    parts.append(tf(255, 1, 55, 12, "$F{DESTINATION}", style="Alternate Row Colour"))
    parts.append(tf(315, 1, 40, 12, "$F{CALL_COUNT}", "#,##0;-#,##0", align="Right", style="Alternate Row Colour"))
    parts.append(tf(360, 1, 45, 12, "$F{USAGE}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"))
    parts.append(tf(410, 1, 35, 12, "$F{RATE_UNIT}", style="Alternate Row Colour"))
    parts.append(tf(450, 1, 40, 12, "$F{RATE}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"))
    parts.append(tf(495, 1, 55, 12, "$F{NET_AMOUNT}", "#,##0.00;-#,##0.00", align="Right", style="Alternate Row Colour"))
    parts.append("\t\t</band>")
    parts.append("\t</detail>")
    parts.append("</jasperReport>")
    return "\n".join(parts) + "\n"


def _output_by_role(outputs: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    by_suffix: dict[str, dict[str, str]] = {}
    for item in outputs:
        stem = Path(item["file"]).stem
        if stem.endswith("_main"):
            by_suffix["main"] = item
        elif stem.endswith("_detail"):
            by_suffix["detail"] = item
    if "main" not in by_suffix and outputs:
        by_suffix["main"] = outputs[0]
    if "detail" not in by_suffix and len(outputs) > 1:
        by_suffix["detail"] = outputs[1]
    return by_suffix


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default=str(DEFAULT_SPEC),
        help="Functional spec .md path",
    )
    args = parser.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.is_file():
        print(f"Spec not found: {spec_path}", file=sys.stderr)
        return 1

    resolved = derive_outputs(spec_path)
    roles = _output_by_role(resolved["outputs"])
    if "main" not in roles or "detail" not in roles:
        print(
            "Spec must define Cover + Detail pages (or explicit output table with _main/_detail).",
            file=sys.stderr,
        )
        return 1

    main_out = roles["main"]
    detail_out = roles["detail"]
    main_name = main_out["jasper_name"]
    detail_name = detail_out["jasper_name"]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / main_out["file"]).write_text(
        gen_main(main_name, detail_name, spec_path), encoding="utf-8"
    )
    (OUT / detail_out["file"]).write_text(
        gen_detail(detail_name, spec_path), encoding="utf-8"
    )
    print(f"Spec: {spec_path}")
    print(f"Wrote {OUT / main_out['file']}")
    print(f"Wrote {OUT / detail_out['file']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
