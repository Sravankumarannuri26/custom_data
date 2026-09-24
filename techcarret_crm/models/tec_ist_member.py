# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class IstMember(models.Model):
    _name = 'ist.member'

    name = fields.Char('IST Member', copy=False, required=True)

    _sql_constraints = [('unique_ist_member', 'unique (name)', 'IST Member must be unique.')]


