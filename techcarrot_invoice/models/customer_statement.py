from markupsafe import Markup
from odoo import _, models
from odoo.tools import SQL


class AccountFollowupReportHandler(models.AbstractModel):
    _inherit = 'account.followup.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        options['forced_domain'] = options.get('forced_domain', []) + [
            ('move_id.move_type', '=', 'out_invoice'),
        ]
        options['columns'] = [col for col in options['columns'] if col['expression_label'] != 'amount_currency']

    def _get_additional_column_aml_values(self):
        return SQL(
            "account_move_line.amount_residual AS amount_residual, "
            "account_move_line.amount_residual_currency AS amount_residual_currency, "
            "'Invoice' AS transaction_type,"
        )

    # ------------------------------------------------------------------
    # Precompute the WHOLE ledger for a partner once - opening balance,
    # then each invoice/payment delta in order - and store final
    # balances in a lookup table. Rendering only ever READS this table,
    # never mutates it, so it's safe no matter how many times Odoo
    # calls the render methods internally.
    # ------------------------------------------------------------------
    def _build_ledger(self, options, partner):
        date_from = options.get('date', {}).get('date_from')
        opening_by_currency = {}
        if date_from and partner.id:
            domain = [
                ('partner_id', '=', partner.id),
                ('move_id.move_type', '=', 'out_invoice'),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                ('date', '<', date_from),
            ]
            for aml in self.env['account.move.line'].search(domain):
                cur = aml.currency_id or aml.company_currency_id
                opening_by_currency[cur.id] = opening_by_currency.get(cur.id, 0.0) + (aml.amount_residual_currency or aml.amount_residual)

        aml_values = self._get_aml_values(options, [partner.id]).get(partner.id, [])

        running = dict(opening_by_currency)
        aml_balances = {}
        payment_balances = {}

        for aml_result in aml_values:
            cur_id = aml_result['currency_id']
            running[cur_id] = running.get(cur_id, 0.0) + aml_result['amount_currency']
            aml_balances[aml_result['id']] = running[cur_id]

            aml = self.env['account.move.line'].browse(aml_result['id'])
            currency = self.env['res.currency'].browse(cur_id)
            for partial in (aml.matched_credit_ids | aml.matched_debit_ids).sorted('max_date'):
                is_debit_side = partial.debit_move_id.id == aml.id
                other_line = partial.credit_move_id if is_debit_side else partial.debit_move_id
                payment = self.env['account.payment'].search([('move_id', '=', other_line.move_id.id)], limit=1)
                if not payment:
                    continue
                paid_amount = payment.amount if payment.currency_id == currency else abs(partial.amount)
                if not paid_amount:
                    continue
                running[cur_id] -= paid_amount
                payment_balances[payment.id] = running[cur_id]

        return {
            'opening_by_currency': opening_by_currency,
            'aml_balances': aml_balances,
            'payment_balances': payment_balances,
        }

    def _get_ledger(self, options, partner):
        ledgers = options.setdefault('_soa_ledgers', {})
        if partner.id not in ledgers:
            ledgers[partner.id] = self._build_ledger(options, partner)
        return ledgers[partner.id]

    # ------------------------------------------------------------------
    # Partner line (customer name + address + TRN)
    # ------------------------------------------------------------------
    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        line = super()._get_report_line_partners(options, partner, partner_values, level_shift=level_shift)

        if partner:
            parts = []
            if partner.street:
                parts.append(partner.street)
            if partner.street2:
                parts.append(partner.street2)
            if partner.city:
                parts.append(partner.city)
            if partner.state_id:
                parts.append(partner.state_id.name)
            if partner.zip:
                parts.append(partner.zip)
            if partner.country_id:
                parts.append(partner.country_id.name)
            address = ', '.join(parts)
            if partner.vat:
                address = f"{address} - TRN: {partner.vat}" if address else f"TRN: {partner.vat}"

            if options.get('export_mode') == 'print':
                name_html = Markup('<span style="font-size: 14px; font-weight: bold;">{}</span>').format(line['name'])
                if address:
                    address_html = Markup('<span style="color: #888888;">{}</span>').format(address)
                    line['name'] = Markup('{}<br/>{}').format(name_html, address_html)
                else:
                    line['name'] = name_html
            elif address:
                line['name'] = f"{line['name']} - {address}"

            self._get_ledger(options, partner)

        return line

    # ------------------------------------------------------------------
    # Invoice line - Amount / Balance (looked up from the precomputed
    # ledger) / Invoice Currency / Transaction. Payments column stays
    # blank here - the paid amount now only shows on the payment row.
    # ------------------------------------------------------------------
    def _get_report_line_move_line(self, options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=0):
        line = super()._get_report_line_move_line(
            options, aml_query_result, partner_line_id, init_bal_by_col_group, level_shift=level_shift
        )

        report = self.env['account.report'].browse(options['report_id'])
        currency = self.env['res.currency'].browse(aml_query_result['currency_id'])
        own_amount = aml_query_result['amount_currency']

        res_ids_map = report._get_res_ids_from_line_id(partner_line_id, ['res.partner'])
        partner_id = res_ids_map.get('res.partner')
        partner = self.env['res.partner'].browse(partner_id) if partner_id else self.env['res.partner']
        ledger = self._get_ledger(options, partner) if partner else {'aml_balances': {}}
        balance_value = ledger['aml_balances'].get(aml_query_result['id'], own_amount)

        for column, col_data in zip(options['columns'], line['columns']):
            label = column['expression_label']
            if label == 'amount':
                new_col = report._build_column_dict(own_amount, column, options=options, currency=currency)
                col_data.clear()
                col_data.update(new_col)
            elif label == 'balance':
                new_col = report._build_column_dict(balance_value, column, options=options, currency=currency)
                col_data.clear()
                col_data.update(new_col)
            elif label == 'payment_id':
                col_data.clear()
                col_data.update(report._build_column_dict(None, None))
            elif label == 'currency_id':
                new_col = report._build_column_dict(currency.name, column, options=options)
                col_data.clear()
                col_data.update(new_col)
            elif label == 'transaction_type':
                new_col = report._build_column_dict(_('Invoice'), column, options=options)
                col_data.clear()
                col_data.update(new_col)

        return line

    # ------------------------------------------------------------------
    # One row per real payment - name is "PaymentName (InvoiceNumber)",
    # Payments column shows the amount NEGATIVE, Balance looked up from
    # the ledger, and caret_options set so clicking gives "View Payment".
    # ------------------------------------------------------------------
    def _get_payment_transaction_lines(self, options, aml_query_result, partner_line_id, currency, level_shift):
        report = self.env['account.report'].browse(options['report_id'])
        aml = self.env['account.move.line'].browse(aml_query_result['id'])
        partials = aml.matched_credit_ids | aml.matched_debit_ids

        res_ids_map = report._get_res_ids_from_line_id(partner_line_id, ['res.partner'])
        partner_id = res_ids_map.get('res.partner')
        partner = self.env['res.partner'].browse(partner_id) if partner_id else self.env['res.partner']
        ledger = self._get_ledger(options, partner) if partner else {'payment_balances': {}}

        lines = []
        for partial in partials.sorted('max_date'):
            is_debit_side = partial.debit_move_id.id == aml.id
            other_line = partial.credit_move_id if is_debit_side else partial.debit_move_id
            payment_move = other_line.move_id

            payment = self.env['account.payment'].search([('move_id', '=', payment_move.id)], limit=1)
            if not payment:
                continue

            paid_amount = payment.amount if payment.currency_id == currency else abs(partial.amount)
            if not paid_amount:
                continue

            balance_value = ledger['payment_balances'].get(payment.id, 0.0)

            columns = []
            for column in options['columns']:
                label = column['expression_label']
                if label == 'payment_id':
                    columns.append(report._build_column_dict(-paid_amount, column, options=options, currency=currency))
                elif label == 'balance':
                    columns.append(report._build_column_dict(balance_value, column, options=options, currency=currency))
                elif label == 'invoice_date':
                    columns.append(report._build_column_dict(partial.max_date, column, options=options))
                elif label == 'currency_id':
                    columns.append(report._build_column_dict(currency.name, column, options=options))
                elif label == 'transaction_type':
                    columns.append(report._build_column_dict(_('Payment Received'), column, options=options))
                else:
                    columns.append(report._build_column_dict(None, None))

            lines.append({
                'id': report._get_generic_line_id('account.move.line', other_line.id, parent_line_id=partner_line_id,
                                                  markup=partial.id),
                'parent_id': partner_line_id,
                'name': f"{payment.name} ({payment.memo or aml.move_id.name})" if payment.name else (aml.move_id.name or ''),
                'columns': columns,
                'level': 3 + level_shift,
                'caret_options': 'account.payment',
            })
        return lines

    def _get_partner_aml_report_lines(self, report, options, partner_line_id, aml_results, progress, offset=0, level_shift=0):
        lines, next_progress, treated_count, has_more = super()._get_partner_aml_report_lines(
            report, options, partner_line_id, aml_results, progress, offset=offset, level_shift=level_shift
        )

        expanded_lines = []

        res_ids_map = report._get_res_ids_from_line_id(partner_line_id, ['res.partner'])
        partner_id = res_ids_map.get('res.partner')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            ledger = self._get_ledger(options, partner)
            report_obj = self.env['account.report'].browse(options['report_id'])

            # One Opening Balance row per currency that appears anywhere
            # in this customer's visible invoices, even if that
            # currency's opening balance is 0.
            currencies_to_show = set(ledger['opening_by_currency'].keys())
            currencies_to_show.update(aml['currency_id'] for aml in aml_results)

            for cur_id in currencies_to_show:
                amount = ledger['opening_by_currency'].get(cur_id, 0.0)
                currency = self.env['res.currency'].browse(cur_id)
                columns = []
                for column in options['columns']:
                    label = column['expression_label']
                    if label == 'balance':
                        columns.append(report_obj._build_column_dict(amount, column, options=options, currency=currency))
                    elif label == 'currency_id':
                        columns.append(report_obj._build_column_dict(currency.name, column, options=options))
                    elif label == 'transaction_type':
                        columns.append(report_obj._build_column_dict(_('Opening Balance'), column, options=options))
                    else:
                        columns.append(report_obj._build_column_dict(None, None))
                expanded_lines.append({
                    'id': report_obj._get_generic_line_id(None, None, parent_line_id=partner_line_id, markup=f'opening_{cur_id}'),
                    'parent_id': partner_line_id,
                    'name': _('Opening Balance'),
                    'columns': columns,
                    'level': 3 + level_shift,
                })

        for line in lines:
            expanded_lines.append(line)
            model, record_id = report._get_model_info_from_id(line['id'])
            if model == 'account.move.line':
                aml_match = next((a for a in aml_results if a['id'] == record_id), None)
                if aml_match:
                    currency = self.env['res.currency'].browse(aml_match['currency_id'])
                    expanded_lines.extend(
                        self._get_payment_transaction_lines(options, aml_match, partner_line_id, currency, level_shift)
                    )

        return expanded_lines, next_progress, treated_count, has_more

    # ------------------------------------------------------------------
    # Totals - one line PER CURRENCY
    # ------------------------------------------------------------------
    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = super()._dynamic_lines_generator(report, options, all_column_groups_expression_totals, warnings=warnings)
        lines = [l for l in lines if not (isinstance(l[1], dict) and l[1].get('name') == _('Total'))]

        partner_ids = options.get('partner_ids', [])
        aml_values = self._get_aml_values(options, partner_ids) if partner_ids else {}
        all_amls = [aml for partner_amls in aml_values.values() for aml in partner_amls]

        totals_by_currency = {}
        for aml in all_amls:
            cur_id = aml['currency_id']
            residual = aml.get('amount_residual_currency')
            residual = residual if residual is not None else aml['amount_currency']
            paid = aml['amount_currency'] - residual
            t = totals_by_currency.setdefault(cur_id, {'amount': 0.0, 'payment': 0.0, 'balance': 0.0})
            t['amount'] += aml['amount_currency']
            t['payment'] += paid
            t['balance'] += residual

        report_obj = self.env['account.report'].browse(options['report_id'])
        for cur_id, sums in totals_by_currency.items():
            currency = self.env['res.currency'].browse(cur_id)
            columns = []
            for column in options['columns']:
                label = column['expression_label']
                if label in ('amount', 'payment_id', 'balance'):
                    key = {'amount': 'amount', 'payment_id': 'payment', 'balance': 'balance'}[label]
                    formatted_number = f"{sums[key]:,.2f}"
                    columns.append({'name': f"{formatted_number} {currency.name}", 'no_format': sums[key]})
                elif label == 'currency_id':
                    columns.append(report_obj._build_column_dict(currency.name, column, options=options))
                else:
                    columns.append(report_obj._build_column_dict(None, None))

            lines.append((0, {
                'id': report_obj._get_generic_line_id(None, None, markup=f'total_{cur_id}'),
                'name': _('Total (%s)') % currency.name,
                'level': 1,
                'columns': columns,
            }))

        return lines