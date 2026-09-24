from odoo import models, fields
import random

class ComplianceProjectTag(models.Model):
    _name = 'compliance.project.tag'
    _description = 'Compliance Project Tag'

    name = fields.Char(required=True)
    color = fields.Integer(
        string="Color",
        default=lambda self: random.randint(1, 10)
    )
