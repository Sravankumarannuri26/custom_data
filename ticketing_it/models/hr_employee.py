# -*- coding: utf-8 -*-

from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'  # Extend the existing HR Employee model

    # Computed field to store the number of tickets raised by the employee
    ticket_count = fields.Integer('Tickets', compute='_compute_ticket_count')

    # Compute method to count tickets linked to each employee
    def _compute_ticket_count(self):
        for employee in self:
            employee.ticket_count = self.env['it.ticket'].search_count([
                ('employee_id', '=', employee.id)
            ])

    # Action method to open a list/form view of tickets for the current employee
    def action_view_tickets(self):
        return {
            'name': 'IT Tickets',
            'type': 'ir.actions.act_window',
            'res_model': 'it.ticket',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
        }