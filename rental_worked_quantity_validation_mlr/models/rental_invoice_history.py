from odoo import models, api
from odoo.exceptions import ValidationError

class RentalInvoiceHistory(models.Model):
    _inherit = 'rental.invoice.history'

    @api.constrains('worked_days', 'planned_days')
    def _check_worked_days_limit(self):
        for rec in self:
            if rec.worked_days > rec.planned_days:
                raise ValidationError(" Worked Days cannot exceed Planned Days.")
