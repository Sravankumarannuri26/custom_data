# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class ExitReason(models.Model):
    _name = 'exit.reason'

    name = fields.Char('Exit Reason', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_exit_reason', 'unique (name)', 'Exit Reason name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Exit Reason name must be unique!'
    )
