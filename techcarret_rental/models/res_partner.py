# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

# code changed by sriman as trying to create the new res.partner
class Partner(models.Model):
    # _inherit = ['res.partner']
    _inherit = 'res.partner'

    customer_code = fields.Char('Customer Code', copy=False, index='trigram', required=True, default=lambda self: self.env['ir.sequence'].next_by_code('res.partner') or _('New'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('customer_code', _("New")) == _("New"):
                vals['customer_code'] = self.env['ir.sequence'].next_by_code('res.partner') or _("New")
        return super(Partner, self).create(vals_list)