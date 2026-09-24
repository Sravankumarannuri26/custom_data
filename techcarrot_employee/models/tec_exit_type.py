# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class ExitType(models.Model):
    _name = 'exit.type'

    name = fields.Char('Exit Type', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_exit_type', 'unique (name)', 'Exit Type name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Exit Type name must be unique!'
    )
