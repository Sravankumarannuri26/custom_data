# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.tools import float_compare, float_is_zero, plaintext2html
from odoo import Command, api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from markupsafe import Markup


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # This is the same original with extra values: amount_currency and currency_id.
    def _prepare_line_values(self, line, account_id, date, debit, credit):

        def calculate_amount_currency(amount_currency=0):
            # the if statement is to check if its normal payslip with positive value or refunded payslip with negative value
            if line.amount >= 0:
                if debit == 0 and credit > 0:
                    amount_currency -= abs(line.amount)
                elif credit == 0 and debit > 0:
                    amount_currency = abs(line.amount)
            else:  # in case of refund line.amount is negative number
                if debit == 0 and credit > 0:
                    amount_currency -= abs(line.amount)
                elif credit == 0 and debit > 0:
                    amount_currency = abs(line.amount)
            # print(amount_currency)
            return amount_currency

        return {
            'name': line.name,
            'partner_id': line.partner_id.id,
            'account_id': account_id,
            'journal_id': line.slip_id.struct_id.journal_id.id,
            'date': date,
            'debit': debit,
            'credit': credit,
            'amount_currency': calculate_amount_currency(),
            'currency_id': line.slip_id.currency_id.id,
            'analytic_distribution': (line.salary_rule_id.analytic_account_id and {
                line.salary_rule_id.analytic_account_id.id: 100}) or
                                     (line.slip_id.contract_id.analytic_account_id.id and {
                                         line.slip_id.contract_id.analytic_account_id.id: 100})
        }

    # recalculate the amount if the slip currency != company currency.
    def _prepare_slip_lines(self, date, line_ids):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Payroll')
        new_lines = []
        for line in self.line_ids.filtered(lambda line: line.category_id):
            amount_currency = line.total
            if line.slip_id.currency_id == self.env.user.company_id.currency_id:
                amount = line.total
            else:
                amount = line.slip_id.currency_id._convert(
                    line.total,
                    self.env.user.company_id.currency_id,
                    self.company_id,
                    fields.Date.context_today(self),
                )
            if line.code == 'NET':  # Check if the line is the 'Net Salary'.
                for tmp_line in self.line_ids.filtered(lambda line: line.category_id):
                    if tmp_line.salary_rule_id.not_computed_in_net:  # Check if the rule must be computed in the 'Net Salary' or not.
                        if amount > 0:
                            amount -= abs(tmp_line.total)
                        elif amount < 0:
                            amount += abs(tmp_line.total)
            # print("amount=",amount)
            if float_is_zero(amount, precision_digits=precision):
                continue
            debit_account_id = line.salary_rule_id.account_debit.id
            credit_account_id = line.salary_rule_id.account_credit.id
            if debit_account_id:  # If the rule has a debit account.
                debit = amount if amount > 0.0 else 0.0
                credit = -amount if amount < 0.0 else 0.0

                debit_line = self._get_existing_lines(
                    line_ids + new_lines, line, debit_account_id, debit, credit)

                if not debit_line:
                    debit_line = self._prepare_line_values(line, debit_account_id, date, debit, credit)
                    debit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_debit.tax_ids.ids]
                    new_lines.append(debit_line)
                else:
                    debit_line['debit'] += debit
                    debit_line['credit'] += credit
                    debit_line['amount_currency']+= amount_currency

            if credit_account_id:  # If the rule has a credit account.
                debit = -amount if amount < 0.0 else 0.0
                credit = amount if amount > 0.0 else 0.0
                credit_line = self._get_existing_lines(
                    line_ids + new_lines, line, credit_account_id, debit, credit)

                if not credit_line:
                    credit_line = self._prepare_line_values(line, credit_account_id, date, debit, credit)
                    credit_line['tax_ids'] = [(4, tax_id) for tax_id in line.salary_rule_id.account_credit.tax_ids.ids]
                    new_lines.append(credit_line)
                else:
                    credit_line['debit'] += debit
                    credit_line['credit'] += credit
                    credit_line['amount_currency'] -= amount_currency
        return new_lines

    @api.depends('employee_id', 'contract_id', 'struct_id', 'date_from', 'date_to', 'struct_id')
    def _compute_input_line_ids(self):
        attachment_types = self._get_attachment_types()
        attachment_type_ids = [f.id for f in attachment_types.values()]
        for slip in self:
            if not slip.employee_id or not slip.employee_id.salary_attachment_ids or not slip.struct_id:
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id.id in attachment_type_ids)
                slip.update({'input_line_ids': [Command.unlink(line.id) for line in lines_to_remove]})
            if slip.employee_id.salary_attachment_ids and slip.date_to:
                lines_to_remove = slip.input_line_ids.filtered(lambda x: x.input_type_id.id in attachment_type_ids)
                input_line_vals = [Command.unlink(line.id) for line in lines_to_remove]

                valid_attachments = slip.employee_id.salary_attachment_ids.filtered(
                    lambda a: a.state == 'open' and a.date_start <= slip.date_to
                )

                # Only take deduction types present in structure
                deduction_types = list(set(valid_attachments.deduction_type_id.mapped('code')))
                struct_deduction_lines = list(set(slip.struct_id.rule_ids.mapped('code')))
                included_deduction_types = [f for f in deduction_types if attachment_types[f].code in struct_deduction_lines]
                for deduction_type in included_deduction_types:
                    if not slip.struct_id.rule_ids.filtered(lambda r: r.active and r.code == attachment_types[deduction_type].code):
                        continue
                    attachments = valid_attachments.filtered(lambda a: a.deduction_type_id.code == deduction_type)
                    amount = sum(attachments.mapped('active_amount'))
                    # Check if the attachment line currency is the same as company currency
                    if slip.employee_id.contract_id.currency_id != self.env.user.company_id.currency_id:
                        amount = self.env.user.company_id.currency_id._convert(
                            sum(attachments.mapped('active_amount')),
                            slip.employee_id.contract_id.currency_id,
                            self.company_id,
                            fields.Date.context_today(self), )
                    name = ', '.join(attachments.mapped('description'))
                    input_type_id = attachment_types[deduction_type].id
                    input_line_vals.append(Command.create({
                        'name': name,
                        'amount': amount if not slip.credit_note else -amount,
                        'input_type_id': input_type_id,
                    }))
                slip.update({'input_line_ids': input_line_vals})


    def _action_create_account_move(self):
        precision = self.env['decimal.precision'].precision_get('Payroll')
        currencies = []
        company_currency = self.env.company.currency_id
        # Add payslip without run
        payslips_to_post = self.filtered(lambda slip: not slip.payslip_run_id)

        # Adding pay slips from a batch and deleting pay slips with a batch that is not ready for validation.
        payslip_runs = (self - payslips_to_post).mapped('payslip_run_id')
        for run in payslip_runs:
            if run._are_payslips_ready():
                payslips_to_post |= run.slip_ids

        # A payslip need to have a done state and not an accounting move.
        payslips_to_post = payslips_to_post.filtered(lambda slip: slip.state == 'done' and not slip.move_id)

        # Check that a journal exists on all the structures
        if any(not payslip.struct_id for payslip in payslips_to_post):
            raise ValidationError(_('One of the contract for these payslips has no structure type.'))
        if any(not structure.journal_id for structure in payslips_to_post.mapped('struct_id')):
            raise ValidationError(_('One of the payroll structures has no account journal defined on it.'))

        # Map all payslips by structure journal and pay slips month.
        # {'journal_id': {'month': [slip_ids]}}
        slip_mapped_data = defaultdict(lambda: defaultdict(lambda: self.env['hr.payslip']))
        for slip in payslips_to_post:
            if slip.contract_id.currency_id not in currencies:
                currencies.append(slip.contract_id.currency_id)
            slip_mapped_data[slip.struct_id.journal_id.id][
                slip.date or fields.Date().end_of(slip.date_to, 'month')] |= slip
        for journal_id in slip_mapped_data:  # For each journal_id.
            for slip_date in slip_mapped_data[journal_id]:  # For each month.
                line_ids = []
                date = slip_date
                move_dict = {
                    'narration': '',
                    'ref': fields.Date().end_of(slip.date_to, 'month').strftime('%B %Y'),
                    'journal_id': journal_id,
                    'date': date,
                }
                for currency in currencies:
                    payslips = (slip for slip in slip_mapped_data[journal_id][slip_date] if
                                slip.contract_id.currency_id.id == currency.id)
                    line_ids_per_curency = []
                    amount_currency = 0.0
                    debit_sum = 0.0
                    credit_sum = 0.0

                    for slip in payslips:
                        move_dict['narration'] += plaintext2html(
                            slip.number or '' + ' - ' + slip.employee_id.name or '')
                        move_dict['narration'] += Markup('<br/>')
                        slip_lines = slip._prepare_slip_lines(date, line_ids_per_curency)
                        line_ids_per_curency.extend(slip_lines)

                    for line_id_per_curency in line_ids_per_curency:  # Get the debit and credit sum.
                        debit_sum += line_id_per_curency['debit']
                        credit_sum += line_id_per_curency['credit']
                        line_id_per_curency['currency_id'] = currency.id


                    # The code below is called if there is an error in the balance between credit and debit sum.
                    if float_compare(credit_sum, debit_sum, precision_digits=precision) == -1:

                        slip._prepare_adjust_line(line_ids_per_curency, 'credit', debit_sum, credit_sum, date)
                    elif float_compare(debit_sum, credit_sum, precision_digits=precision) == -1:
                        slip._prepare_adjust_line(line_ids_per_curency, 'debit', debit_sum, credit_sum, date)

                    line_ids.append(line_ids_per_curency)

                move_dict['line_ids'] = [(0, 0, line_vals) for sublist in line_ids for line_vals in sublist]
                move = self._create_account_move(move_dict)
                for slip in slip_mapped_data[journal_id][slip_date]:
                    slip.write({'move_id': move.id, 'date': date})
        return True
