from odoo import models, fields

class LocationMasterForCompliance(models.Model):
    _name = 'compliance.location.master'
    _description = 'Location Master For Compliance'
    _order = 'name'

    name = fields.Char(string="Location Name", required=True)

