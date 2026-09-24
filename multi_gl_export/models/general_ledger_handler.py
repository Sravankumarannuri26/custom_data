# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo import models, fields
from odoo.tools import SQL


class AccountGeneralLedgerReportHandlerMulti(models.AbstractModel):
    """
       Extension of `account.general.ledger.report.handler`
       to enable comma-separated multi-account filtering during export.
       Also adds Reference and Project Code columns to General Ledger.
    """
    _inherit = 'account.general.ledger.report.handler'


    def _report_custom_engine_general_ledger(
        self, expressions, options, date_scope,
        current_groupby, next_groupby,
        offset=0, limit=None, warnings=None
    ):

        def get_grouping_key(row, groupby):
            if groupby == 'id_with_accumulated_balance':
                if not row['id']:
                    return f"balance_line_{row['account_id']}"
                else:
                    import json
                    return json.dumps([fields.Date.to_string(row['date']), row['id']])
            return row[groupby] if groupby else None

        report = self.env['account.report'].browse(options['report_id'])
        options_date_from = fields.Date.from_string(options['date']['date_from'])
        fiscalyear_date_from = self.env.company.compute_fiscalyear_dates(
            options_date_from
        )['date_from']

        additional_domain = [
            '|',
            ('account_id.include_initial_balance', '=', True),
            ('date', '>=', fiscalyear_date_from),
        ]

        report_query = report._get_report_query(
            options, 'from_beginning', additional_domain
        )

        # ==================================================
        # MULTI-ACCOUNT SEARCH (COMMA-SEPARATED)
        # ==================================================
        if (
                options.get('export_mode') == 'print'
                and options.get('filter_search_bar')
                and current_groupby not in ('id_with_accumulated_balance', 'id')
        ):
            search = options.get('filter_search_bar')
            tokens = [t.strip() for t in search.split(',') if t.strip()]

            # Build OR domain
            domain = []
            for token in tokens:
                domain.append(('display_name', 'ilike', token))

            if len(domain) > 1:
                from odoo.osv.expression import OR
                domain = OR([[d] for d in domain])
            else:
                domain = domain[:1]

            domain += self.env['account.account']._check_company_domain(
                self.env['account.report'].get_report_company_ids(options)
            )

            search_bar_sql = SQL(
                """
                AND result_account.id = ANY(%(search_bar_account_query)s)
                """,
                search_bar_account_query=self.env['account.account']._search(domain)
                .select(SQL.identifier('id'))
            )
        else:
            search_bar_sql = SQL()

        additional_select = SQL("")
        groupby_sql = []

        if current_groupby == 'id_with_accumulated_balance':
            account_code_select = self.env['account.account']._field_to_sql(
                'result_account', 'code', report_query
            )
            account_name_select = self.env['account.account']._field_to_sql(
                'result_account', 'name'
            )

            # ============================================
            # ADDED: Reference and Project Code fields
            # ============================================
            additional_select = SQL(
                """
                CASE WHEN account_move_line.date >= %(date)s
                     THEN account_move_line.id ELSE NULL END AS id,
                CASE WHEN account_move_line.date >= %(date)s
                     THEN account_move_line.date ELSE NULL END AS date,
                MIN(move.name) AS move_name,
                SUM(account_move_line.amount_currency) AS amount_currency,
                MIN(partner.name) AS partner_name,
                MIN(account_move_line.currency_id) AS currency_id,
                MIN(result_account.id) AS account_id,
                MIN(account_move_line.name) AS line_name,
                MIN(%(account_name_select)s) AS account_name,
                MIN(%(account_code_select)s) AS account_code,
                MIN(move.name) AS name,
                MIN(account_move_line.project_code) AS project,
                MIN(account_move_line.name) AS label,
                MIN(move.ref) AS ref,
                """,
                date=fields.Date.from_string(options['date']['date_from']),
                account_name_select=account_name_select,
                account_code_select=account_code_select,
            )
            groupby_sql = [SQL("1"), SQL("2"), SQL("account_id")]

        elif current_groupby == 'account_id':
            additional_select = SQL(
                """
                result_account.id AS account_id,
                result_account.account_type AS account_type,
                SUM(account_move_line.amount_currency) AS amount_currency,
                result_account.currency_id AS currency_id,
                """
            )
            groupby_sql = [
                SQL("result_account.id"),
                SQL("result_account.currency_id"),
            ]

        elif current_groupby:
            field_sql = self.env['account.move.line']._field_to_sql(
                'account_move_line', current_groupby, report_query
            )
            additional_select = SQL("%s,", field_sql)
            groupby_sql = [SQL("%s", field_sql)]


        query = SQL(
            """
            SELECT
                %(additional_select)s
                COALESCE(SUM(%(select_debit)s), 0.0) AS debit,
                COALESCE(SUM(%(select_credit)s), 0.0) AS credit,
                COALESCE(SUM(%(select_balance)s), 0.0) AS balance
            FROM %(from_clause)s
            LEFT JOIN res_partner partner
                ON partner.id = account_move_line.partner_id
            JOIN account_account account
                ON account.id = account_move_line.account_id
            JOIN account_account result_account
                ON result_account.id = account_move_line.account_id
            JOIN account_move move
                ON move.id = account_move_line.move_id
            %(currency_table_join)s
            WHERE %(where_clause)s
            %(search_bar_sql)s
            %(additional_groupby)s
            %(orderby_clause)s
            %(offset_clause)s
            LIMIT %(limit)s
            """,
            additional_select=additional_select,
            select_balance=report._currency_table_apply_rate(
                SQL("account_move_line.balance")
            ),
            select_debit=report._currency_table_apply_rate(
                SQL("account_move_line.debit")
            ),
            select_credit=report._currency_table_apply_rate(
                SQL("account_move_line.credit")
            ),
            from_clause=report_query.from_clause,
            currency_table_join=report._currency_table_aml_join(options),
            where_clause=report_query.where_clause,
            search_bar_sql=search_bar_sql,
            additional_groupby=SQL(
                "GROUP BY %s", SQL(",").join(groupby_sql)
            ) if groupby_sql else SQL(),
            orderby_clause=SQL(
                "ORDER BY 2 NULLS FIRST, move_name, 1 NULLS FIRST"
            ) if current_groupby == 'id_with_accumulated_balance' else SQL(),
            offset_clause=SQL("OFFSET %s", offset) if offset else SQL(),
            limit=limit,
        )

        # ============================================
        # ADDED: Initialize reference and project fields
        # ============================================
        rows_by_key = defaultdict(lambda: {
            'date': None,
            'partner_name': None,
            'amount_currency': None,
            'currency_id': self.env.company.currency_id.id,
            'debit': 0,
            'credit': 0,
            'balance': 0,
            'has_sublines': True,
            'name': None,
            'project': None,
            'label':None,
            'ref':None,

        })

        for row in self.env.execute_query_dict(query):
            key = get_grouping_key(row, current_groupby)

            if key not in rows_by_key:
                rows_by_key[key].update({
                    'debit': row['debit'],
                    'credit': row['credit'],
                    'balance': row['balance'],
                })

                if current_groupby == 'id_with_accumulated_balance':
                    rows_by_key[key]['has_sublines'] = False
                    rows_by_key[key]['account_id'] = row['account_id']

                    if 'balance_line' not in key:
                        # ============================================
                        # ADDED: Store reference and project values
                        # ============================================
                        rows_by_key[key].update({
                            'date': row['date'],
                            'partner_name': row['partner_name'],
                            'line_name': row['line_name'],
                            'account_code': row['account_code'],
                            'account_name': row['account_name'],
                            'move_name': row['move_name'],
                            'name': row.get('name', ''),
                            'project': row.get('project', ''),
                            'label': row.get('label', ''),
                            'ref': row.get('ref', ''),

                        })

                    if row['currency_id'] != self.env.company.currency_id.id:
                        rows_by_key[key]['amount_currency'] = row['amount_currency']
                        rows_by_key[key]['currency_id'] = row['currency_id']

                elif current_groupby == 'account_id':
                    rows_by_key[key]['has_sublines'] = True
                    if row.get('currency_id'):
                        rows_by_key[key]['amount_currency'] = row['amount_currency']
                        rows_by_key[key]['currency_id'] = row['currency_id']
            else:
                rows_by_key[key]['debit'] += row['debit']
                rows_by_key[key]['credit'] += row['credit']
                rows_by_key[key]['balance'] += row['balance']

        if not current_groupby:
            return rows_by_key[None]

        return [(k, v) for k, v in rows_by_key.items()]