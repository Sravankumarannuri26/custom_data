# -*- coding: utf-8 -*-
from odoo import fields, models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    employee_type = fields.Selection(
        selection=[
            ('employee', 'Employee'),
            ('worker', 'Worker'),
            ('student', 'Student'),
            ('trainee', 'Trainee'),
            ('contractor', 'Contractor'),
            ('freelance', 'Freelancer'),
        ],
        string='Employment Category',  # Changed label
        default='employee',
        required=True,
        groups="hr.group_hr_user",
        tracking=True,
        help="Categorize your Employees by type."
    )