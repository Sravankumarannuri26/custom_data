import base64
import io

import xlsxwriter

from odoo import models

HEADERS = [
    "Order Reference", "Order Date", "Customer", "Salesperson", "Currency",
    "PO Reference", "Expiration", "Item (Product) Name",
    "Description", "Quantity", "Qty Invoiced", "UoM", "Unit Price", "Total",
]

# 0-based column indices that need special number/date formatting
DATE_COLS = {1, 6}
MONEY_COLS = {13, 14}


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_export_so_line_products_xlsx(self):
        """Export all sale.order.line records (products) for the selected
        sale orders to a formatted XLSX. One row per order line, with the
        order-level columns (reference, date, customer) repeated on every
        row belonging to that order.
        Bound to the Sales Orders list view via the 'Export Order Lines to
        XLSX' server action (see data/ir_actions_server.xml) so it's
        callable from the Action menu after selecting records.
        """
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        sheet = workbook.add_worksheet("SO Line Products")

        header_format = workbook.add_format({
            "bold": True, "bg_color": "#D9E1F2", "border": 1,
        })
        date_format = workbook.add_format({"num_format": "dd/mm/yyyy"})
        money_format = workbook.add_format({"num_format": "#,##0.00"})

        for col, header in enumerate(HEADERS):
            sheet.write(0, col, header, header_format)
        sheet.set_column(0, len(HEADERS) - 1, 18)
        sheet.set_column(9, 9, 40)  # widen Description column

        row_idx = 1
        for order in self:
            row_idx = order._write_so_line_products_rows(
                sheet, row_idx, date_format, money_format
            )

        workbook.close()
        output.seek(0)

        attachment = self.env["ir.attachment"].create({
            "name": "Sale_Order_Line_Products.xlsx",
            "type": "binary",
            "datas": base64.b64encode(output.read()),
            "res_model": "sale.order",
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

    def _write_so_line_products_rows(self, sheet, row_idx, date_format, money_format):
        """Write one row per sale.order.line (product) for a single order
        (self). Order-level fields are computed once and repeated on every
        row; line-level fields (product, description, qty, uom, price)
        are written per line.
        """
        self.ensure_one()
        order = self

        lines = order.order_line.filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
        )
        if not lines:
            return row_idx

        # --- Order-level fields: same for every row of this order ---
        order_ref = order.name
        order_date = order.date_order
        customer_name = order.partner_id.name
        salesperson = order.user_id.name or ""
        currency_name = order.currency_id.name or ""
        po_reference = order.client_order_ref or ""
        expiration = order.validity_date

        # --- Line-level fields: one row per product line ---
        for l in lines:
            product_name = l.product_id.display_name or ""

            description = l.name or ""
            qty = l.product_uom_qty
            qty_invoiced = l.qty_invoiced
            uom_name = l.product_uom_id.name or ""
            price_unit = l.price_unit
            price_total = l.price_total

            row_values = [
                order_ref,
                order_date,
                customer_name,
                salesperson,
                currency_name,
                po_reference,
                expiration,
                product_name,

                description,
                qty,
                qty_invoiced,
                uom_name,
                price_unit,
                price_total,
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