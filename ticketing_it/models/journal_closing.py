from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    x_opening_balance = fields.Monetary(
        string='Opening Balance',
        currency_field='company_currency_id',
        compute='_compute_x_opening_closing_balance',
        store=False,
        help="Cumulative balance of this account for all posted entries "
             "strictly before this line's date.",
    )
    x_closing_balance = fields.Monetary(
        string='Closing Balance',
        currency_field='company_currency_id',
        compute='_compute_x_opening_closing_balance',
        store=False,
        help="Opening Balance + this line's own movement (debit - credit).",
    )

    @api.depends('account_id', 'date', 'debit', 'credit', 'balance', 'move_id.state')
    def _compute_x_opening_closing_balance(self):
        for line in self:
            if not line.account_id or not line.date:
                line.x_opening_balance = 0.0
                line.x_closing_balance = 0.0
                continue

            domain = [
                ('account_id', '=', line.account_id.id),
                ('date', '<', line.date),
                ('move_id.state', '=', 'posted'),
                ('id', '!=', line.id),
            ]
            result = self.env['account.move.line'].read_group(
                domain=domain,
                fields=['balance:sum'],
                groupby=[],
            )
            opening = result[0]['balance'] or 0.0 if result else 0.0

            line.x_opening_balance = opening
            line.x_closing_balance = opening + line.balance