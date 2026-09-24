import os
import logging
from datetime import datetime
from odoo import models, api, fields

_logger = logging.getLogger(__name__)

LOG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'sanitize_logs'
)


class StagingDatabaseSanitizer(models.Model):
    _name        = 'staging.database.sanitizer'
    _description = 'Staging Database Sanitizer'

    name = fields.Char('Name', default='Sanitizer Instance')

    # ─────────────────────────────────────────────────────
    # ENTRY POINT — called by post_init_hook
    # ─────────────────────────────────────────────────────
    @api.model
    def run_sanitization_check(self):
        _logger.info("=" * 60)
        _logger.info("SANITIZATION CHECK STARTED")
        _logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        _logger.info("=" * 60)

        # Step 1: Check if database is neutralized (restored)
        if not self._is_staging_environment():
            return

        # Step 2: Check if already sanitized
        if self._is_already_sanitized():
            _logger.info("✓ Already sanitized — skipping")
            return

        _logger.info("✓ Not yet sanitized — proceeding")

        # Step 3: Execute all operations
        self._execute_sanitization()

        _logger.info("=" * 60)
        _logger.info("SANITIZATION COMPLETED")
        _logger.info("=" * 60)

    # ─────────────────────────────────────────────────────
    # ENVIRONMENT DETECTION — database.is_neutralized ONLY
    # ─────────────────────────────────────────────────────
    def _is_staging_environment(self):
        """
        Check if database.is_neutralized = True.
        This parameter is automatically set by Odoo when restoring a database.
        If True, we assume this is a staging/test environment.
        """
        _logger.info("─" * 60)
        _logger.info("ENVIRONMENT CHECK")
        _logger.info("─" * 60)

        try:
            is_neutralized = self.env['ir.config_parameter'].sudo().get_param(
                'database.is_neutralized', 'False'
            )

            _logger.info(f"  database.is_neutralized = '{is_neutralized}'")

            if is_neutralized.lower() == 'true':
                _logger.info("  ✓ Database is neutralized (restored DB)")
                _logger.info("  ✓ Assuming STAGING environment — proceeding")
                return True
            else:
                _logger.info("  ✗ Database is NOT neutralized")
                _logger.info("  ✗ Assuming PRODUCTION environment — skipping")
                return False

        except Exception as e:
            _logger.error(f"  ✗ Error checking neutralization status: {e}")
            _logger.error("  Assuming PRODUCTION for safety — skipping")
            return False

    # ─────────────────────────────────────────────────────
    # DUPLICATE RUN PREVENTION
    # ─────────────────────────────────────────────────────
    def _is_already_sanitized(self):
        flag = self.env['ir.config_parameter'].sudo().get_param(
            'staging.db.sanitized', 'False'
        )
        return flag.lower() == 'true'

    def _set_sanitized_flag(self):
        self.env['ir.config_parameter'].sudo().set_param(
            'staging.db.sanitized', 'True'
        )
        _logger.info("  ✓ Sanitized flag saved")

    # ─────────────────────────────────────────────────────
    # SQL HELPERS
    # ─────────────────────────────────────────────────────
    def _table_exists(self, table):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public'
                AND   table_name   = %s
            )
        """, (table,))
        return self.env.cr.fetchone()[0]

    def _column_exists(self, table, column):
        self.env.cr.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name  = %s
                AND   column_name = %s
            )
        """, (table, column))
        return self.env.cr.fetchone()[0]

    # ─────────────────────────────────────────────────────
    # MAIN EXECUTION
    # ─────────────────────────────────────────────────────
    def _execute_sanitization(self):
        stats = {
            'sign_document_deleted' : 0,
            'payslip_deleted'       : 0,
            'employee_updated'      : 0,
            'attachment_deleted'    : 0,
            'mail_tracking_deleted' : 0,
            'gl_entries_deleted'    : 0,
            'gl_reconcile_deleted'  : 0,
            'gl_details'            : {},
            'errors'                : [],
        }

        _logger.info("─" * 60)
        _logger.info("RUNNING OPERATIONS")
        _logger.info("─" * 60)

        # ── 1. Sign Documents (FK dependency — MUST be first) ──
        try:
            stats['sign_document_deleted'] = self._delete_sign_documents()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Sign documents failed: {e}")
            stats['errors'].append(f"sign_document: {e}")

        # ── 2. DELETE FROM hr_payslip ──
        try:
            stats['payslip_deleted'] = self._delete_payslips()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Payslips failed: {e}")
            stats['errors'].append(f"hr_payslip: {e}")

        # ── 3. UPDATE hr_version SET sub_total = 100 ──
        try:
            stats['employee_updated'] = self._update_employees()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Employees failed: {e}")
            stats['errors'].append(f"hr_version: {e}")

        # ── 4. DELETE FROM ir_attachment ──
        try:
            stats['attachment_deleted'] = self._delete_attachments()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Attachments failed: {e}")
            stats['errors'].append(f"ir_attachment: {e}")

        # ── 5. DELETE FROM mail_tracking_value ──
        try:
            stats['mail_tracking_deleted'] = self._delete_mail_tracking()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Mail tracking failed: {e}")
            stats['errors'].append(f"mail_tracking_value: {e}")

        # ── 6. DELETE GL CODE SERIES ──
        try:
            gl_result = self._delete_gl_code_series()
            stats['gl_entries_deleted']   = gl_result['total']
            stats['gl_reconcile_deleted'] = gl_result['reconcile_deleted']
            stats['gl_details']           = gl_result['details']
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ GL entries failed: {e}")
            stats['errors'].append(f"gl_entries: {e}")

        # ── Save log to DB ──
        try:
            self._create_log_record(stats)
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Log record failed: {e}")

        # ── Save log to file ──
        self._write_log_file(stats)

        # ── Set sanitized flag ──
        try:
            self._set_sanitized_flag()
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            _logger.error(f"  ✗ Flag save failed: {e}")

        # ── Summary ──
        _logger.info("─" * 60)
        _logger.info("SUMMARY")
        _logger.info("─" * 60)
        _logger.info(f"  [1] Sign Docs Deleted   : {stats['sign_document_deleted']}")
        _logger.info(f"  [2] Payslips Deleted    : {stats['payslip_deleted']}")
        _logger.info(f"  [3] HR Version Updated  : {stats['employee_updated']}")
        _logger.info(f"  [4] Attachments Deleted : {stats['attachment_deleted']}")
        _logger.info(f"  [5] Mail Tracking Del   : {stats['mail_tracking_deleted']}")
        _logger.info(f"  [6] GL Reconciles Del   : {stats['gl_reconcile_deleted']}")
        _logger.info(f"      GL Entries Deleted  : {stats['gl_entries_deleted']}")
        _logger.info(f"  Errors                  : {len(stats['errors'])}")

    # ─────────────────────────────────────────────────────
    # OPERATION 0: Sign Documents
    # ─────────────────────────────────────────────────────
    def _delete_sign_documents(self):
        _logger.info("→ [0] Sign Documents (FK dependency)...")
        if not self._table_exists('sign_document'):
            _logger.info("    ℹ Table not found — skipping")
            return 0

        self.env.cr.execute('DELETE FROM "sign_document"')
        count = self.env.cr.rowcount

        if count > 0:
            _logger.info(f"    ✓ Deleted {count} records")
        else:
            _logger.info("    ✓ Nothing to delete")
        return count

    # ─────────────────────────────────────────────────────
    # OPERATION 1: DELETE FROM hr_payslip
    # ─────────────────────────────────────────────────────
    def _delete_payslips(self):
        _logger.info("→ [1] DELETE FROM hr_payslip...")
        if not self._table_exists('hr_payslip'):
            _logger.info("    ℹ Table not found — skipping")
            return 0

        self.env.cr.execute('DELETE FROM "hr_payslip"')
        count = self.env.cr.rowcount

        if count > 0:
            _logger.info(f"    ✓ Deleted {count} records")
        else:
            _logger.info("    ✓ Nothing to delete")
        return count

    # ─────────────────────────────────────────────────────
    # OPERATION 2: UPDATE hr_version SET sub_total = 100 and manual fields=100
    # ─────────────────────────────────────────────────────

    def _update_employees(self):
        _logger.info("→ [2] UPDATE hr_version fields to 100...")

        if not self._table_exists('hr_version'):
            _logger.info("    ℹ Table not found — skipping")
            return 0

        fields_to_update = [
            'sub_total',
            'basic_salary_manual',
            'hra_manual',
            'flexi_manual',
            'statutory_manual',
            'gratuity_manual',
            'pf_manual',
            'medical_manual'
        ]

        # Check which columns actually exist
        existing_fields = [
            f for f in fields_to_update
            if self._column_exists('hr_version', f)
        ]

        if not existing_fields:
            _logger.warning("    ⚠ None of the required columns found — skipping")
            return 0

        # Build dynamic SQL
        set_clause = ', '.join([f'{field} = 100' for field in existing_fields])

        query = f'UPDATE "hr_version" SET {set_clause}'
        self.env.cr.execute(query)

        count = self.env.cr.rowcount

        if count > 0:
            _logger.info(f"    ✓ Updated {count} records ({', '.join(existing_fields)} = 100)")
        else:
            _logger.info("    ✓ Nothing to update")

        return count



    # ─────────────────────────────────────────────────────
    # OPERATION 3: DELETE FROM ir_attachment
    # ─────────────────────────────────────────────────────
    def _delete_attachments(self):
        _logger.info("→ [3] DELETE FROM ir_attachment...")
        if not self._table_exists('ir_attachment'):
            _logger.info("    ℹ Table not found — skipping")
            return 0
        self.env.cr.execute("""
            DELETE FROM ir_attachment
            WHERE create_uid != 1
            AND id NOT IN (
                SELECT id FROM ir_attachment
                WHERE url LIKE '/web/%' or url like '/_custom/%'
            )
        """)
        count = self.env.cr.rowcount

        if count > 0:
            _logger.info(f"    ✓ Deleted {count} records")
            _logger.info("    ℹ Physical files cleaned by Odoo GC on restart")
        else:
            _logger.info("    ✓ Nothing to delete")
        return count

    # ─────────────────────────────────────────────────────
    # OPERATION 4: DELETE FROM mail_tracking_value
    # ─────────────────────────────────────────────────────
    def _delete_mail_tracking(self):
        _logger.info("→ [4] DELETE FROM mail_tracking_value...")
        if not self._table_exists('mail_tracking_value'):
            _logger.info("    ℹ Table not found — skipping")
            return 0

        self.env.cr.execute('DELETE FROM "mail_tracking_value"')
        count = self.env.cr.rowcount

        if count > 0:
            _logger.info(f"    ✓ Deleted {count} records")
        else:
            _logger.info("    ✓ Nothing to delete")
        return count

    #GL code series values updated to 0 (Zero)
    def _delete_gl_code_series(self):
        """
        Zero out journal entries that contain lines with specific GL code series.
        Sets both debit and credit to 0 to maintain balanced accounting.

        This preserves the audit trail while neutralizing sensitive data.

        Balance sheet items: 11, 14, 21, 22, 28, 30
        P&L items: 50, 52, 62
        """
        _logger.info("→ [5] ZERO OUT GL Code Series (Maintain Balance)...")

        if not self._table_exists('account_move'):
            _logger.info("    ℹ account_move table not found — skipping")
            return {'total': 0, 'reconcile_deleted': 0, 'details': {}}

        if not self._table_exists('account_move_line'):
            _logger.info("    ℹ account_move_line table not found — skipping")
            return {'total': 0, 'reconcile_deleted': 0, 'details': {}}

        # GL code series to zero out
        balance_sheet_series = ['11', '14', '21', '22', '28', '30']
        pnl_series = ['50', '52', '62']
        all_series = balance_sheet_series + pnl_series

        total_moves_affected = 0
        total_lines_zeroed = 0
        reconcile_deleted = 0
        details = {}

        _logger.info(f"    ℹ Balance Sheet series: {', '.join(balance_sheet_series)}")
        _logger.info(f"    ℹ P&L series: {', '.join(pnl_series)}")


        _logger.info("    → Finding journal entries to zero out...")

        try:
            series_patterns = ' OR '.join([f"kv.value LIKE '{s}%'" for s in all_series])


            self.env.cr.execute(f"""
                SELECT DISTINCT am.id, am.name
                FROM account_move am
                JOIN account_move_line aml ON aml.move_id = am.id
                JOIN account_account aa ON aa.id = aml.account_id
                JOIN jsonb_each_text(aa.code_store) kv ON true
                WHERE {series_patterns}
            """)

            moves_to_zero = self.env.cr.fetchall()
            move_ids = [m[0] for m in moves_to_zero]

            if not move_ids:
                _logger.info("    ✓ No journal entries found matching GL series")
                return {'total': 0, 'reconcile_deleted': 0, 'details': {}}

            total_moves_affected = len(move_ids)
            _logger.info(f"    ℹ Found {total_moves_affected} journal entries to zero out")

        except Exception as e:
            _logger.error(f"    ✗ Error finding journal entries: {e}")
            return {'total': 0, 'reconcile_deleted': 0, 'details': {}}


        if self._table_exists('account_partial_reconcile'):
            _logger.info("    → Deleting partial reconciliations...")

            try:
                self.env.cr.execute("""
                    DELETE FROM account_partial_reconcile
                    WHERE debit_move_id IN (
                        SELECT id FROM account_move_line WHERE move_id IN %s
                    )
                    OR credit_move_id IN (
                        SELECT id FROM account_move_line WHERE move_id IN %s
                    )
                """, (tuple(move_ids), tuple(move_ids)))

                reconcile_deleted = self.env.cr.rowcount

                if reconcile_deleted > 0:
                    _logger.info(f"    ✓ Deleted {reconcile_deleted} reconciliations")

            except Exception as e:
                _logger.error(f"    ✗ Error deleting reconciliations: {e}")


        _logger.info("    → Analyzing GL series breakdown...")

        for series in all_series:
            try:
                self.env.cr.execute(f"""
                    SELECT COUNT(DISTINCT aml.id)
                    FROM account_move_line aml
                    JOIN account_account aa ON aa.id = aml.account_id
                    JOIN jsonb_each_text(aa.code_store) kv ON true
                    WHERE aml.move_id IN %s
                    AND kv.value LIKE %s
                """, (tuple(move_ids), f'{series}%'))

                count = self.env.cr.fetchone()[0]

                if count > 0:
                    details[series] = count
                    series_type = 'Balance Sheet' if series in balance_sheet_series else 'P&L'
                    _logger.info(f"    ℹ GL {series}... ({series_type}): {count} lines")

            except Exception as e:
                _logger.error(f"    ✗ Error analyzing GL {series}...: {e}")
                details[f'{series}_error'] = str(e)

        # STEP 4: Zero out ALL lines in affected journal entries
        _logger.info("    → Zeroing out account move lines...")

        try:
            # Set debit, credit, amount_currency, and balance to 0

            self.env.cr.execute("""
                UPDATE account_move_line
                SET 
                    debit = 0,
                    credit = 0,
                    amount_currency = 0,
                    balance = 0
                WHERE move_id IN %s
            """, (tuple(move_ids),))

            total_lines_zeroed = self.env.cr.rowcount
            _logger.info(f"    ✓ Zeroed out {total_lines_zeroed} account move lines")

        except Exception as e:
            _logger.error(f"    ✗ Error zeroing move lines: {e}")
            return {
                'total': 0,
                'reconcile_deleted': reconcile_deleted,
                'details': details
            }

        # STEP 5: Update journal entry totals to 0
        _logger.info("    → Updating journal entry totals...")

        try:
            # Check if amount_total column exists (may vary by Odoo version)
            if self._column_exists('account_move', 'amount_total'):
                self.env.cr.execute("""
                    UPDATE account_move
                    SET 
                        amount_total = 0,
                        amount_untaxed = 0,
                        amount_tax = 0,
                        amount_residual = 0
                    WHERE id IN %s
                """, (tuple(move_ids),))
            else:
                # For older versions, just update what exists
                self.env.cr.execute("""
                    UPDATE account_move
                    SET amount_total = 0
                    WHERE id IN %s
                      AND EXISTS (
                          SELECT 1 FROM information_schema.columns
                          WHERE table_name = 'account_move'
                          AND column_name = 'amount_total'
                      )
                """, (tuple(move_ids),))

            _logger.info(f"    ✓ Updated {total_moves_affected} journal entry totals")

        except Exception as e:
            _logger.error(f"    ✗ Error updating journal entry totals: {e}")

        # Summary
        _logger.info("    ─" * 30)
        _logger.info(f"    ✓ SUMMARY:")
        _logger.info(f"      • Journal Entries Zeroed: {total_moves_affected}")
        _logger.info(f"      • Move Lines Zeroed: {total_lines_zeroed}")
        _logger.info(f"      • Reconciliations Removed: {reconcile_deleted}")
        _logger.info(f"      • Debit/Credit Balance: MAINTAINED ✅")
        _logger.info("    ─" * 30)

        return {
            'total': total_lines_zeroed,
            'moves_affected': total_moves_affected,
            'reconcile_deleted': reconcile_deleted,
            'details': details
        }

    # ─────────────────────────────────────────────────────
    # LOGGING
    # ─────────────────────────────────────────────────────
    def _create_log_record(self, stats):
        """Save log record to Odoo DB"""
        _logger.info("→ Creating DB log record...")

        # Format GL details for storage
        gl_details_text = ''
        if stats.get('gl_details'):
            gl_details_text = '\n'.join(
                f"{series}... series: {count} entries"
                for series, count in sorted(stats['gl_details'].items())
                if not series.endswith('_error')
            )
            # Add errors if any
            errors = [
                f"{series.replace('_error', '')}: {msg}"
                for series, msg in stats['gl_details'].items()
                if series.endswith('_error')
            ]
            if errors:
                gl_details_text += '\n\nErrors:\n' + '\n'.join(errors)

        log = self.env['staging.sanitize.log'].sudo().create({
            'database_name'         : self.env.cr.dbname,
            'sign_document_deleted' : stats['sign_document_deleted'],
            'payslip_deleted'       : stats['payslip_deleted'],
            'employee_updated'      : stats['employee_updated'],
            'attachment_deleted'    : stats['attachment_deleted'],
            'mail_tracking_deleted' : stats['mail_tracking_deleted'],
            'gl_entries_deleted'    : stats.get('gl_entries_deleted', 0),
            'gl_details'            : gl_details_text or False,
            'error_count'           : len(stats['errors']),
            'error_details'         : '\n'.join(stats['errors']) or False,
            'status'                : (
                'Success' if not stats['errors']
                else 'Completed with errors'
            ),
        })
        _logger.info(f"    ✓ Log record created: ID {log.id}")

    def _write_log_file(self, stats):
        """Save log to file — restricted to authorized persons"""
        try:
            os.makedirs(LOG_DIR, exist_ok=True)

            ts           = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            log_filename = f"sanitize_{self.env.cr.dbname}_{ts}.log"
            log_filepath = os.path.join(LOG_DIR, log_filename)

            errors_text = (
                '\n'.join(f"  ✗ {e}" for e in stats['errors'])
                if stats['errors'] else "  None"
            )

            # Format GL details
            gl_details_text = ''
            if stats.get('gl_details'):
                gl_details_text = '\n'.join(
                    f"    {series}... series : {count} entries"
                    for series, count in sorted(stats['gl_details'].items())
                    if not series.endswith('_error')
                )

            content = (
                f"{'=' * 60}\n"
                f"      SANITIZATION REPORT\n"
                f"{'=' * 60}\n"
                f"  Timestamp    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"  Database     : {self.env.cr.dbname}\n"
                f"  Status       : {'Success' if not stats['errors'] else 'Completed with errors'}\n"
                f"{'─' * 60}\n"
                f"  SQL OPERATIONS EXECUTED\n"
                f"{'─' * 60}\n"
                f"  DELETE FROM sign_document      : {stats['sign_document_deleted']} rows\n"
                f"  DELETE FROM hr_payslip         : {stats['payslip_deleted']} rows\n"
                f"  UPDATE hr_version sub_total    : {stats['employee_updated']} rows\n"
                f"  DELETE FROM ir_attachment      : {stats['attachment_deleted']} rows\n"
                f"  DELETE FROM mail_tracking_value: {stats['mail_tracking_deleted']} rows\n"
                f"  DELETE GL reconciliations      : {stats.get('gl_reconcile_deleted', 0)} rows\n"
                f"  DELETE GL entries (total)      : {stats.get('gl_entries_deleted', 0)} rows\n"
            )

            if gl_details_text:
                content += (
                    f"{'─' * 60}\n"
                    f"  GL SERIES BREAKDOWN\n"
                    f"{'─' * 60}\n"
                    f"{gl_details_text}\n"
                )

            content += (
                f"{'─' * 60}\n"
                f"  ERRORS ({len(stats['errors'])} total)\n"
                f"{'─' * 60}\n"
                f"{errors_text}\n"
                f"{'=' * 60}\n"
            )

            with open(log_filepath, 'w', encoding='utf-8') as f:
                f.write(content)

            _logger.info(f"    ✓ Log file saved: {log_filepath}")

        except Exception as e:
            _logger.error(f"    ✗ Could not write log file: {e}")