from odoo import api, models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    @api.constrains("date_from", "date_to", "employee_id")
    def _check_date_state(self):
        # TEMPORARY ONLY
        return