# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.fields import Command
from odoo.tools import format_datetime, format_time, date_utils
from odoo.tools import get_lang, SQL
from odoo.exceptions import ValidationError
from datetime import datetime
# from dateutil import relativedelta


class ProjectMilestone(models.Model):
    _inherit = 'project.milestone'


    quantity_amount = fields.Float('Amount', copy=False)
    sale_line_amount = fields.Monetary(related='sale_line_id.price_subtotal', string='Price Total', copy=False)
    currency_id = fields.Many2one(related='sale_line_id.currency_id', string='Curency', copy=False)

    @api.onchange('quantity_amount')
    def _onchange_quantity_amount(self):
        sale_line_amount = self.sale_line_id.price_subtotal
        if self.quantity_amount > sale_line_amount:
            raise ValidationError(_("The given amount exceeded the sale line amount"))
        self.quantity_percentage = (self.quantity_amount / sale_line_amount)
        # self.quantity_percentage = (self.quantity_amount) * (100/sale_line_amount)

    @api.onchange('quantity_percentage')
    def _onchange_quantity_percentage(self):
        sale_line_amount = self.sale_line_id.price_subtotal
        self.quantity_amount = self.quantity_percentage * sale_line_amount







