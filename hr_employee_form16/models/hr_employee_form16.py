from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrEmployeeForm16(models.Model):
    _name = 'hr.employee.form16'
    _description = 'Employee Form 16'
    _order = 'financial_year desc'
    _rec_name = 'display_name'

    employee_id = fields.Many2one(
        'hr.employee', string='Employee', required=True, ondelete='cascade'
    )
    company_id = fields.Many2one(
        related='employee_id.company_id', store=True, readonly=True
    )
    financial_year = fields.Char(
        string='Financial Year', required=True,
        help="e.g. 2024-2025"
    )
    form16_pdf = fields.Binary(string='Form 16 PDF', required=True, attachment=True)
    form16_filename = fields.Char(string='File Name')
    display_name = fields.Char(compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('unique_employee_year',
         'unique(employee_id, financial_year)',
         'Form 16 for this employee and financial year already exists!')
    ]

    @api.depends('employee_id', 'financial_year')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.employee_id.name or ''} - {rec.financial_year or ''}"

    @api.constrains('employee_id')
    def _check_inr_currency(self):
        for rec in self:
            if rec.employee_id.currency_id.name != 'INR':
                raise ValidationError(
                    "Form 16 can only be uploaded for employees with INR currency."
                )
