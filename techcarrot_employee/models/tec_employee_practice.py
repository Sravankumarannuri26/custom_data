# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmployeePractice(models.Model):
    _name = 'employee.practice'

    name = fields.Char('Practice', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_employee_practice', 'unique (name)', 'Practice name must be unique.')]
    _name_unique = models.Constraint(
        'unique (name)',
        'Practice name must be unique!'
    )

