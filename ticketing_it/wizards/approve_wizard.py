from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class ItTicketApproveWizard(models.TransientModel):
    _name = 'it.ticket.approve.wizard'
    _description = 'Approve Ticket Wizard'

    ticket_id = fields.Many2one('it.ticket', required=True)
    comment = fields.Text(string='Comment')

    def approve_ticket(self):
        self.ensure_one()
        rec = self.ticket_id.sudo()
        _logger.info('APPROVAL: ticket=%s state=%s level=%s user=%s',
                     rec.name, rec.state, rec.workflow_level, self.env.user.name)

        # Remember which role is acting, so we know where it's safe to redirect
        # afterward — some roles (e.g. HR) lose read access to the ticket the
        # instant it leaves their stage, so we must not try to reload the same
        # record's form view after approval or Odoo throws an Access Error.
        acting_role = None

        # ── LINE MANAGER APPROVAL ───────────────────────────────────────────
        if rec.state == 'manager_approval':
            if self.env.user != rec.line_manager_id:
                raise UserError(_('Only the Line Manager (%s) can approve this ticket.')
                                 % (rec.line_manager_id.name or '?'))
            acting_role = 'line_manager'

            if self.comment:
                rec.sudo().write({'manager_remarks': self.comment})

            level = rec.workflow_level

            if level == '1':
                # Line Manager → IT Support (direct assign)
                it_user = rec.assigned_to_id
                notify_group_users = self.env['res.users']
                has_specific_group = False
                if not it_user:
                    it_user, notify_group_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                rec.with_context(bypass_assignment_check=True).write({
                    'state': 'assigned',
                    'assigned_to_id': it_user.id if it_user else False,
                })
                recipients = rec.employee_id.user_id
                if has_specific_group and notify_group_users:
                    recipients |= notify_group_users
                rec._notify('ticketing_it.email_template_it_assigned', recipients)
                msg = _('✅ Line Manager <b>%s</b> approved → Assigned to IT Support: <b>%s</b>') % (
                    self.env.user.name, it_user.name if it_user else 'N/A')

            elif level == '2':
                # Line Manager → IT Manager
                # Always resolve the CURRENT IT Manager group member here — do not
                # rely on whatever it_manager_id was set to at ticket creation time,
                # since group membership can change afterward and a stale value
                # would silently point to someone no longer in the group.
                mgr = rec._find_it_manager()
                if mgr:
                    rec.sudo().write({'state': 'it_approval', 'it_manager_id': mgr.id})
                else:
                    rec.with_context(bypass_assignment_check=True).write({'state': 'it_approval'})
                if rec.it_manager_id:
                    rec._notify('ticketing_it.email_template_it_approval', rec.it_manager_id)
                msg = _('✅ Line Manager <b>%s</b> approved → Forwarded to IT Manager: <b>%s</b>') % (
                    self.env.user.name, rec.it_manager_id.name if rec.it_manager_id else 'N/A')

            elif level == '3':
                # Line Manager → HR
                rec.with_context(bypass_assignment_check=True).write({'state': 'hr_approval'})
                if not rec.hr_approver_id:
                    rec._compute_hr_approver()
                # Notify ALL HR reviewers
                grp = self.env.ref('employee_profile_change_request.group_profile_change_hr_reviewer', raise_if_not_found=False)
                if grp:
                    self.env.cr.execute("""
                        SELECT ru.id FROM res_users ru
                        JOIN res_groups_users_rel rel ON rel.uid = ru.id
                        WHERE rel.gid = %s AND ru.active = true
                    """, (grp.id,))
                    hr_manager_ids = [r[0] for r in self.env.cr.fetchall()]
                    hr_managers = self.env['res.users'].sudo().browse(hr_manager_ids)
                    for hr_user in hr_managers:
                        rec._notify('ticketing_it.email_template_hr_approval', hr_user)
                msg = _('✅ Line Manager <b>%s</b> approved → Forwarded to HR: <b>%s</b>') % (
                    self.env.user.name, rec.hr_approver_id.name if rec.hr_approver_id else 'N/A')

            else:
                raise UserError(_('Unexpected workflow level for this ticket.'))

        # ── HR APPROVAL (level 3) ───────────────────────────────────────────
        elif rec.state == 'hr_approval':
            if not self.env.user.has_group('employee_profile_change_request.group_profile_change_hr_reviewer'):
                raise UserError(_('Only HR Managers can approve this ticket.'))
            acting_role = 'hr'
            it_user = rec.assigned_to_id
            notify_group_users = self.env['res.users']
            has_specific_group = False
            if not it_user:
                it_user, notify_group_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                if not it_user:
                    raise ValidationError(_('No IT Support user found to assign.'))
            rec.with_context(bypass_assignment_check=True).write({
                'state': 'assigned',
                'assigned_to_id': it_user.id,
            })
            recipients = rec.employee_id.user_id
            if has_specific_group and notify_group_users:
                recipients |= notify_group_users
            rec._notify('ticketing_it.email_template_it_assigned', recipients)
            msg = _('✅ HR <b>%s</b> approved → Assigned to IT Support: <b>%s</b>') % (
                self.env.user.name, it_user.name)

        # ── IT MANAGER APPROVAL (level 2) ───────────────────────────────────
        elif rec.state == 'it_approval':
            if not self.env.user.has_group('ticketing_it.group_it_manager'):
                raise UserError(_('Only IT Managers can approve this ticket.'))
            acting_role = 'it_manager'

            if self.comment:
                rec.sudo().write({'it_manager_remarks': self.comment})

            it_user = rec.assigned_to_id
            notify_group_users = self.env['res.users']
            has_specific_group = False
            if not it_user:
                it_user, notify_group_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                if not it_user:
                    raise ValidationError(_('No IT Support user found to assign.'))
            rec.with_context(bypass_assignment_check=True).write({
                'state': 'assigned',
                'assigned_to_id': it_user.id,
            })
            recipients = rec.employee_id.user_id
            if has_specific_group and notify_group_users:
                recipients |= notify_group_users
            rec._notify('ticketing_it.email_template_it_assigned', recipients)
            msg = _('✅ IT Manager <b>%s</b> approved → Assigned to IT Support: <b>%s</b>') % (
                self.env.user.name, it_user.name)

        else:
            raise UserError(_('This ticket cannot be approved in its current state (%s).') % rec.state)

        rec.activity_unlink(['mail.mail_activity_data_todo'])
        if self.comment:
            msg += _('<br/><b>Comment:</b> %s') % self.comment
        rec.message_post(body=msg, body_is_html=True,
                         author_id=self.env.user.partner_id.id,
                         subtype_xmlid='mail.mt_comment')
        _logger.info('APPROVAL DONE: ticket=%s new_state=%s', rec.name, rec.state)

        # ── SAFE REDIRECT ────────────────────────────────────────────────────
        # HR loses read access to the ticket the instant it leaves 'hr_approval'
        # (by design — HR only sees pending items). If we just close the wizard,
        # Odoo tries to re-render the ticket form behind it and throws an Access
        # Error, even though the approval itself succeeded. So for HR specifically,
        # redirect back to the "Pending HR Approval" list instead of the record.
        # ── SAFE REDIRECT ────────────────────────────────────────────────────
        if acting_role == 'hr':
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