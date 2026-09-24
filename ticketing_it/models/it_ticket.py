# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, AccessError
from collections import defaultdict
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ITTicketType(models.Model):
    _name = 'it.ticket.type'
    _description = 'IT Ticket Type'
    _rec_name = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Ticket type code must be unique!')
    ]


class ITTicket(models.Model):
    _name = 'it.ticket'
    _description = 'IT Support Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # Basic Fields
    name = fields.Char(string='Ticket Number', required=True, copy=False,
                       readonly=True, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
                                  default=lambda self: self._get_current_employee(), tracking=True)
    partner_id = fields.Many2one('res.partner', related='employee_id.user_id.partner_id',
                                 store=True, readonly=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id',
                                    store=True, readonly=True)

    # Details
    ticket_type_id = fields.Many2one('it.ticket.type', string='Ticket Type',
                                     required=True, tracking=True)
    priority = fields.Selection([
        ('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Urgent'),
    ], default='1', required=True, tracking=True, string='Priority')
    subject = fields.Char(required=True, tracking=True, string='Subject')
    description = fields.Html(required=True, string='Description')
    required_date = fields.Date(string='Required By Date')
    user_id = fields.Many2one('res.users', string="Assigned To")

    # State
    # Workflow levels from Excel:
    #   0 = direct IT Support
    #   1 = Line Manager → IT Support
    #   2 = Line Manager → IT Manager → IT Support
    #   3 = Line Manager → HR → IT Support
    state = fields.Selection([
        ('draft', 'Draft'),
        ('manager_approval', 'Pending Line Manager'),
        ('hr_approval', 'Pending HR'),
        ('it_approval', 'Pending IT Manager'),
        ('assigned', 'Assigned to IT'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
    ], default='manager_approval', tracking=True, string='Status')

    # Approvers
    line_manager_id = fields.Many2one('res.users', string='Line Manager', tracking=True)
    it_manager_id = fields.Many2one('res.users', compute='_compute_it_manager',
                                    store=True, string='IT Manager')
    hr_approver_id = fields.Many2one('res.users', compute='_compute_hr_approver',
                                     store=True, string='HR Approver')
    assigned_to_id = fields.Many2one('res.users', string='Assigned To (IT Support)', tracking=True)

    # Workflow level (stored)
    workflow_level = fields.Selection([
        ('0', '0'), ('1', '1'), ('2', '2'), ('3', '3'),
    ], compute='_compute_workflow_level', store=True)

    # Dates
    submitted_date = fields.Date(readonly=True, string='Submitted Date')
    manager_approval_date = fields.Date(readonly=True, string='Manager Approval Date')
    hr_approval_date = fields.Date(readonly=True, string='HR Approval Date')
    it_approval_date = fields.Date(readonly=True, string='IT Approval Date')
    done_date = fields.Date(readonly=True, string='Completion Date')
    last_reminder_sent = fields.Date(readonly=True, string='Last Reminder Sent')
    month_solved = fields.Char(compute='_compute_month_solved', store=True, string='Month')

    # Social media duration
    duration = fields.Selection([
        ('3m', '3 Months'), ('6m', '6 Months'), ('12m', '1 Year'), ('custom', 'Custom Date')
    ], default='3m', string='Access Duration')
    custom_expiry_date = fields.Date(string='Custom Date')
    access_start_date = fields.Date()
    access_end_date = fields.Date()
    access_finish_date = fields.Date()

    # Rejection
    rejection_reason = fields.Text(readonly=True, string='Rejection Reason')
    rejected_by_id = fields.Many2one('res.users', readonly=True, string='Rejected By')
    rejected_date = fields.Datetime(readonly=True, string='Rejection Date')

    # Approval remarks — kept on dedicated fields (separate from chatter) so the
    # next approver in the chain can see exactly what the previous approver said.
    manager_remarks = fields.Text(readonly=True, string='Line Manager Remarks')
    it_manager_remarks = fields.Text(readonly=True, string='IT Manager Remarks')

    # Helper fields
    allowed_it_users = fields.Many2many('res.users', compute='_compute_allowed_it_users')
    show_it_manager = fields.Boolean(compute='_compute_show_to_it_manager', store=True)
    show_it_teams = fields.Boolean(compute='_compute_show_to_it_team', store=True)
    is_line_manager = fields.Boolean(compute='_compute_user_roles')
    is_it_manager = fields.Boolean(compute='_compute_user_roles')
    can_edit = fields.Boolean(compute='_compute_can_edit', store=False)
    is_social_media = fields.Boolean(compute='_compute_is_social_media')

    # Reporting
    manager_processing_days = fields.Float(compute='_compute_processing_days', store=True, aggregator='avg')
    it_processing_days = fields.Float(compute='_compute_processing_days', store=True, aggregator='avg')
    it_team_processing_days = fields.Float(compute='_compute_processing_days', store=True, aggregator='avg')
    status_category = fields.Selection([('open', 'Open'), ('closed', 'Closed')],
                                       compute='_compute_status_category', store=True)
    open_count = fields.Integer(compute='_compute_counts', store=True)
    closed_count = fields.Integer(compute='_compute_counts', store=True)

    # ─── Computed Fields ────────────────────────────────────────────────────

    @api.depends('ticket_type_id')
    def _compute_workflow_level(self):
        type_ids = [rec.ticket_type_id.id for rec in self if rec.ticket_type_id]
        level_map = {}
        if type_ids:
            self.env.cr.execute(
                "SELECT ticket_type_id, workflow_level FROM it_ticket_workflow_config WHERE ticket_type_id = ANY(%s)",
                (type_ids,)
            )
            level_map = {r[0]: r[1] for r in self.env.cr.fetchall()}
        for rec in self:
            rec.workflow_level = level_map.get(rec.ticket_type_id.id, '0') if rec.ticket_type_id else '0'

    @api.depends('department_id')
    def _compute_it_manager(self):
        it_manager = self._find_it_manager()
        for rec in self:
            rec.it_manager_id = it_manager if it_manager else False

    @api.depends('ticket_type_id')
    def _compute_hr_approver(self):
        hr_manager = self._find_hr_manager()
        for rec in self:
            rec.hr_approver_id = hr_manager if hr_manager else False

    @api.depends('state')
    def _compute_show_to_it_manager(self):
        for t in self:
            t.show_it_manager = t.state not in ['draft', 'manager_approval', 'hr_approval']

    @api.depends('state')
    def _compute_show_to_it_team(self):
        for t in self:
            t.show_it_teams = t.state in ['assigned', 'in_progress', 'done']

    @api.depends()
    def _compute_allowed_it_users(self):
        grp = self.env.ref('ticketing_it.group_it_team', raise_if_not_found=False)
        users = grp.user_ids if grp else self.env['res.users']
        for t in self:
            t.allowed_it_users = users

    def _user_has_it_access(self, user):
        """True if this user should see IT-support portal pages/cards at all
        (dashboard card, /my/it-tickets). Deliberately NOT based on implied_ids
        (that pollutes real group membership — see security.xml note) and NOT a
        hardcoded list of group names either: it checks the flat IT Team group,
        OR membership in ANY group that is currently set as the IT Support Group
        on ANY sub-category. So a brand new group works here the moment it's
        picked in that dropdown on some Ticket Type — no code change, ever.
        This only gates whether IT pages/cards are shown; which SPECIFIC tickets
        that user can then see is still decided per-ticket by _resolve_it_support
        / the ir.rule, based on direct membership in that ticket's own group.
        """
        if user.has_group('ticketing_it.group_it_team'):
            return True
        configured_group_ids = self.env['it.ticket.type'].sudo().search(
            [('it_support_group_id', '!=', False)]).mapped('it_support_group_id').ids
        if not configured_group_ids:
            return False
        return bool(self.env['res.groups'].sudo().search_count(
            [('id', 'in', configured_group_ids), ('user_ids', '=', user.id)]))

    def _resolve_it_support(self, ticket_type_id):
        """Resolve (assignee_user, notify_users, has_specific_group) for a ticket
        of this sub-category.

        Sub-category routing: if the it.ticket.type has an it_support_group_id set,
        that group's members are used instead of the flat 'IT Team' group — the
        first member becomes the assignee (ticket owner), and ALL members are
        returned as notify_users so the whole group gets the email. has_specific_group
        is True only in this case.

        If no group is configured on the sub-category, this still falls back to the
        flat ticketing_it.group_it_team group for ASSIGNMENT (so the ticket still has
        an owner and the workflow keeps moving) — but has_specific_group is False, and
        callers should NOT email IT support in that case. IT only starts receiving
        emails once a specific group has been set for that sub-category.
        """
        it_type = self.env['it.ticket.type'].sudo().browse(ticket_type_id) if ticket_type_id else False
        grp = it_type.it_support_group_id if it_type else False
        has_specific_group = bool(grp)
        if not grp:
            grp = self.env.ref('ticketing_it.group_it_team', raise_if_not_found=False)
        users = grp.sudo().user_ids if grp else self.env['res.users']
        if it_type and it_type.it_support_id and it_type.it_support_id in users:
            # An explicit default user for this sub-category still wins the
            # assignment, but the rest of the resolved group is still notified.
            assignee = it_type.it_support_id
        else:
            assignee = users[:1]
        return assignee, users, has_specific_group

    @api.depends('line_manager_id', 'state')
    def _compute_user_roles(self):
        for rec in self:
            rec.is_line_manager = (rec.line_manager_id == self.env.user) if rec.line_manager_id else False
            rec.is_it_manager = self.env.user.has_group('ticketing_it.group_it_manager')

    @api.depends('state', 'assigned_to_id', 'line_manager_id')
    def _compute_can_edit(self):
        for rec in self:
            user = self.env.user
            rec.can_edit = (
                (rec.state == 'it_approval' and user.has_group('ticketing_it.group_it_manager')) or
                rec.state in ['done', 'rejected']
            )

    def _compute_is_social_media(self):
        ref = self.env.ref('ticketing_it.type_social', raise_if_not_found=False)
        for rec in self:
            rec.is_social_media = (rec.ticket_type_id == ref) if ref else False

    @api.depends('state')
    def _compute_status_category(self):
        for rec in self:
            rec.status_category = 'closed' if rec.state in ['done', 'rejected'] else 'open'

    @api.depends('state')
    def _compute_counts(self):
        for rec in self:
            rec.open_count = 1 if rec.status_category == 'open' else 0
            rec.closed_count = 1 if rec.status_category == 'closed' else 0

    @api.depends('submitted_date', 'manager_approval_date', 'it_approval_date', 'done_date')
    def _compute_processing_days(self):
        for rec in self:
            rec.manager_processing_days = (
                (rec.manager_approval_date - rec.submitted_date).days
                if rec.submitted_date and rec.manager_approval_date else 0.0)
            rec.it_processing_days = (
                (rec.it_approval_date - rec.manager_approval_date).days
                if rec.manager_approval_date and rec.it_approval_date else 0.0)
            rec.it_team_processing_days = (
                (rec.done_date - rec.it_approval_date).days
                if rec.it_approval_date and rec.done_date else 0.0)

    @api.depends('done_date')
    def _compute_month_solved(self):
        for rec in self:
            rec.month_solved = rec.done_date.strftime('%B %Y') if rec.done_date else 'N/A'

    # ─── Helpers ────────────────────────────────────────────────────────────

    def _get_current_employee(self):
        return self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)

    def _get_workflow_level(self, ticket_type_id):
        if not ticket_type_id:
            return '0'
        self.env.cr.execute(
            "SELECT workflow_level FROM it_ticket_workflow_config WHERE ticket_type_id = %s LIMIT 1",
            (ticket_type_id,)
        )
        row = self.env.cr.fetchone()
        return row[0] if row else '0'

    def _find_it_manager(self):
        grp = self.env.ref('ticketing_it.group_it_manager', raise_if_not_found=False)
        if not grp:
            return False
        self.env.cr.execute("""
            SELECT ru.id FROM res_users ru
            JOIN res_groups_users_rel rel ON rel.uid = ru.id
            WHERE rel.gid = %s AND ru.active = true
            ORDER BY ru.id LIMIT 1
        """, (grp.id,))
        row = self.env.cr.fetchone()
        return self.env['res.users'].sudo().browse(row[0]) if row else False

    def _find_hr_manager(self):
        grp = self.env.ref('employee_profile_change_request.group_profile_change_hr_reviewer', raise_if_not_found=False)
        if not grp:
            return False
        self.env.cr.execute("""
            SELECT ru.id FROM res_users ru
            JOIN res_groups_users_rel rel ON rel.uid = ru.id
            WHERE rel.gid = %s AND ru.active = true
            ORDER BY ru.id LIMIT 1
        """, (grp.id,))
        row = self.env.cr.fetchone()
        return self.env['res.users'].sudo().browse(row[0]) if row else False

    def _compute_access_url(self):
        super()._compute_access_url()
        for ticket in self:
            ticket.access_url = '/my/tickets/%s' % ticket.id

    def _notify(self, template_xmlid, users):
        """Send one notification email to one or more users, logging a
        single chatter entry (not one per recipient)."""
        recipients = users.filtered(lambda u: u and u.email) if hasattr(users, 'filtered') \
            else self.env['res.users'].browse([u.id for u in users if u and u.email])
        if not recipients:
            return
        tmpl = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not tmpl:
            _logger.warning('IT Ticket: template %s not found', template_xmlid)
            return
        try:
            tmpl.send_mail(self.id, force_send=True, email_values={
                'email_to': ','.join(recipients.mapped('email')),
                'recipient_ids': [(5, 0, 0)],
                'partner_ids': [(5, 0, 0)],
            })
        except Exception as e:
            _logger.error('IT Ticket %s: notify failed for %s — %s', self.name, recipients.mapped('name'), e)

    # ─── CREATE ─────────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('it.ticket') or _('New')

            ticket_type_id = vals.get('ticket_type_id')
            level = self._get_workflow_level(ticket_type_id)
            vals['workflow_level'] = level
            vals['submitted_date'] = fields.Date.today()

            # Auto-resolve line_manager_id from employee if not explicitly passed
            # (skip entirely for Level 0 — Line Manager is not part of that flow at all)
            if level != '0' and not vals.get('line_manager_id') and vals.get('employee_id'):
                emp = self.env['hr.employee'].sudo().browse(vals['employee_id'])
                if emp:
                    if emp.line_manager_id and emp.line_manager_id.user_id:
                        vals['line_manager_id'] = emp.line_manager_id.user_id.id

            # True if this ticket needed a Line Manager step but the employee
            # has none on record (e.g. CEO / top of the org chart) — such
            # tickets used to get permanently stuck at 'manager_approval'
            # since no one could ever match rec.line_manager_id there.
            no_line_manager = level != '0' and not vals.get('line_manager_id')

            if level == '0':
                # Direct to IT Support — actual assignee/group resolved after
                # create() below, once the record (and its ticket_type_id) exists.
                vals['state'] = 'assigned'
            elif no_line_manager:
                # No line manager to approve — skip that step and start the
                # ticket at whichever stage comes next for this workflow level.
                if level == '3':
                    vals['state'] = 'hr_approval'
                elif level == '2':
                    vals['state'] = 'it_approval'
                else:  # level == '1'
                    vals['state'] = 'assigned'
                vals['manager_approval_date'] = fields.Date.today()
            else:
                # All multi-step flows start at Line Manager
                vals['state'] = 'manager_approval'

        records = super().create(vals_list)

        for rec in records:
            level = rec.workflow_level
            if rec.state == 'assigned':
                # Level 0, or Level 1 with no line manager — goes straight to IT Support
                assignee, notify_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                if assignee:
                    rec.sudo().write({'assigned_to_id': assignee.id})
                recipients = rec.employee_id.user_id
                if has_specific_group and notify_users:
                    recipients |= notify_users
                rec._notify('ticketing_it.email_template_it_assigned', recipients)
            elif rec.state == 'it_approval':
                # Level 2 with no line manager — skipped straight to IT Manager
                if rec.it_manager_id:
                    rec._notify('ticketing_it.email_template_it_approval', rec.it_manager_id)
                else:
                    _logger.warning('IT Ticket %s: no line manager AND no IT manager resolved for %s', rec.name, rec.employee_id.name)
            elif rec.state == 'hr_approval':
                # Level 3 with no line manager — skipped straight to HR
                if rec.hr_approver_id:
                    rec._notify('ticketing_it.email_template_hr_approval', rec.hr_approver_id)
                else:
                    _logger.warning('IT Ticket %s: no line manager AND no HR approver resolved for %s', rec.name, rec.employee_id.name)
            else:
                # Normal flow — notify line manager (levels 1, 2, 3 all start here)
                if rec.line_manager_id:
                    rec._notify('ticketing_it.email_template_manager_approval', rec.line_manager_id)
                else:
                    _logger.warning('IT Ticket %s: no line manager for %s — ticket created in pending state', rec.name, rec.employee_id.name)

            if rec.ticket_type_id.code == 'social_media':
                duration = self.env['ir.config_parameter'].sudo().get_param(
                    'it_ticket.social_media_duration', '3m')
                rec.duration = duration

        return records

    # ─── WRITE ──────────────────────────────────────────────────────────────

    def write(self, vals):
        # Guard IT support assignment
        if 'assigned_to_id' in vals:
            if not (self.env.user.has_group('ticketing_it.group_it_manager') or
                    self.env.context.get('bypass_assignment_check') or
                    self.env.su):
                raise AccessError(_('Only IT Manager can assign tickets.'))

        # Track approval dates when LEAVING a state
        if 'state' in vals:
            new_state = vals['state']
            today = fields.Date.today()
            for rec in self:
                if rec.state == 'manager_approval' and new_state != 'manager_approval':
                    if not rec.manager_approval_date:
                        vals['manager_approval_date'] = today
                if rec.state == 'hr_approval' and new_state != 'hr_approval':
                    if not rec.hr_approval_date:
                        vals['hr_approval_date'] = today
                if rec.state == 'it_approval' and new_state != 'it_approval':
                    if not rec.it_approval_date:
                        vals['it_approval_date'] = today

        return super().write(vals)

    # ─── WORKFLOW ACTIONS ────────────────────────────────────────────────────

    def action_submit(self):
        """Called by portal auto-submit automation or manual submit."""
        for rec in self.filtered(lambda r: r.state == 'draft'):
            level = self._get_workflow_level(rec.ticket_type_id.id)
            if level == '0':
                assignee, notify_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                rec.write({'state': 'assigned',
                           'assigned_to_id': assignee.id if assignee else False,
                           'submitted_date': fields.Date.today()})
                recipients = rec.employee_id.user_id
                if has_specific_group and notify_users:
                    recipients |= notify_users
                if recipients:
                    rec._notify('ticketing_it.email_template_it_assigned', recipients)
            elif not rec.line_manager_id:
                # No line manager on record (e.g. CEO / top of the org chart) —
                # skip that step and start at whichever stage comes next.
                if level == '3':
                    next_state = 'hr_approval'
                elif level == '2':
                    next_state = 'it_approval'
                else:  # level == '1'
                    next_state = 'assigned'
                rec.write({'state': next_state, 'submitted_date': fields.Date.today(),
                           'manager_approval_date': fields.Date.today()})
                if next_state == 'assigned':
                    assignee, notify_users, has_specific_group = rec._resolve_it_support(rec.ticket_type_id.id)
                    if assignee:
                        rec.write({'assigned_to_id': assignee.id})
                    recipients = rec.employee_id.user_id
                    if has_specific_group and notify_users:
                        recipients |= notify_users
                    rec._notify('ticketing_it.email_template_it_assigned', recipients)
                elif next_state == 'it_approval' and rec.it_manager_id:
                    rec._notify('ticketing_it.email_template_it_approval', rec.it_manager_id)
                elif next_state == 'hr_approval' and rec.hr_approver_id:
                    rec._notify('ticketing_it.email_template_hr_approval', rec.hr_approver_id)
                else:
                    _logger.warning('IT Ticket %s: no line manager AND no fallback approver resolved for %s', rec.name, rec.employee_id.name)
            else:
                rec.write({'state': 'manager_approval', 'submitted_date': fields.Date.today()})
                if rec.line_manager_id:
                    rec._notify('ticketing_it.email_template_manager_approval', rec.line_manager_id)
                else:
                    _logger.warning('IT Ticket %s: no line manager for %s', rec.name, rec.employee_id.name)

    def action_manager_approve(self):
        self.ensure_one()
        rec = self.sudo()
        if self.env.user != rec.line_manager_id:
            raise UserError(_('Only the line manager (%s) can approve this ticket.') % rec.line_manager_id.name)
        return self._open_approve_wizard()

    def action_it_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('ticketing_it.group_it_manager'):
            raise UserError(_('Only IT managers can approve this ticket.'))
        return self.sudo()._open_approve_wizard()

    def action_hr_approve(self):
        self.ensure_one()
        if not self.env.user.has_group('employee_profile_change_request.group_profile_change_hr_reviewer'):
            raise UserError(_('Only HR Managers can approve this ticket.'))
        return self.sudo()._open_approve_wizard()

    def _open_approve_wizard(self):
        return {
            'name': _('Approve Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket.approve.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id},
        }

    def action_reject(self):
        self.ensure_one()
        self._check_reject_access()
        return {
            'name': _('Reject Ticket'),
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_ticket_id': self.id},
        }

    def _check_reject_access(self):
        self.ensure_one()
        rec = self.sudo()
        user = self.env.user
        if rec.state == 'manager_approval' and user != rec.line_manager_id:
            raise UserError(_('Only the line manager can reject this ticket.'))
        elif self.state == 'hr_approval' and not user.has_group('employee_profile_change_request.group_profile_change_hr_reviewer'):
            raise UserError(_('Only HR Managers can reject this ticket.'))
        elif self.state == 'it_approval' and not user.has_group('ticketing_it.group_it_manager'):
            raise UserError(_('Only IT managers can reject this ticket.'))
        elif self.state not in ['manager_approval', 'hr_approval', 'it_approval']:
            raise UserError(_('This ticket cannot be rejected in its current state.'))

    def do_reject(self, reason):
        for rec in self:
            rec.sudo()._check_reject_access()
            rec.sudo().write({
                'state': 'rejected',
                'rejection_reason': reason,
                'rejected_by_id': self.env.user.id,
                'rejected_date': fields.Datetime.now(),
            })
            rec.activity_unlink(['mail.mail_activity_data_todo'])
            if rec.employee_id and rec.employee_id.user_id:
                rec._notify('ticketing_it.email_template_rejection', rec.employee_id.user_id)
            rec.message_post(body=_('Rejected by %s. Reason: %s') % (self.env.user.name, reason))

    def action_start_work(self):
        for rec in self.sudo():
            if rec.assigned_to_id.id != self.env.uid:
                raise UserError(_('This ticket is not assigned to you.'))
            rec.state = 'in_progress'
            rec.message_post(body=_('Work started by %s') % self.env.user.name)

    def action_done(self):
        for rec in self.sudo():
            rec.state = 'done'
            rec.done_date = fields.Date.today()
            if rec.ticket_type_id.code == 'social_media' and rec.duration:
                start = rec.done_date
                rec.access_start_date = start
                deltas = {'3m': relativedelta(months=3), '6m': relativedelta(months=6),
                          '12m': relativedelta(years=1)}
                rec.access_finish_date = (start + deltas[rec.duration]
                                          if rec.duration in deltas else rec.custom_expiry_date)
            if rec.employee_id and rec.employee_id.user_id:
                rec._notify('ticketing_it.email_template_done', rec.employee_id.user_id)
            rec.message_post(body=_('Completed by %s') % self.env.user.name)

    # ─── REMINDERS (CRON) ────────────────────────────────────────────────────

    def open_reminder_wizard(self):
        return {'type': 'ir.actions.act_window', 'res_model': 'it.reminder.config.wizard',
                'view_mode': 'form', 'target': 'new'}

    def action_send_dynamic_reminder(self):
        _logger.info('===== CRON: IT Ticket Reminder =====')
        ICP = self.env['ir.config_parameter'].sudo()
        reminder_days = int(ICP.get_param('ticketing_it.reminder_days', 1))
        today = fields.Date.today()

        tickets = self.search([('state', 'in', ['manager_approval', 'hr_approval', 'it_approval'])])
        user_map = defaultdict(list)

        for ticket in tickets:
            level = ticket.workflow_level
            state_date, user = False, False

            if level == '1':
                if ticket.state == 'manager_approval':
                    state_date, user = ticket.submitted_date, ticket.line_manager_id
            elif level == '2':
                if ticket.state == 'manager_approval':
                    state_date, user = ticket.submitted_date, ticket.line_manager_id
                elif ticket.state == 'it_approval':
                    state_date, user = ticket.manager_approval_date, ticket.it_manager_id
            elif level == '3':
                if ticket.state == 'manager_approval':
                    state_date, user = ticket.submitted_date, ticket.line_manager_id
                elif ticket.state == 'hr_approval':
                    state_date, user = ticket.manager_approval_date, ticket.hr_approver_id

            if not state_date or not user:
                continue
            if (today - state_date).days < reminder_days:
                continue
            if ticket.last_reminder_sent and (today - ticket.last_reminder_sent).days < reminder_days:
                continue
            user_map[user].append(ticket)

        tmpl = self.env.ref('ticketing_it.email_template_approval_reminder', raise_if_not_found=False)
        if not tmpl:
            _logger.error('Reminder template not found!')
            return

        for user, tlist in user_map.items():
            tickets_rs = self.browse([t.id for t in tlist])
            try:
                tmpl.with_context(approver_name=user.name, tickets=tickets_rs).send_mail(
                    tickets_rs[0].id, force_send=True,
                    email_values={'email_to': user.email,
                                  'recipient_ids': [(5, 0, 0)], 'partner_ids': [(5, 0, 0)]})
            except Exception as e:
                _logger.error('Reminder failed for %s: %s', user.name, e)
                continue
            for t in tickets_rs:
                t.sudo().write({'last_reminder_sent': today})
                t.message_post(body=_('Reminder sent to %s') % user.name)

        _logger.info('===== CRON DONE =====')

    def check_social_media_expiry(self):
        today = fields.Date.today()
        for ticket in self.search([('access_finish_date', '=', today)]):
            try:
                if ticket.assigned_to_id and ticket.assigned_to_id.email:
                    ticket._notify('ticketing_it.email_template_access_end_assignee', ticket.assigned_to_id)
                if ticket.employee_id and ticket.employee_id.user_id:
                    ticket._notify('ticketing_it.email_template_access_end_employee', ticket.employee_id.user_id)
            except Exception as e:
                _logger.error('Expiry check error ticket %s: %s', ticket.id, e)


class ITTicketWorkflowConfig(models.Model):
    _name = 'it.ticket.workflow.config'
    _description = 'Ticket Workflow Configuration'
    _rec_name = 'ticket_type_id'

    ticket_type_id = fields.Many2one('it.ticket.type', string='Ticket Type',
                                     required=True,
                                     domain="[('id', 'not in', existing_ticket_type_ids)]")
    workflow_level = fields.Selection([
        ('0', '0 - Direct to IT Support'),
        ('1', '1 - Line Manager → IT Support'),
        ('2', '2 - Line Manager → IT Manager → IT Support'),
        ('3', '3 - Line Manager → HR → IT Support'),
    ], default='1', required=True)
    existing_ticket_type_ids = fields.Many2many('it.ticket.type',
                                                compute='_compute_existing_ticket_types')
    category_id = fields.Many2one('it.ticket.category', string='Category',
                                   related='ticket_type_id.category_id', store=True, readonly=True)
    it_support_group_id = fields.Many2one(
        'res.groups', string='IT Support Group',
        related='ticket_type_id.it_support_group_id', store=True, readonly=False,
        help='Which group owns tickets of this sub-category. Editable here — '
             'writes straight back to the sub-category (it.ticket.type) record.')

    _sql_constraints = [
        ('unique_ticket_type', 'unique(ticket_type_id)', 'Workflow already defined for this ticket type!')
    ]

    @api.constrains('ticket_type_id')
    def _check_unique(self):
        for rec in self:
            if self.search([('ticket_type_id', '=', rec.ticket_type_id.id), ('id', '!=', rec.id)]):
                raise ValidationError(_('Workflow already exists for this ticket type!'))

    @api.depends()
    def _compute_existing_ticket_types(self):
        all_configured = self.search([]).mapped('ticket_type_id')
        for rec in self:
            rec.existing_ticket_type_ids = all_configured