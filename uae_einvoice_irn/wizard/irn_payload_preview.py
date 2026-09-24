from odoo import fields, models


class IrnPayloadPreview(models.TransientModel):
    _name = "irn.payload.preview"
    _description = "IRN Payload Preview"

    json_payload = fields.Text(
        string="IRN JSON Payload",
        readonly=True,
    )