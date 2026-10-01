from odoo import models, fields


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    x_frozen_unlocked = fields.Boolean(string="Unlock Frozen Leave")
    x_type_is_frozen = fields.Boolean(
        related='holiday_status_id.x_is_frozen', store=False,
    )

    def message_post(self, **kwargs):
        kwargs['mail_auto_delete'] = True
        self = self.with_context(
            mail_create_nosubscribe=True, mail_dont_send=True, mail_notify_force_send=False,
        )
        return super().message_post(**kwargs)

    def activity_update(self):
        return super(HrLeaveAllocation, self.with_context(mail_dont_send=True)).activity_update()