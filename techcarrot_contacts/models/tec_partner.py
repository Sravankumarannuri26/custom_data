# -*- coding: utf-8 -*-

from odoo import api, models, _, fields
from odoo.exceptions import ValidationError
import re

class ResPartner(models.Model):
    _inherit = 'res.partner'

    avg_time_spent = fields.Float('Average Time Spent (Minutes)', copy=False)
    partner_dob = fields.Date('Date of Birth', copy=False)
    first_name = fields.Char('First Name', copy=False)
    department = fields.Char('Department', copy=False)
    home_country_address = fields.Text('Home Country Address', copy=False)
    last_name = fields.Char('Last Name', copy=False)
    referrer = fields.Char(string="Referrer", help="Enter the website URL", widget='url')
    reporting_to_id = fields.Many2one('tec.reporting', string='Reporting To', copy=False)
    role_id = fields.Many2one('tec.role', string='Role', copy=False)
    secondary_email = fields.Char('Secondary Email', copy=False)
    tec_title = fields.Char('Title', copy=False)
    customer_code = fields.Char('Customer Code', copy=False)
    mapping_to_id = fields.Many2one('hr.employee', string='Mapping To', copy=False, 
                                    help="Employee that this contact is mapped to")
    # mobile field added by sriman
    mobile = fields.Char(copy=False)

    @api.constrains('secondary_email')
    def _check_email_validity(self):
        for record in self:
            if record.secondary_email:
                pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
                if not re.match(pattern, record.secondary_email):
                    raise ValidationError(
                        "Invalid email format for %s. Please ensure it follows the correct structure." % record.secondary_email)


    @api.constrains('customer_code')
    def _check_unique_customer_code(self):
        for record in self:
            existing_record = self.search([('customer_code', '=', record.customer_code), ('id', '!=', record.id)], limit=1)
            if existing_record:
                raise ValidationError("The Customer Code must be unique.")
