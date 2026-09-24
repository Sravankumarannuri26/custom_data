# -*- coding: utf-8 -*-
import json



from odoo import models, api, _
from odoo.exceptions import UserError


INVOICE_TYPE_CODES = {
    "out_invoice": "388",   # Tax invoice
    "out_refund": "381",    # Credit note
}



class AccountMove(models.Model):
    _inherit = "account.move"



    def action_generate_irn(self):

        self.ensure_one()

        if self.move_type not in ("out_invoice", "out_refund"):
            raise UserError(_(
                "Generate IRN is only available for Customer Invoices "
                "and Customer Credit Notes."
            ))

        if self.state == "draft":
            raise UserError(_(
                "Please confirm (post) the invoice before generating "
                "the IRN payload."
            ))

        payload = self._prepare_irn_json()

        pretty_json = json.dumps(
            payload,
            indent=4,
            ensure_ascii=False,
            default=str,
        )

        wizard = self.env["irn.payload.preview"].create({
            "json_payload": pretty_json,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("IRN Payload"),
            "res_model": "irn.payload.preview",
            "view_mode": "form",
            "res_id": wizard.id,
            "target": "new",
        }


    def _prepare_irn_json(self):
        self.ensure_one()
        return {
            "invoiceHeader": self._irn_invoice_header(),
            "processControl": self._irn_process_control(),
            "seller": self._irn_seller(),
            "buyer": self._irn_buyer(),
            "documentTotals": self._irn_document_totals(),
            "taxBreakdown": self._irn_tax_breakdown(),
            "invoiceLines": self._irn_invoice_lines(),
        }

    def _irn_product_lines(self):
        self.ensure_one()
        return self.invoice_line_ids.filtered(
            lambda l: l.display_type not in ("line_section", "line_note")
        )


    def _irn_invoice_header(self):
        self.ensure_one()
        return {
            "invoiceNumber": self.name or "",
            "invoiceIssueDate": self.invoice_date.isoformat() if self.invoice_date else "",
            "invoiceTypeCode": INVOICE_TYPE_CODES.get(self.move_type, ""),
            "invoiceTransactionTypeCode": "",
            "invoiceCurrencyCode": self.currency_id.name or "",
        }


    def _irn_process_control(self):
        self.ensure_one()
        return {
            "businessProcessType": "",
            "specificationIdentifier": "",
        }


    def _irn_seller(self):
        self.ensure_one()
        company = self.company_id
        return {
            "sellerName": company.name or "",
            "sellerTaxIdentifier": company.vat or "",
            "taxSchemeCode": "",
            "sellerElectronicAddress": "",
            "schemeIdentifier": "",
            "postalAddress": {
                "addressLine1": company.street or "",
                "city": company.city or "",
                "countrySubdivision": company.state_id.name or "",
                "countryCode": company.country_id.code or "",
            },
        }

    def _irn_buyer(self):
        self.ensure_one()
        partner = self.partner_id
        return {
            "buyerName": partner.name or "",
            "buyerElectronicAddress": partner.vat or "",
            "schemeIdentifier": "",
            "postalAddress": {
                "addressLine1": partner.street or "",
                "city": partner.city or "",
                "countrySubdivision": partner.state_id.name or "",
                "countryCode": partner.country_id.code or "",
            },
        }

    def _irn_document_totals(self):
        self.ensure_one()
        currency = self.currency_id.name or ""
        product_lines = self._irn_product_lines()
        untaxed = round(sum(product_lines.mapped("price_subtotal")), 2)
        total = round(sum(product_lines.mapped("price_total")), 2)
        tax = round(total - untaxed, 2)
        residual = round(self.amount_residual, 2)
        return {
            "sumOfInvoiceLineNetAmount": {
                "amount": untaxed, "currencyCode": currency,
            },
            "invoiceTotalAmountWithoutTax": {
                "amount": untaxed, "currencyCode": currency,
            },
            "invoiceTotalTaxAmount": {
                "amount": tax, "currencyCode": currency,
            },
            "invoiceTotalAmountWithTax": {
                "amount": total, "currencyCode": currency,
            },
            "amountDueForPayment": {
                "amount": residual, "currencyCode": currency,
            },
        }


    def _irn_tax_breakdown(self):
        self.ensure_one()
        currency = self.currency_id.name or ""
        groups = {}  # tax.id -> {"tax": tax, "taxable": float, "tax_amount": float}

        for line in self._irn_product_lines():
            taxes = line.tax_ids
            if not taxes:
                continue
            line_tax_amount = line.price_total - line.price_subtotal
            total_rate = sum(taxes.mapped("amount")) or len(taxes)
            for tax in taxes:
                share = (tax.amount / total_rate) if total_rate else (1.0 / len(taxes))
                group = groups.setdefault(tax.id, {"tax": tax, "taxable": 0.0, "tax_amount": 0.0})
                group["taxable"] += line.price_subtotal * share
                group["tax_amount"] += line_tax_amount * share

        breakdown = []
        for group in groups.values():
            tax = group["tax"]
            breakdown.append({
                "taxCategoryTaxableAmount": {
                    "amount": round(abs(group["taxable"]), 2), "currencyCode": currency,
                },
                "taxCategoryRate": tax.amount,
                "taxCategoryTaxAmount": {
                    "amount": round(abs(group["tax_amount"]), 2), "currencyCode": currency,
                },
                "taxCategoryCode": "",
                "taxSchemeCode": "",
            })
        return breakdown

    def _irn_invoice_lines(self):
        self.ensure_one()
        currency = self.currency_id.name or ""
        lines = []
        for idx, line in enumerate(self._irn_product_lines(), start=1):
            # Item net price = price_unit less the line discount, both stock fields.
            discount_amount = line.price_unit * (line.discount or 0.0) / 100.0
            net_price = round(line.price_unit - discount_amount, 2)
            # VAT line amount = price_total - price_subtotal, both stock fields.
            line_tax_amount = round(line.price_total - line.price_subtotal, 2)
            # Optional GCC localization field, only used if actually present
            # on this database (module l10n_gcc_invoice or similar); left
            # blank otherwise rather than guessed. Note: per the mapping
            # sheet this field actually stores a tax AMOUNT, not a rate -
            # rename the JSON key below if that's misleading for your ASP.
            gcc_tax_amount = getattr(line, "l10n_gcc_invoice_tax_amount", "")

            lines.append({
                # Sequential position in the invoice, not the internal
                # move-line "sequence" field (which can be 0/falsy and was
                # previously rendered as an empty string).
                "invoiceLineIdentifier": str(idx),
                "invoicedQuantity": line.quantity,
                "invoicedQuantityUnitOfMeasureCode": line.product_uom_id.name or "",
                "invoiceLineNetAmount": {
                    "amount": round(line.price_subtotal, 2), "currencyCode": currency,
                },
                "priceDetails": {
                    "itemPriceBaseQuantity": "",
                    "syntaxBindingQualifier": "",
                    "itemGrossPrice": {
                        "amount": round(line.price_unit, 2), "currencyCode": currency,
                    },
                    "itemNetPrice": {
                        "amount": net_price, "currencyCode": currency,
                    },
                },
                "lineTaxInformation": {
                    "invoicedItemTaxCategoryCode": "",
                    "invoicedItemTaxRate": gcc_tax_amount or "",
                    "vatLineAmount": {
                        "amount": line_tax_amount, "currencyCode": currency,
                    },
                },
                "itemInformation": {
                    "itemName": line.product_id.name or "",
                    "itemDescription": line.name or "",
                    "itemClassificationIdentifier": "",
                    "schemeIdentifier": "",
                },
            })
        return lines
