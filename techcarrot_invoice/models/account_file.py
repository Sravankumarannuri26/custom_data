import io
import zipfile
import base64
from odoo import models

class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_print_invoices_as_zip(self):
        report = self.env.ref('techcarrot_invoice.action_generate_techcarrot_invoice_report')
        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for move in self:
                pdf_content, _ = self.env['ir.actions.report']._render_qweb_pdf(
                    report.id, [move.id]
                )
                filename = f"{move.name.replace('/', '_')}.pdf"
                zf.writestr(filename, pdf_content)

        buffer.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': 'Invoices.zip',
            'type': 'binary',
            'datas': base64.b64encode(buffer.read()),
            'mimetype': 'application/zip',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }