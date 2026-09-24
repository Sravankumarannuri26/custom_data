from odoo import models, fields, api

class ITDurationConfigWizard(models.TransientModel):
    _name = 'it.duration.config.wizard'
    _description = 'Social Media Duration Configuration'
    # To get duration of social media tickets
    duration = fields.Selection([
        ('3m', '3 Months'),
        ('6m', '6 Months'),
        ('12m', '1 Year')
    ], string="Access Duration", default='3m', required=True)

    def action_save(self):
        param = self.env['ir.config_parameter'].sudo()
        param.set_param('it_ticket.social_media_duration', self.duration)