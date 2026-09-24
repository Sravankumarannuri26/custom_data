from odoo import api, fields, models
from odoo.osv import expression


class SaleOrder(models.Model):
    _inherit = "sale.order"

    po_no = fields.Char('PO No', )



