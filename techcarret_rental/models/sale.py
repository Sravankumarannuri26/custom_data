# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # _sql_constraints = [
    #     ('accountable_required_fields',
    #         "CHECK(display_type IS NOT NULL OR is_downpayment OR (product_id IS NOT NULL AND product_uom IS NOT NULL))",
    #         "Missing required fields on accountable sale order line."),
    #     ('non_accountable_null_fields',
    #         "CHECK((product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 AND product_uom IS NULL AND customer_lead = 0))",
    #         "Forbidden values on non-accountable sale order line"),
    # ]
    _accountable_required_fields = models.Constraint(
        "CHECK(display_type IS NOT NULL OR is_downpayment OR "
        "(product_id IS NOT NULL AND product_uom_id IS NOT NULL))",
        "Missing required fields on accountable sale order line."
    )

   #_non_accountable_null_fields = models.Constraint(
   #     "CHECK((product_id IS NULL AND price_unit = 0 AND product_uom_qty = 0 "
   #     "AND product_uom_id IS NULL AND customer_lead = 0))",
   #     "Forbidden values on non-accountable sale order line"
   #)

class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        self._check_amount_is_positive()
        has_rental_order=False
        has_invoice_lines=False
        for sale in self.sale_order_ids:
            if sale.is_rental_order == True:
                has_rental_order=True
            if sale.rental_inv_line_ids:
                has_invoice_lines=True
        if has_rental_order==True and has_invoice_lines==True:
            for sale in self.sale_order_ids:
                count=0
                for rental in sale.rental_inv_line_ids:
                    if count==0 and rental.state=='draft':
                        sale._cron_create_rental_month_invoices(rental)
                    count = count + 1
        else:
            invoices = self._create_invoices(self.sale_order_ids)
            return self.sale_order_ids.action_view_invoice(invoices=invoices)
