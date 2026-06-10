<!-- Auto-generated from Invoice_Functional_Template.docx. Edit the .docx and re-run docx_spec_to_md.py -->

> **Source:** `Invoice_Functional_Template.docx`  **Pipeline format:** Markdown for agents. Regenerate: `.venv\Scripts\python.exe scripts/docx_spec_to_md.py functional_spec/Invoice_Functional_Template.docx`

- **National Invoice Usage Template**

This template will be used for tax invoices for Domestic/National customers.

| Page | Description |
| --- | --- |
| Cover page | One-page (or multi-page) summary invoice: franchise and operator details, invoice metadata, traffic summary by period and product type, invoice totals, bank payment details, and contact number. |
| Detail page | Supporting detail listing each product / rating line with counts, usage, rate, and amount; includes subtotals by traffic period and product group. |

- **Document flow**

`flowchart TB``
  Cover[Cover page — summary invoice]``
  Detail[Detail page — line breakdown]``
  Cover --> Detail`

- **General Instruction on the**** invoice templates:**
- Each invoice template will be 2 pages PDF.
- Cover Page
- Detail Page
- Date format across invoice document would be DD-MON-YYYY format.
- Volumes should be comma formatted, e.g. 1,001,999
- Where two currencies are shown on a single invoice, both should show the full description, e.g. NZD & USD
- 0 currency amounts should be shown as $-.
- 0 volume amounts should be shown as 0.00
- All Amount, Percentage and Duration figures shown on the invoice would be rounded to 2 decimal places.
- Font ‘Callbri’ to be used for all documents.
- Page number and total pages (e.g. *Page 1 of 2*), right aligned

- **Cover Page**

| REPORT | Sections | Description |  |
| --- | --- | --- | --- |
| COVER PAGE |  |  |  |
| COVER PAGE | Sections | Label | Description |
| COVER PAGE | HEADER and TITLE | H1 | Document Type: Invoice or Declaration Tax Invoice Outbound Statement Franchise Name: Full Name of the Franchise Address: Full Address of the Franchise Tax Registration Number: Tax number of the Franchise |
| COVER PAGE | HEADER and TITLE | H2 | Operator Name: Full Name of the billed Operator Contact Number: Telephone number of the billed Operator Tax Registration Number: Tax number of the billed Operator |
| COVER PAGE | HEADER and TITLE | H3 | Invoice Number: Invoice Number Invoice Period: Billing Period Invoice Date: Date of invoice generation Invoice Due Date: Invoice Due Date calculated based on Term ID Invoice Terms: Payment invoice terms Payment Curr: Invoice currency |
| COVER PAGE | DETAIL | D1 | This Section of the invoice gives the summary of the traffic billed to the customer. Traffic Period: the traffic period, sorted from older to new. Format: YYYY/MM/DD - YYYY/MM/DD Detail Interconnection Service: Domestic: Description is derived based on ICT rating scenario name eg: "Incoming - Fix Termination" International: ICT billed product eg: "International Direct Dial"  Special Deal Adjustment: This section will appear only if there is VBR for national traffic.  VAT Exclusive Amount: Total Amount without taxes VAT%: Taxes percentage per product VAT Amount: Total taxes amount VAT Inclusive Amount: Total amount including taxes Amount In Words: Total amount of invoice in words |
| COVER PAGE | FOOTER | F1 | Account No: Franchise bank account number for the invoice currency Swift Code: Franchise swift code  Account Name: Franchise bank account name Bank Name: Franchise bank account name Bank Address: Franchise bank address Telephone: Franchise telephone number |
| COVER PAGE |  | F2 | Contact No: User who approved/generated the invoice |

- **Data Source**

Main query -> VW_DOCUMENT_TRANS_SUMMARY

Alias: TRANS. Implements Fields Needed for cover page

SELECT

TRANS.DOCUMENT_TYPE,

TRANS.FRN_NAME,

TRANS.FRN_ADDRESS_LINE1,

TRANS.FRN_ADDRESS_LINE2,

TRANS.FRN_ADDRESS_LINE3,

'X123' FRN_TAX_REG_NO,

'HDFC BANK' FRN_BANK_NAME,

'ERTY' FRN_BANK_ACCOUNT_NAME,

TRANS.FRN_BANK_ADDRESS_LINE1,

'AABBCC' FRN_BANK_ACCOUNT_NO,

TRANS.FRN_BANK_SWIFT_CODE,

TRANS.FRN_TELEPHONE,

TRANS.FRN_EMAIL,

TRANS.OPR_NAME,

'1234' OPR_CONTACT_NO,

'Y123' OPR_TAX_REG_NO,

TRANS.CURRENCY,

TRANS.BILLING_PERIOD,

TRANS.DOCUMENT_DATE,

TRANS.PAYMENT_DUE_DAYS,

TRANS.PAYMENT_DUE_DATE,

TRANS.DOCUMENT_NUMBER,

TRANS.SERVICE_NAME,

TRANS.TRAFFIC_PERIOD,

TRANS.DATA_TYPE,

'SERVICE' DETAIL_TYPE,

TRANS.TRANS_TYPE,

TRANS.CALL_COUNT,

TRANS.USAGE,

TRANS.NET_AMOUNT,

TRANS.TAX_PCT,

TRANS.TAX_AMOUNT,

TRANS.TOTAL_AMOUNT,

TRANS.AMOUNT_IN_WORDS,

'TERM' RATING_COMPONENT,

'DUMMY' ORIGINATION,

'INDIA' DESTINATION,

