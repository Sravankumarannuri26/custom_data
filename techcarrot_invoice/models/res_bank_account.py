from odoo import api, fields, models
from odoo.osv import expression


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    iban_no = fields.Char('IBAN')
    swift_code = fields.Char('SWIFT Code', copy=False)

    # _sql_constraints = [
    #     (
    #         "iban_no_unique",
    #         "unique(iban_no)","Bank IBAN should be unique.",
    #     ),
    # ]
    _iban_no_unique = models.Constraint(
        "unique (iban_no)",
        "Bank IBAN should be unique."
    )

class ResBank(models.Model):
    _inherit = "res.bank"


    branch = fields.Char('Branch', copy=False)



class ResCompany(models.Model):
    _inherit = "res.company"

    lut_code = fields.Char(string="LUT Code")
    iec_code = fields.Char(string="IEC Code")

