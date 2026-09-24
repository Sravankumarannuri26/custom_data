from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    form16_ids = fields.One2many(
        'hr.employee.form16', 'employee_id', string='Form 16 Documents'
    )
    is_inr_currency = fields.Boolean(
        compute='_compute_is_inr_currency'
    )

    @api.depends('currency_id')
    def _compute_is_inr_currency(self):
        for emp in self:
            emp.is_inr_currency = emp.currency_id.name == 'INR'