'MIN' RATE_UNIT,

'0.52' RATE,

'TELE' PRODUCT_GROUP

FROM VW_DOCUMENT_TRANS_SUMMARY TRANS

WHERE  ID = $P{P_TRANS_ID}

AND TRANS.TOTAL_AMOUNT <> 0

ORDER BY TRANS.TRAFFIC_PERIOD, TRANS.DATA_TYPE, TRANS.SERVICE_NAME

- **Business Rule**

| Field | Section and Level | Used on | Business Rule |
| --- | --- | --- | --- |
| Document Type | HEADER and TITLE; H1 |  | Tax Invoice when document type is invoice (INV); Outbound Statement when declaration (DEC); otherwise show the system document type. |
| All other listed fields | All other labels on HEADER and FOOTER | Per query |  |
| Traffic period | DETAIL, D1 |  | Under each traffic period, charges grouped by traffic type:  Line items:- One row per service/product with amounts and tax columns.  Section subtotal:- Subtotal per data type (domestic / international / special deal) for net, tax, and total.  Invoice totals: - Total Net Amount, Tax Amount, Total Amount; Amount in words for the invoice total. |

- **Detail Page**

| REPORT | Sections | Description |  |
| --- | --- | --- | --- |
| DETAIL PAGE |  |  |  |
| DETAIL PAGE | Sections | Label | Description |
| DETAIL PAGE | HEADER and TITLE | H1 | Franchise Name: Full Name of the Franchise Tax Registration Number: Tax number of the Franchise |
| DETAIL PAGE | HEADER and TITLE | H2 | Bill To: Operator Name Invoice Reference: Invoice Number Invoice Period: Billing Period |
| DETAIL PAGE | HEADER and TITLE | H3 | Invoice Date: Date of invoice generation Invoice Due Date: Invoice Due Date calculated based on Term ID Payment Curr: Invoice currency |
| DETAIL PAGE | DETAIL | D1 | This Section of the invoice gives the detail of the traffic billed to the customer. Traffic Period: the traffic period, sorted from older to new. Format: YYYY/MM/DD - YYYY/MM/DD Detail: this should be break down by product or VBR and subtotals calculated Product Description: Description is derived based on ICT rating scenario name eg: Incoming - Fix Termination OR description derived from Step Number Name. Rating Component: ICT rating component  Origination: TBD Destination: Tier name Count: Number of events Usage: Total minutes or volume Unit: Rate unit Rate: Unit cost used or flat rate charge Amount: amount without taxes |

- **Data Source**

Main query -> VW_DOCUMENT_TRANS_SUMMARY

Alias: TRANS. Implements Fields Needed for detail page

SELECT

TRANS.DOCUMENT_TYPE,

TRANS.FRN_NAME,

TRANS.FRN_ADDRESS_LINE1,

TRANS.FRN_ADDRESS_LINE2,

TRANS.FRN_ADDRESS_LINE3,

'X123' FRN_TAX_REG_NO,

'HDFC BANK' FRN_BANK_NAME,

'ERTY' FRN_BANK_ACCOUNT_NAME,

TRANS.FRN_BANK_ADDRESS_LINE1,

'AABBCC' FRN_BANK_ACCOUNT_NO,

TRANS.FRN_BANK_SWIFT_CODE,

TRANS.FRN_TELEPHONE,

TRANS.FRN_EMAIL,

TRANS.OPR_NAME,

'1234' OPR_CONTACT_NO,

'Y123' OPR_TAX_REG_NO,

TRANS.CURRENCY,

TRANS.BILLING_PERIOD,

TRANS.DOCUMENT_DATE,

TRANS.PAYMENT_DUE_DAYS,

TRANS.PAYMENT_DUE_DATE,

TRANS.DOCUMENT_NUMBER,

TRANS.SERVICE_NAME,

TRANS.TRAFFIC_PERIOD,

TRANS.DATA_TYPE,

'SERVICE' DETAIL_TYPE,

TRANS.TRANS_TYPE,

TRANS.CALL_COUNT,

TRANS.USAGE,

TRANS.NET_AMOUNT,

TRANS.TAX_PCT,

TRANS.TAX_AMOUNT,

TRANS.TOTAL_AMOUNT,

TRANS.AMOUNT_IN_WORDS,

'TERM' RATING_COMPONENT,

'DUMMY' ORIGINATION,

'INDIA' DESTINATION,

'MIN' RATE_UNIT,

'0.52' RATE,

'TELE' PRODUCT_GROUP

FROM VW_DOCUMENT_TRANS_SUMMARY TRANS

WHERE ID = $P{P_TRANS_ID}

AND TRANS.TOTAL_AMOUNT <> 0

ORDER BY TRANS.TRAFFIC_PERIOD, TRANS.DATA_TYPE, TRANS.SERVICE_NAME

- **Business Rule**

| Field | Section and Level | Used on | Business Rule |
| --- | --- | --- | --- |
| Traffic period | Detail, D1 |  | Under each traffic period, charges grouped by traffic type:  Line items:- One row per service/product with amounts and no tax columns.  Section subtotal:- Subtotal per data type (domestic / international / special deal) for net, and total.  Invoice totals:- Total Net Amount, Total Amount; |
| All other listed fields | All other labels on Detail | Per query |  |
|  |  |  |  |

- **Parameters**

| Parameter | Required | Purpose |
| --- | --- | --- |
| P_TRANS_ID | Yes | Document transaction ID (TRANS.ID in views). Passed from main subreport parameter. |
