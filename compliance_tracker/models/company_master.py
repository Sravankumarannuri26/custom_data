from odoo import models, fields

class CompanyMasterForCompliance(models.Model):
    _name = 'compliance.company.master'
    _description = 'Company Master For Compliance'
    _order = 'name'

    name = fields.Char(string="Company Name", required=True)
    
