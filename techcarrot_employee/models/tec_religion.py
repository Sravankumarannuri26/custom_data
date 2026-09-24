# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class TecReligion(models.Model):
    _name = 'tec.religion'

    name = fields.Char('Religion', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_tec_religion', 'unique (name)', 'Religion name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Religion name must be unique!'
    )
