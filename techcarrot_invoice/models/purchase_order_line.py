# -*- coding: utf-8 -*-
from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # ------------------------------------------------------------------
    # Core logic: compare supplier state vs delivery state and return
    # the correct tax (18% GST if same state, 18% IGST if different).
    # ------------------------------------------------------------------
    def _get_state_based_tax(self):
        self.ensure_one()

        order = self.order_id
        supplier = order.partner_id
        delivery = order.deliver_partner_id

        if not supplier or not delivery:
            return self.env['account.tax']

        if supplier.country_id.code != 'IN' or delivery.country_id.code != 'IN':
            return self.env['account.tax']

        supplier_state = supplier.state_id
        delivery_state = delivery.state_id

        if not supplier_state or not delivery_state:
            return self.env['account.tax']

        Tax = self.env['account.tax']

        if supplier_state == delivery_state:
            tax = Tax.search([
                ('name', 'in', ['9% CGST','9% SGST']),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', order.company_id.id),
                ('active', '=', True),
            ], limit=2)
        else:
            tax = Tax.search([
                ('name', '=', '18% IGST'),
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', order.company_id.id),
                ('active', '=', True),
            ], limit=1)

        return tax

    # ------------------------------------------------------------------
    # UI feedback only — fires while the user is filling the form,
    # updates the field on screen immediately. Does NOT write to DB
    # by itself (onchange never does).
    # ------------------------------------------------------------------
    @api.onchange('product_id')
    def _onchange_product_id_state_based_tax(self):
        for line in self:
            if not line.product_id:
                continue
            tax = line._get_state_based_tax()
            if tax:
                line.tax_ids = tax

    # ------------------------------------------------------------------
    # ACTUAL DB PERSISTENCE — this is what guarantees tax_ids is
    # stored the moment a product is added, no matter whether the
    # line came from the form UI, an import, an API call, or another
    # module calling create()/write() directly.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._apply_state_based_tax()
        return lines

    def write(self, vals):
        res = super().write(vals)
        if 'product_id' in vals or 'order_id' in vals:
            self._apply_state_based_tax()
        return res

    def _apply_state_based_tax(self):
        for line in self:
            if not line.product_id:
                continue
            tax = line._get_state_based_tax()
            if tax and tax not in line.tax_ids:
                line.tax_ids = [(6, 0, tax.ids)]