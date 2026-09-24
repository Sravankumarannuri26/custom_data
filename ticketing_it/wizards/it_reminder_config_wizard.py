from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ITReminderConfigWizard(models.TransientModel):
    _name = 'it.reminder.config.wizard'
    _description = 'IT Reminder Configuration Wizard'

    # Number of days between reminder emails for IT tickets
    reminder_days = fields.Integer(
        string="Reminder Interval (Days)",
        required=True,
        default=1
    )

    @api.model
    def default_get(self, fields_list):
        """Load saved reminder configuration from system parameters."""
        res = super().default_get(fields_list)

        # Fetch stored reminder interval from system settings
        ICP = self.env['ir.config_parameter'].sudo()
        saved_days = ICP.get_param('ticketing_it.reminder_days')

        # Set default value in wizard
        res['reminder_days'] = int(saved_days) if saved_days else 1
        return res

    def action_save(self):
        """Save reminder interval into system configuration."""

        # Validate input value
        if self.reminder_days <= 0:
            raise ValidationError(_("Reminder days must be greater than 0."))

        # Save into system parameters (persistent config)
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('ticketing_it.reminder_days', self.reminder_days)

        # Close wizard after saving
        return {'type': 'ir.actions.act_window_close'}