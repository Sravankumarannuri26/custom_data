from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import get_lang


class EditDesc(models.TransientModel):
    _name = "edit.product.desc"
    _description = "Edit Product Desc"


    prod_desc = fields.Char('Enter Desc', copy=False)

    def confirm_product_line_desc(self):
        if self.env.context.get('active_model') == 'sale.order.line':
            active_id = self.env.context.get('active_id')
            sale_line_id = self.env['sale.order.line'].browse(active_id)
            if sale_line_id:
                sale_line_id.name = self.prod_desc




