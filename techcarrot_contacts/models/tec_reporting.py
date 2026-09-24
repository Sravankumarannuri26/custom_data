# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class TecReporting(models.Model):
    _name = 'tec.reporting'
    _description = 'TEC Reporting'

    name = fields.Char('Reporting To', copy=False, required=True)

    # _sql_constraints = [('unique_tec_reporting', 'unique (name)', 'Reporting To must be unique.')]
    # code change by sriman
    _name_unique = models.Constraint(
        'unique (name)',
        'Name must be unique!'
    )

