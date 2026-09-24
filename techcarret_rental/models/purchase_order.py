# -*- coding: utf-8 -*-
import pytz
import calendar
from math import ceil
from dateutil.relativedelta import relativedelta
from setuptools.dist import sequence
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta
from odoo.fields import Command
from odoo.tools import format_datetime, format_time, date_utils
from pytz import timezone, UTC
from odoo.tools import get_lang, SQL
from odoo.exceptions import ValidationError
from datetime import datetime
# from dateutil import relativedelta
import base64


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'


    deliver_partner_id = fields.Many2one('res.partner', 'Deliver To', copy=False)


    def action_rfq_send(self):
        res = super(PurchaseOrder, self).action_rfq_send()
        for order in self:
            pdf_content = \
                self.env['ir.actions.report']._render('techcarret_rental.action_generate_techcarrot_purchase_report',
                                                      self.ids)[0]
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            name = ''
            if self.state not in ['purchase', 'done']:
                name = 'Request For Quotation'
            else:
                name = 'Purchase Order'
            attachment = self.env['ir.attachment'].create({
                'name': name + ' - ' + self.name,
                'type': 'binary',
                'datas': pdf_base64,
                'res_model': 'purchase.order',
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            if res.get('context'):
                res['context'].setdefault('default_attachment_ids', []).append(attachment.id)
        return res


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"


    def _check_qty_whole_fraction_po_line(self):
        qty = self.product_qty
        frac_qty = str(self.product_qty).split('.')[1]
        frac_qty = int(frac_qty)
        if frac_qty == 0:
            qty = "{:,.2f}".format(self.product_qty)
        else:
            digits = f"{self.product_qty:.6f}"
            if '.' in digits:
                qty = digits.rstrip('0').rstrip('.')
        return qty

