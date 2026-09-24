from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import get_lang


class InvEditDesc(models.TransientModel):
    _name = "inv.edit.product.desc"
    _description = "Edit Product Desc"


    inv_prod_desc = fields.Char('Enter Desc', copy=False)

    def inv_confirm_product_line_desc(self):
        if self.env.context.get('active_model') == 'account.move.line':
            active_id = self.env.context.get('active_id')
            inv_line_id = self.env['account.move.line'].browse(active_id)
            name = ''
            if inv_line_id:
                if inv_line_id.rental_start_date and inv_line_id.rental_return_date:
                    retrun_datetime = inv_line_id.rental_return_date
                    s_date = inv_line_id.rental_start_date.strftime(get_lang(self.env).date_format)
                    r_date = retrun_datetime.strftime(get_lang(self.env).date_format)
                    prod_desc = str(self.inv_prod_desc) + ' \n' + str(s_date) +' TO '+str(r_date)
                    name = prod_desc
                else:
                    name = self.inv_prod_desc
                inv_line_id.name = name




