# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class PortalWizard(models.TransientModel):
    _inherit = 'portal.wizard.user'

    def _send_email(self):
        """ send notification email to a new portal user """
        self.ensure_one()

        template = self.env.ref('portal_mail.portal_send_invite_email')
        if not template:
            raise UserError(_('The template "Portal: new user" not found for sending email to the portal user.'))

        lang = self.user_id.sudo().lang
        partner = self.user_id.sudo().partner_id
        partner.signup_prepare()

        template.with_context(dbname=self.env.cr.dbname, lang=lang, welcome_message=self.wizard_id.welcome_message, medium='portalinvite').send_mail(self.user_id.id, force_send=True)

        return True