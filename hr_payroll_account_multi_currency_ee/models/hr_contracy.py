# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError

class HrContract(models.Model):
    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    # override the currency_id and set (original attribute) readonly to False and related to False
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=False, related=False,
                                  default=lambda self: self.env.user.company_id.currency_id)

    # prevent user from changing the currency of the contract
    def write(self, vals):
        if 'currency_id' in vals:
            raise UserError("Changing the currency will cause an errors in accounting \n"
                            "If you want to change the currency please create a new contract")

        return super(HrContract, self).write(vals)
