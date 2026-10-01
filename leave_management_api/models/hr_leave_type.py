from odoo import models, fields, api


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    x_is_frozen = fields.Boolean(
        string="Frozen Leave", compute='_compute_is_frozen', store=True,
    )

    @api.depends('name')
    def _compute_is_frozen(self):
        for lt in self:
            lt.x_is_frozen = (lt.name or '').strip().lower() == 'frozen leave'