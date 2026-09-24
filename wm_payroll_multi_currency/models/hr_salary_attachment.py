# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.date_utils import start_of
from odoo.tools.misc import formatLang

from dateutil.relativedelta import relativedelta
from math import ceil

class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=False, related=False,
                                  default=lambda self: self.env.company.currency_id)

    # @api.constrains('currency_id')
    # def _check_currency(self):
    #     if any(attachment.currency_id != attachment.employee_ids[0].contract_id.currency_id for attachment in self.filtered(lambda x: x.employee_count == 1)):
    #         raise ValidationError(_("Salary attachment currency not match employee current contract currency."))

    # @api.depends('state', 'total_amount', 'monthly_amount', 'date_start')
    # def _compute_estimated_end(self):
    #     for record in self:
    #         if record.state not in ['close', 'cancel'] and record.has_total_amount and record.monthly_amount:
    #             record.date_estimated_end = start_of(record.date_start + relativedelta(months=ceil(record.remaining_amount / record.monthly_amount)), 'month')
    #             record.date_end = start_of(record.date_start + relativedelta(months=ceil(record.remaining_amount / record.monthly_amount)),
    #                 'month')
    #         else:
    #             record.date_estimated_end = False
    #             record.date_end = False
