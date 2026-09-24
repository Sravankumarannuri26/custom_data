# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta


class HrEmployeePrivate(models.Model):
    _inherit = "hr.employee"

    work_entry_ids = fields.One2many(
        comodel_name='employee.workentry',
        inverse_name='employee_id',
        string="Work Entry",
        copy=True, auto_join=True)
    marital = fields.Selection(
        selection='_get_marital_status_selection',
        string='Marital Status',
        groups="hr.group_hr_user",
        default='single',
        required=False,
        tracking=True)

    def _get_marital_status_selection(self):
        return [
            ('single', _('Single')),
            ('married', _('Married')),
            ('cohabitant', _('Legal Cohabitant')),
            ('widower', _('Widower')),
            ('divorced', _('Divorced')),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        employees = super(HrEmployeePrivate, self).create(vals_list)
        if employees:
            for employee in employees:
                # Create a product template
                uom_obj = self.env['uom.uom'].search([('name', '=', 'Days')], limit=1)
                product_template_id = self.env['product.template'].create({
                    'name': employee.name,
                    'sale_ok': False,
                    'purchase_ok': False,
                    'rent_ok': True,
                    'type': 'service',
                    'is_storable': False,
                    'employee_id':employee.id,
                })
                if product_template_id:
                    product_template_id.name = employee.name
                    product_template_id.uom_id = uom_obj.id
                    # attribute_obj = self.env['product.attribute'].search([('name', '=', 'Shift')], limit=1)
                    # if attribute_obj:
                    #     self.env['product.template.attribute.line'].create({
                    #         'attribute_id': attribute_obj.id,
                    #         'product_tmpl_id': product_template_id.id,
                    #         'value_ids': [(6, 0, [attribute_obj.value_ids.ids[0]])],
                    #     })
        return employees

class WorkEntry(models.Model):
    _name = "employee.workentry"
    _description = 'Work Entry'

    def _get_year_selection(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1990, current_year + 8)]

    employee_id = fields.Many2one(comodel_name='hr.employee', string="Employee Reference", required=True, ondelete='cascade', index=True, copy=False)
    month = fields.Integer("Month")
    year = fields.Selection(selection='_get_year_selection', string='Year')
    rental_sale_id = fields.Many2one(comodel_name='sale.order', string="Rental Order")
    percent = fields.Float("Project Contribution(%)")
    worked_days = fields.Integer("Worked QTY")
    analytic_account_id = fields.Many2one('account.analytic.account', copy=False,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=?', company_id)]",
                                 ondelete='set null')
    import_id = fields.Many2one('import.attendance.line', 'Attendance line')
    state = fields.Selection([('imported', 'Imported'), ('invoiced', 'Invoiced')], default='imported', string="State")
