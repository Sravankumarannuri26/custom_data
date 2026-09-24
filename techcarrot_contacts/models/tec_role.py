# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class TecRole(models.Model):
    _name = 'tec.role'
    _description = 'TEC Role'

    name = fields.Char('Role', copy=False, required=True)

    # _sql_constraints = [('unique_tec_role', 'unique (name)', 'Role must be unique.')]
    # code change by sriman
    _name_unique = models.Constraint(
        'unique (name)',
        'Name must be unique!'
    )
