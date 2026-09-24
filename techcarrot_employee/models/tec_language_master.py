# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class LanguageMaster(models.Model):
    _name = 'language.master'

    name = fields.Char('Language Master', copy=False, required=True)

    # code change by sriman
    # _sql_constraints = [('unique_language_master', 'unique (name)', 'Language Master name must be unique.')]

    _name_unique = models.Constraint(
        'unique (name)',
        'Language Master name must be unique!'
    )
