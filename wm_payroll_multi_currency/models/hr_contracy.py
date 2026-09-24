# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from odoo.exceptions import UserError

class HrContract(models.Model):
    _inherit = 'hr.employee'
    _description = 'Employee Contract'

    # override the currency_id and set (original attribute) readonly to False and related to False
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=False, related=False,
                                  default=lambda self: self.env.company.currency_id)

    # prevent user from changing the currency of the contract
    def write(self, vals):
        for contract in self:
            # payslips = self.env['hr.payslip'].search_count([('contract_id', '=', contract.id)])
            payslips = self.env['hr.payslip'].search_count([('employee_id',"=", self.id)])

            if 'currency_id' in vals and payslips > 0:
                raise UserError(_("Changing the currency will cause an errors in accounting \n"
                                "If you want to change the currency please create a new employee"))

        return super(HrContract, self).write(vals)

class HrVersion(models.Model):
    _inherit = 'hr.version'
    _description = 'HR Version inheritance'

    currency_id = fields.Many2one(string="Currency", related='employee_id.currency_id', readonly=True)
