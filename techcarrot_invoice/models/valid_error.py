# -*- coding: utf-8 -*-
from odoo import models


class AccountMoveSequenceBypass(models.Model):
    _inherit = 'account.move'

    def _must_check_constrains_date_sequence(self):
        return False