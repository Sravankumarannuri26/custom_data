# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class LeadStatus(models.Model):
    _name = 'lead.status'

    name = fields.Char('Lead Status', copy=False, required=True)

    _sql_constraints = [('unique_lead_status', 'unique (name)', 'Lead Status must be unique.')]


