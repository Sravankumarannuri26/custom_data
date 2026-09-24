from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    leave_approval_required = fields.Boolean(
        string="Require Manager Approval for Leave",
        default=False,
    )


    leave_hr_manager_id = fields.Many2one(
        'hr.employee',
        string="HR Manager (Leave Notifications)",
    )
    leave_delivery_head_id = fields.Many2one(
        'hr.employee',
        string="Delivery Head (Leave Notifications)",
    )

    leave_hr_department_email = fields.Char(
        string="HR Department Email (Leave Notifications)",
        default="Hr@techcarrot.ae",
    )