from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _get_payment_keyword_attachments(self, ids):
        return self.env['ir.attachment'].search([
            ('res_model', '=', 'account.payment'),
            ('res_id', 'in', ids),
            '|', '|',
            ('name', 'ilike', 'payment'),
            ('name', 'ilike', 'advice'),
            ('name', 'ilike', 'transaction'),
        ])

    def _compute_attachment_ids(self):
        super()._compute_attachment_ids()
        for composer in self:
            if composer.model != 'account.payment':
                continue
            ids = composer._evaluate_res_ids()
            if not ids:
                continue
            existing = self._get_payment_keyword_attachments(ids)
            if existing:
                composer.attachment_ids = composer.attachment_ids | existing

    def action_send_mail(self):
        for wizard in self:
            if wizard.model != 'account.payment':
                continue
            ids = wizard._evaluate_res_ids()
            if not ids:
                continue
            existing = self._get_payment_keyword_attachments(ids)
            if existing:
                wizard.attachment_ids = [(4, att.id) for att in existing]
        return super().action_send_mail()