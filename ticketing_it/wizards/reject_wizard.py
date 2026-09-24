from odoo import models, fields, _


class ITTicketRejectWizard(models.TransientModel):
    _name = 'it.ticket.reject.wizard'
    _description = 'Reject Ticket Wizard'

    ticket_id = fields.Many2one(
        'it.ticket',
        string='Ticket',
        required=True
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True
    )

    def action_reject(self):
        self.ensure_one()

        ticket = self.ticket_id

        # Remember whether the current user is HR
        is_hr = self.env.user.has_group(
            'employee_profile_change_request.group_profile_change_hr_reviewer'
        )

        # Execute rejection
        ticket.sudo().do_reject(self.rejection_reason)

        # HR loses access after rejection, so don't close the wizard.
        if is_hr:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Pending HR Approval'),
                'res_model': 'it.ticket',
                'view_mode': 'list,form',
                'views': [(False, 'list'), (False, 'form')],
                'domain': [('state', '=', 'hr_approval')],
                'target': 'current',
            }

        return {'type': 'ir.actions.act_window_close'}