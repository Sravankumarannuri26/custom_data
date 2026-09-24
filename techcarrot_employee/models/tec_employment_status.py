# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class EmploymentStatus(models.Model):
    _name = 'employment.status'

    name = fields.Char('Employee Status', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_employment_status', 'unique (name)', 'Employment Status name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Employee Status name must be unique!'
    )

