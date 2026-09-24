from odoo import models


class ITTicketReportProcessing(models.Model):
    # Reporting model for analyzing ticket processing times using existing it_ticket table
    _name = "it.ticket.report.processing"
    _inherit = "it.ticket"
    _table = "it_ticket"
    _description = "IT Ticket Processing Report"
    _rec_name = "name"


class ITTicketReportType(models.Model):
    # Reporting model for analyzing tickets grouped by type using same table
    _name = "it.ticket.report.type"
    _inherit = "it.ticket"
    _table = "it_ticket"
    _description = "IT Ticket Type Report"
    _rec_name = "name"


class ITTicketReportOpen(models.Model):
    # Reporting model focused on open tickets using shared ticket table
    _name = "it.ticket.report.open"
    _inherit = "it.ticket"
    _table = "it_ticket"
    _description = "IT Ticket Open Report"
    _rec_name = "name"


class ITTicketReportSolved(models.Model):
    # Reporting model focused on solved/closed tickets using shared table
    _name = "it.ticket.report.solved"
    _inherit = "it.ticket"
    _table = "it_ticket"
    _description = "IT Ticket Solved Report"
    _rec_name = "name"