# -*- coding: utf-8 -*-
from odoo import models, fields


class HrProfileChangeRequestTrail(models.Model):
    _name = 'hr.profile.change.request.trail'
    _description = 'Profile Change Request Audit Trail'
    _order = 'action_date desc'
    _rec_name = 'note'

    # ── Parent ────────────────────────────────────────────────────
    request_id = fields.Many2one(
        comodel_name='hr.profile.change.request',
        string='Change Request',
        required=True,
        ondelete='cascade',
        index=True,
    )

    # ── What happened ─────────────────────────────────────────────
    action = fields.Selection(
        selection=[
            ('submitted', 'Submitted'),
            ('approved',  'Approved'),
            ('rejected',  'Rejected'),
            ('reopened',  'Re-opened'),
        ],
        string='Action',
        required=True,
    )
    note = fields.Char(
        string='Note',
    )
    reason = fields.Text(
        string='Rejection Reason',
        help='Populated only when action is Rejected.',
    )

    # ── Who and when ──────────────────────────────────────────────
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Action By',
        readonly=True,
        ondelete='set null',
    )
    action_date = fields.Datetime(
        string='Date & Time',
        readonly=True,
        default=fields.Datetime.now,
    )

    # ── Related (for reporting) ───────────────────────────────────
    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        related='request_id.employee_id',
        string='Employee',
        store=True,
        readonly=True,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        related='request_id.department_id',
        string='Department',
        store=True,
        readonly=True,
    )

