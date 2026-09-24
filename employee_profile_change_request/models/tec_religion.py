# -*- coding: utf-8 -*-
from odoo import models, fields


class TecReligion(models.Model):
    _name = 'tec.religion'
    _description = 'Religion'
    _order = 'name'

    name = fields.Char(string='Religion', required=True, translate=True)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Religion name must be unique.'),
    ]