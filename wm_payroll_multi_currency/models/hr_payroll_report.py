# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo import api, fields, models
from odoo.tools.sql import drop_view_if_exists, SQL


class HrPayrollReport(models.Model):
    _inherit = "hr.payroll.report"

    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True)

    def _select(self, additional_rules):
        return super()._select(additional_rules) + """,
                res_currency.id as currency_id
                """
    def _from(self, additional_rules):
        return super()._from(additional_rules) + """
                left join res_currency res_currency on (res_currency.id = c.currency_id)
               """

    def _group_by(self, additional_rules):
        return super()._group_by(additional_rules) + """,
                res_currency.id"""