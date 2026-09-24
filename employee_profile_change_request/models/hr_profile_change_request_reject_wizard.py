
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrProfileChangeRequestRejectWizard(models.TransientModel):
    _name = 'hr.profile.change.request.reject.wizard'
    _description = 'Reject Profile Change Request Wizard'

    request_id = fields.Many2one(
        comodel_name='hr.profile.change.request',
        string='Request Reference',
        required=True,
        readonly=True,
    )

    employee_name = fields.Char(
        string='Employee',
        related='request_id.employee_id.name',
        readonly=True,
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='This reason will be emailed to the employee and saved in audit trail.',
    )

    def action_confirm_reject(self):
        self.ensure_one()

        if not self.rejection_reason or not self.rejection_reason.strip():
            raise UserError(_(
                'Rejection reason is required. '
                'The employee will receive this reason by email.'
            ))

        req = self.request_id

        req.write({
            'state': 'rejected',
            'rejection_reason': self.rejection_reason.strip(),
            'reviewed_by': self.env.user.id,
            'review_date': fields.Datetime.now(),
        })

        # ── Mark overlay as rejected (keep submitted data, just change state) ──

        req.employee_id.sudo().write({
            'last_submission_state': 'rejected',
            'last_portal_submission': req.submitted_data,  # ← ADD THIS LINE
        })

        if hasattr(req, '_add_trail'):
            req._add_trail(
                action='rejected',
                note='Rejected by %s' % self.env.user.name,
                reason=self.rejection_reason.strip(),
            )

        if hasattr(req, '_send_mail_to_employee'):
            req._send_mail_to_employee('rejected')

        return {'type': 'ir.actions.act_window_close'}








