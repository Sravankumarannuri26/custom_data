# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class CrmIndustry(models.Model):
    _name = 'crm.industry'

    name = fields.Char('Industry', copy=False, required=True)

    _sql_constraints = [('unique_crm_industry', 'unique (name)', 'Industry must be unique.')]


