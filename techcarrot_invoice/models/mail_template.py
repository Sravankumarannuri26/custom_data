from odoo import models

NEW_BODY_HTML = """<div style="margin: 0px; padding: 0px;">
    <p style="margin: 0px; padding: 0px; font-size: 13px;">
        Dear <t t-out="object.partner_id.name or ''">Azure Interior</t><br/><br/>
        <t t-if="object.payment_type == 'outbound'">
            We have made the payment for your invoice(s). It's a pleasure doing business with you.
            We look forward to working with you.
        </t>
        <t t-else="">
            Thank you for your payment.
        </t>
        <br/><br/>
        Here is your payment receipt <span style="font-weight:bold;" t-out="(object.name or '').replace('/','-') or ''">BNK1-2021-05-0002</span> amounting
        to <span style="font-weight:bold;" t-out="format_amount(object.amount, object.currency_id) or ''">$ 10.00</span> from <t t-out="object.company_id.name or ''">YourCompany</t>.
        <br/><br/>
        Do not hesitate to contact us if you have any questions.
        <br/><br/>
        Best regards,
        <t t-if="not is_html_empty(user.signature)">
            <br/><br/>
            <div>--<br/><t t-out="user.signature or ''">Mitchell Admin</t></div>
        </t>
    </p>
</div>"""


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def _register_hook(self):
        super()._register_hook()
        template = self.env.ref('account.mail_template_data_payment_receipt', raise_if_not_found=False)
        if template and template.body_html != NEW_BODY_HTML:
            template.sudo().write({'body_html': NEW_BODY_HTML})