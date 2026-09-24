from odoo import models, _


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_pdf_export_html(self, options, lines, additional_context=None, template=None):
        if self.custom_handler_model_id.model == 'account.customer.statement.report.handler':
            options['report_title'] = _('Statement of Accounts')

        return super()._get_pdf_export_html(
            options, lines, additional_context=additional_context, template=template
        )