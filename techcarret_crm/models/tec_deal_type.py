# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class DealType(models.Model):
    _name = 'deal.type'

    name = fields.Char('Type', copy=False, required=True)

    _sql_constraints = [('unique_deal_type', 'unique (name)', 'Deal Type must be unique.')]


