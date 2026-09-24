# -*- coding: utf-8 -*-
from odoo import models, fields


class ITTicketCategory(models.Model):
    _name = 'it.ticket.category'
    _description = 'IT Ticket Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    ticket_type_ids = fields.One2many('it.ticket.type', 'category_id', string='Sub-Categories')

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Category code must be unique!')
    ]


class ITTicketTypeInherit(models.Model):
    """Add category_id and it_support_id to the existing it.ticket.type model."""
    _inherit = 'it.ticket.type'

    category_id = fields.Many2one('it.ticket.category', string='Category',
                                  ondelete='restrict', index=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    it_support_id = fields.Many2one(
        'res.users',
        string='Default IT Support',
        help='Default IT team member assigned for this sub-category.',
    )
    it_support_group_id = fields.Many2one(
        'res.groups',
        string='IT Support Group',
        help='Security group that owns this sub-category. Every ticket of this '
             'type is assigned to a member of this group instead of the flat '
             '"IT Team" group, and every member of this group is emailed when '
             'a ticket of this type comes in. Falls back to the flat IT Team '
             'group if left empty.',
    )
