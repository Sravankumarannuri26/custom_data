# # Copyright 2017 ForgeFlow S.L.
# # License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
#
# from odoo import api, models
#
#
# class AccountTax(models.Model):
#     _inherit = "account.tax"
#
#     @api.model
#     def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
#         res = super()._prepare_base_line_for_taxes_computation(record, **kwargs)
#         if record and record._name == "account.move.line" and record.discount_fixed:
#             res["discount"] = record._get_discount_from_fixed_discount()
#         return res

# Copyright 2017 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)

from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _prepare_base_line_for_taxes_computation(self, record, **kwargs):
        """Override to apply fixed discount when computing taxes."""
        res = super()._prepare_base_line_for_taxes_computation(record, **kwargs)

        # Check if this is an account.move.line with a fixed discount
        if (record and
                record._name == "account.move.line" and
                hasattr(record, 'discount_fixed') and
                record.discount_fixed):
            # Use the calculated discount from fixed discount
            res["discount"] = record._get_discount_from_fixed_discount()

        return res
