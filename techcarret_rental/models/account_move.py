import base64
import io

import xlsxwriter

from odoo import models

HEADERS = [
    "Invoice Date", "Sales Order Number", "Invoice Number", "Customer Name",
    "Due Date", "PurchaseOrder/ Reference #", "Currency Code",
    "Payment Terms Label", "Account", "Product", "Invoice Description",
    "Quantity", "Item Price /Rate", "Total", "Item Tax %",
    "Item Tax Amount", "Amount with Tax", "Project Name/Code",
]

# 0-based column indices that need special number/date formatting
DATE_COLS = {0, 4}
MONEY_COLS = {11, 12, 13, 15, 16}


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_export_invoice_xlsx(self):
        """Export the selected customer invoices to a formatted XLSX.
        One row per invoice LINE (product). If an invoice has a single
        product it produces a single row, exactly as before. If it has
        multiple products, it now produces one row per product, with the
        invoice-level columns (date, invoice number, customer, due date,
        PO ref, currency, payment terms) repeated identically on every
        row belonging to that invoice.
        Bound to the Invoices list view via the 'Export Invoices to XLSX'
        server action (see data/ir_actions_server.xml) so it's callable
        from Action menu after selecting records.
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("Invoice")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#D9E1F2", "border": 1,
        })
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
        money_format = workbook.add_format({"num_format": "#,##0.00"})

        for col, header in enumerate(HEADERS):
            sheet.write(0, col, header, header_format)
        sheet.set_column(0, len(HEADERS) - 1, 18)

        row_idx = 1
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                continue
            row_idx = move._write_invoice_export_rows(
                sheet, row_idx, date_format, money_format
            )

        workbook.close()
        output.seek(0)

        attachment = self.env["ir.attachment"].create({
            "name": "Invoice_Export.xlsx",
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "res_model": "account.move",
            "mimetype": (
                "application/vnd.openxmlformats-officedocument"
                ".spreadsheetml.sheet"
            ),
        })

        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % attachment.id,
            "target": "self",
        }

    def _write_invoice_export_rows(self, sheet, row_idx, date_format, money_format):
        """Write one row per invoice line (product) for a single invoice
        (self). Invoice-level fields are computed once and repeated on
        every row; line-level fields (product, qty, price, tax, account,
        project) are written per line.
        """
        self.ensure_one()
        move = self

        lines = move.invoice_line_ids.filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
        )
        if not lines:
            return row_idx

        # --- Invoice-level fields: same for every row of this invoice ---
        invoice_date = move.invoice_date
        invoice_due_date = move.invoice_date_due
        invoice_number = move.name
        customer_name = move.partner_id.name
        currency_code = move.currency_id.name
        payment_terms = move.invoice_payment_term_id.name or ""

        sale_order_names = []
        po_reference = []
        for l in lines:
            for sale_line in l.sale_line_ids:
                so_name = sale_line.order_id.x_studio_so_period_1
                po_ref = sale_line.order_id.client_order_ref
                if so_name and so_name not in sale_order_names:
                    sale_order_names.append(so_name)
                if po_ref and po_ref not in po_reference:
                    po_reference.append(po_ref)
        sale_order_str = ", ".join(sale_order_names)
        po_reference_str = ", ".join(po_reference)

        # --- Line-level fields: one row per product line ---
        for l in lines:
            account_name = l.account_id.name or ""
            product_name = l.product_id.display_name or ""
            description = l.name or ""
            qty = l.quantity
            price_unit = l.price_unit
            price_subtotal = l.price_subtotal
            tax_amount = l.l10n_gcc_invoice_tax_amount

            line_tax_names = [t.name for t in l.tax_ids if t.name]
            tax_name_str = ", ".join(dict.fromkeys(line_tax_names))

            analytic_ids_seen = set()
            dist = l.analytic_distribution or {}
            for key in dist.keys():
                # keys can combine several analytic-plan ids, e.g. "4009,3974"
                for part in key.split(","):
                    part = part.strip()
                    if part:
                        analytic_ids_seen.add(int(part))
            project_names = []
            if analytic_ids_seen:
                analytic_accounts = self.env["account.analytic.account"].browse(
                    list(analytic_ids_seen)
                )
                project_names = [
                    a.name for a in analytic_accounts if a.exists() and a.name
                ]
            project_str = ", ".join(project_names)

            row_values = [
                invoice_date,
                sale_order_str,
                invoice_number,
                customer_name,
                invoice_due_date,
                po_reference_str,
                currency_code,
                payment_terms,
                account_name,
                product_name,
                description,
                qty,
                price_unit,
                price_subtotal,
                tax_name_str,
                tax_amount,
                price_subtotal + tax_amount,
                project_str,
            ]

            for col, value in enumerate(row_values):
                if col in DATE_COLS:
                    if value:
                        sheet.write_datetime(row_idx, col, value, date_format)
                    else:
                        sheet.write(row_idx, col, "")
                elif col in MONEY_COLS:
                    sheet.write_number(row_idx, col, value or 0.0, money_format)
                else:
                    sheet.write(row_idx, col, value or "")

            row_idx += 1

        return row_idx

