# -*- coding: utf-8 -*-

from odoo import api, models, _, fields

class CrmPipelineInherit(models.Model):
    _inherit = 'crm.lead'

    type_id = fields.Many2one('deal.type', string='Type')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    annual_revenue = fields.Monetary('Annual Revenue', copy=False)
    brief_about_lead = fields.Text('Brief About the Lead', copy=False)
    converted_acc_id = fields.Many2one('res.partner', string='Converted Account')
    converted_deal_id = fields.Many2one('res.partner', string='Converted Deal')
    description = fields.Text('Description', copy=False)
    first_name = fields.Char('First Name', copy=False)
    last_name = fields.Char('Last Name', copy=False)
    industry_id = fields.Many2one('crm.industry', string='Industry')
    ist_member_id = fields.Many2one('ist.member', string='IST Member')
    lead_status_id = fields.Many2one('lead.status', string='Lead Status', copy=False)
    referrer = fields.Char(string="Referrer", help="Enter the website URL", widget='url')
    tec_title = fields.Char('Title', copy=False)
    stage_id = fields.Many2one('crm.stage', string='Stage')
    deal_category = fields.Char('Deal Category', compute='_compute_deal_category', store=True)
    forecast_category = fields.Char('Forecast Category', compute='_compute_forecast_category', store=True)

    @api.depends('stage_id')
    def _compute_deal_category(self):
        for record in self:
            if record.stage_id:  # If there is a stage_id set
                # Here, you can either pull a value from the stage or compute it based on stage logic
                record.deal_category = record.stage_id.name  # Example: using the stage's name
            else:
                record.deal_category = False

    @api.depends('stage_id')
    def _compute_forecast_category(self):
        for record in self:
            if record.stage_id:  # If there is a stage_id set
                # Example: using the stage's name for forecast category too
                record.forecast_category = record.stage_id.name  # Or any logic based on stage
            else:
                record.forecast_category = False

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        if self.stage_id and self.stage_id.name == 'Need Analysis':
            self.probability = 10
        if self.stage_id and self.stage_id.name == 'Proposal/Price Quote':
            self.probability = 50
        if self.stage_id and self.stage_id.name == 'Negotiation/Review':
            self.probability = 90
        if self.stage_id and self.stage_id.name == 'Closed Won':
            self.probability = 100
        if self.stage_id and self.stage_id.name == 'Closed Lost':
            self.probability = 0
        if self.stage_id and self.stage_id.name == 'No Bid':
            self.probability = 0
        if self.stage_id and self.stage_id.name == 'On Hold':
            self.probability = 0
        if self.stage_id and self.stage_id.name == 'Dropped by Customer':
            self.probability = 0
        # if self.stage_id and self.stage_id.name == 'New':
        #     self.probability = 0
        # if self.stage_id and self.stage_id.name == 'Qualified':
        #     self.probability = 0
        # if self.stage_id and self.stage_id.name == 'Proposition':
        #     self.probability = 0
        # if self.stage_id and self.stage_id.name == 'Won':
        #     self.probability = 0