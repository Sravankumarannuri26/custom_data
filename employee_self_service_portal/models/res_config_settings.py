from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    leave_approval_required = fields.Boolean(
        related='company_id.leave_approval_required',
        readonly=False,
        string="Require Manager Approval for Leave",
    )
    leave_hr_manager_id = fields.Many2one(
        related='company_id.leave_hr_manager_id',
        readonly=False,
        string="HR Manager (Leave Notifications)",
    )
    leave_delivery_head_id = fields.Many2one(
        related='company_id.leave_delivery_head_id',
        readonly=False,
        string="Delivery Head (Leave Notifications)",
    )
    leave_hr_department_email = fields.Char(
        related='company_id.leave_hr_department_email',
        readonly=False,
        string="HR Department Email (Leave Notifications)",
    )