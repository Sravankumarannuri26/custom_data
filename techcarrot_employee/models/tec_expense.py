# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
from datetime import datetime
import re
import phonenumbers

class HrExpense(models.Model):
    _inherit = 'hr.expense'

    emp_code = fields.Char('Employee Code', copy=False)
    project_id = fields.Many2one('project.project', 'Project', copy=False)

    @api.model
    def create(self, vals):
        if 'emp_code' in vals and not vals.get('employee_id'):
            emp_code = vals['emp_code']
            employee = self.env['hr.employee'].search([('emp_code', '=', emp_code)], limit=1)
            if employee:
                vals['employee_id'] = employee.id
        return super(HrExpense, self).create(vals)
# .
