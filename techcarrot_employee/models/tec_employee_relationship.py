# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmployeeRelationship(models.Model):
    _name = 'employee.relationship'

    name = fields.Char('Employee Relationship Name', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_employee_relationship', 'unique (name)', 'Employee Relationship name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Employee Relation name must be unique!'
    )
