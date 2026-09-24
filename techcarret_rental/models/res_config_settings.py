# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    r_invoice_day = fields.Integer(string="Days")
    r_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', domain="[('parent_id', '=', False)]")
    r_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', domain="[('parent_id', '=', r_analytic_plan_id)]")
    s_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', domain="[('parent_id', '=', False)]")
    s_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', domain="[('parent_id', '=', s_analytic_plan_id)]")
    ss_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', domain="[('parent_id', '=', False)]")
    ss_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', domain="[('parent_id', '=', ss_analytic_plan_id)]")
    rental_journal_id = fields.Many2one('account.journal', 'Rental Journal', domain="[('type', '=', 'sale')]")
    subscription_journal_id = fields.Many2one('account.journal', 'Subscription Journal', domain="[('type', '=', 'sale')]")
    sales_journal_id = fields.Many2one('account.journal', 'Project Journal', domain="[('type', '=', 'sale')]")



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    r_invoice_day = fields.Integer(string="Days", related='company_id.r_invoice_day')
    r_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', related='company_id.r_analytic_plan_id', readonly=False, domain="[('parent_id', '=', False)]")
    r_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', related='company_id.r_analytic_sub_plan_id', readonly=False, domain="[('parent_id', '=', r_analytic_plan_id)]")
    s_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', related='company_id.s_analytic_plan_id', readonly=False, domain="[('parent_id', '=', False)]")
    s_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', related='company_id.s_analytic_sub_plan_id', readonly=False, domain="[('parent_id', '=', s_analytic_plan_id)]")
    ss_analytic_plan_id = fields.Many2one('account.analytic.plan', 'Plan', related='company_id.ss_analytic_plan_id', readonly=False, domain="[('parent_id', '=', False)]")
    ss_analytic_sub_plan_id = fields.Many2one('account.analytic.plan', 'Sub Plan', related='company_id.ss_analytic_sub_plan_id', readonly=False, domain="[('parent_id', '=', ss_analytic_plan_id)]")
    rental_journal_id = fields.Many2one('account.journal', 'Rental Journal', related='company_id.rental_journal_id', readonly=False, domain="[('type', '=', 'sale')]")
    subscription_journal_id = fields.Many2one('account.journal', 'Subscription Journal', related='company_id.subscription_journal_id', readonly=False, domain="[('type', '=', 'sale')]")
    sales_journal_id = fields.Many2one('account.journal', 'Project Journal', related='company_id.sales_journal_id', readonly=False, domain="[('type', '=', 'sale')]")