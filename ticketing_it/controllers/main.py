# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
from odoo.addons.web.controllers.home import Home
from werkzeug.utils import redirect as werkzeug_redirect
import logging
import urllib.parse

_logger = logging.getLogger(__name__)


class MicrosoftSSOHome(Home):
    @http.route('/web/session/logout', type='http', auth='none', website=True)
    def logout(self, redirect='/web/login', **kwargs):
        microsoft_logout_url = None
        try:
            uid = request.session.uid
            if uid:
                user = request.env['res.users'].sudo().browse(uid)
                if user.exists() and user.oauth_uid:
                    base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    provider = request.env['auth.oauth.provider'].sudo().search(
                        [('id', '=', user.oauth_provider_id.id)], limit=1)
                    tenant_id = 'common'
                    if provider and provider.auth_endpoint:
                        parts = provider.auth_endpoint.split('/')
                        for i, part in enumerate(parts):
                            if 'login.microsoftonline.com' in part and i + 1 < len(parts):
                                tenant_id = parts[i + 1]
                                break
                    microsoft_logout_url = (
                        f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/logout"
                        f"?post_logout_redirect_uri={base_url}/web/login"
                    )
        except Exception as e:
            _logger.error("Azure SSO logout error: %s", e)
        request.session.logout(keep_db=True)
        if microsoft_logout_url:
            return werkzeug_redirect(microsoft_logout_url, code=302)
        return werkzeug_redirect(
            f"{request.httprequest.host_url.rstrip('/')}{redirect}", code=302)


# Import and override PortalEmployee AFTER it is defined
# We do this at import time since controllers/__init__.py imports this file
# after employee_self_service_portal is already loaded (due to depends order)
try:
    from odoo.addons.employee_self_service_portal.controllers.main import PortalEmployee

    class ITTicketPortalOverride(PortalEmployee):
        """
        Override PortalEmployee to render ticketing_it's own ticket detail template.
        This correctly handles all workflow levels (0,1,2,3) with proper
        Assigned To and Ticket Progress sections.
        """

        @http.route(['/my/tickets/<int:ticket_id>'], type='http', auth='user',
                    website=True, sitemap=False)
        def portal_my_ticket_detail(self, ticket_id, **kw):
            employee = request.env['hr.employee'].sudo().search(
                [('user_id', '=', request.env.uid)], limit=1)

            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/tickets')

            user = request.env.user
            is_owner = bool(employee) and ticket.employee_id.id == employee.id
            is_approver = (
                user == ticket.line_manager_id
                or user == ticket.it_manager_id
                or user.has_group('ticketing_it.group_it_manager')
            )
            is_assignee, can_start_work, can_mark_done = self._it_ticket_assignee_flags(ticket)
            if not (is_owner or is_approver or is_assignee):
                return request.redirect('/my/tickets')

            attachments = request.env['ir.attachment'].sudo().search([
                ('res_model', '=', 'it.ticket'),
                ('res_id', '=', ticket.id),
            ])
            for att in attachments:
                if not att.access_token:
                    att.generate_access_token()
            attachments.invalidate_recordset(['access_token'])

            can_approve, can_reject = self._it_ticket_approver_flags(ticket)

            return request.render('ticketing_it.portal_ticket_detail_it', {
                'ticket': ticket,
                'page_name': 'tickets',
                'ticket_attachments': attachments,
                'employee': employee,
                'can_approve': can_approve,
                'can_reject': can_reject,
                'can_start_work': can_start_work,
                'can_mark_done': can_mark_done,
                'error': kw.get('error'),
                'error_message': kw.get('error_msg', ''),
            })

        # ── Helpers ──────────────────────────────────────────────────────

        def _it_ticket_approver_flags(self, ticket):
            """Return (can_approve, can_reject) for the CURRENT portal user on this ticket.
            Only Line Manager and IT Manager can act from the portal — HR approval
            stays backend-only, same as before."""
            user = request.env.user
            state = ticket.state
            if state == 'manager_approval':
                ok = bool(ticket.line_manager_id) and user == ticket.line_manager_id
            elif state == 'it_approval':
                ok = user.has_group('ticketing_it.group_it_manager')
            else:
                ok = False
            return ok, ok

        def _it_ticket_assignee_flags(self, ticket):
            """Return (is_assignee, can_start_work, can_mark_done) for the CURRENT
            portal user on this ticket.

            Two ways to qualify:
            1. You're the specific person auto-picked as assigned_to_id (unchanged,
               still true for the flat-fallback / unconfigured sub-category case).
            2. You're a member of the group actually resolved for this ticket's
               sub-category (it.ticket.type.it_support_group_id) — so if that group
               has 1, 2, or 3 people in it, ALL of them can start work / mark done /
               reject this ticket, not just whoever happened to be picked as owner.
            """
            user = request.env.user
            is_direct_assignee = bool(ticket.assigned_to_id) and user == ticket.assigned_to_id
            grp = ticket.ticket_type_id.it_support_group_id if ticket.ticket_type_id else False
            is_group_member = bool(grp) and user in grp.user_ids
            is_assignee = is_direct_assignee or is_group_member
            can_start_work = is_assignee and ticket.state == 'assigned'
            can_mark_done = is_assignee and ticket.state == 'in_progress'
            return is_assignee, can_start_work, can_mark_done

        def _it_ticket_pending_for_user(self):
            """Tickets currently awaiting approval from the logged-in portal user,
            as either Line Manager or IT Manager (HR approval is backend-only)."""
            user = request.env.user
            domain = ['|',
                       '&', ('state', '=', 'manager_approval'), ('line_manager_id', '=', user.id),
                       '&', ('state', '=', 'it_approval'), ('it_manager_id', '=', user.id)]
            return request.env['it.ticket'].sudo().search(domain, order='create_date desc')

        def _it_ticket_approved_for_user(self, limit=50):
            """Tickets this user has approved — as Line Manager (manager_approval_date
            is set) or as IT Manager (it_approval_date is set) — regardless of what
            state the ticket has since moved to. Explicitly excludes rejected tickets,
            since the approval-date fields get stamped on rejection too (they just mark
            the ticket leaving that approval stage, not a positive decision)."""
            user = request.env.user
            domain = [
                ('state', '!=', 'rejected'),
                '|',
                '&', ('manager_approval_date', '!=', False), ('line_manager_id', '=', user.id),
                '&', ('it_approval_date', '!=', False), ('it_manager_id', '=', user.id),
            ]
            return request.env['it.ticket'].sudo().search(domain, order='write_date desc', limit=limit)

        def _it_ticket_rejected_for_user(self, limit=50):
            """Tickets this user rejected, as Line Manager or IT Manager."""
            user = request.env.user
            domain = [
                ('state', '=', 'rejected'),
                '|',
                ('line_manager_id', '=', user.id),
                ('it_manager_id', '=', user.id),
            ]
            return request.env['it.ticket'].sudo().search(domain, order='write_date desc', limit=limit)

        def _it_ticket_is_approver_anywhere(self):
            """True if this portal user is a Line Manager or IT Manager — either by
            security group membership (so the page is discoverable even before any
            ticket exists) or because a real ticket currently lists them as the
            line manager — used to gate access to the /my/it-approvals page."""
            user = request.env.user
            if user.has_group('ticketing_it.group_it_manager'):
                return True
            if user.has_group('ticketing_it.group_line_manager'):
                return True
            return request.env['it.ticket'].sudo().search_count(
                [('line_manager_id', '=', user.id)]) > 0

        # ── Approvals list page ──────────────────────────────────────────

        @http.route(['/my/it-approvals'], type='http', auth='user', website=True)
        def portal_it_ticket_approvals(self, filterby=None, **kw):
            if not self._it_ticket_is_approver_anywhere():
                return request.redirect('/my/ess')

            _logger.info("IT-APPROVALS DEBUG: raw filterby param = %r, user=%s",
                         filterby, request.env.user.login)

            if not filterby:
                filterby = 'pending'

            if filterby == 'approved':
                tickets = self._it_ticket_approved_for_user()
            elif filterby == 'rejected':
                tickets = self._it_ticket_rejected_for_user()
            else:
                filterby = 'pending'
                tickets = self._it_ticket_pending_for_user()

            _logger.info("IT-APPROVALS DEBUG: resolved filterby=%s, ticket_count=%s, ids=%s",
                         filterby, len(tickets), tickets.ids)

            success_message = None
            if kw.get('success') == 'approved':
                success_message = 'Ticket approved successfully.'
            elif kw.get('success') == 'rejected':
                success_message = 'Ticket rejected.'

            return request.render('ticketing_it.portal_it_ticket_approvals', {
                'tickets': tickets,
                'filterby': filterby,
                'page_name': 'it_approvals',
                'success_message': success_message,
                'error': kw.get('error'),
                'error_message': kw.get('error_msg', ''),
            })

        # ── Approve / Reject actions ─────────────────────────────────────

        @http.route(['/my/tickets/<int:ticket_id>/portal-approve'], type='http',
                    auth='user', website=True, methods=['POST'], csrf=True)
        def portal_it_ticket_approve(self, ticket_id, **kw):
            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/it-approvals')

            can_approve, _can_reject = self._it_ticket_approver_flags(ticket)
            if not can_approve:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "You are not authorised to approve this ticket, "
                            "or it is no longer pending your approval."
                        ),
                    )
                )

            comment = (kw.get('comment') or '').strip()
            redirect_to = kw.get('redirect_to') or '/my/it-approvals?success=approved'

            try:
                wizard = request.env['it.ticket.approve.wizard'].sudo().create({
                    'ticket_id': ticket.id,
                    'comment': comment,
                })
                wizard.approve_ticket()
                return request.redirect(redirect_to)
            except Exception as e:
                _logger.error("Portal IT ticket approve failed for ticket %s: %s", ticket_id, e)
                request.env.cr.rollback()
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "Could not approve this ticket. Please try again or contact IT."
                        ),
                    )
                )

        @http.route(['/my/tickets/<int:ticket_id>/portal-reject'], type='http',
                    auth='user', website=True, methods=['POST'], csrf=True)
        def portal_it_ticket_reject(self, ticket_id, **kw):
            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/it-approvals')

            _can_approve, can_reject = self._it_ticket_approver_flags(ticket)
            if not can_reject:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "You are not authorised to reject this ticket, "
                            "or it is no longer pending your approval."
                        ),
                    )
                )

            reason = (kw.get('rejection_reason') or '').strip()
            if not reason:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus("Please provide a rejection reason."),
                    )
                )

            redirect_to = kw.get('redirect_to') or '/my/it-approvals?success=rejected'

            try:
                ticket.sudo().do_reject(reason)
                return request.redirect(redirect_to)
            except Exception as e:
                _logger.error("Portal IT ticket reject failed for ticket %s: %s", ticket_id, e)
                request.env.cr.rollback()
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "Could not reject this ticket. Please try again or contact IT."
                        ),
                    )
                )

        # ── IT Support (assignee) actions ──────────────────────────────────

        @http.route(['/my/it-tickets'], type='http', auth='user', website=True)
        def portal_it_assigned_tickets(self, **kw):
            user = request.env.user
            if not request.env['it.ticket']._user_has_it_access(user):
                return request.redirect('/my/ess')
            tickets = request.env['it.ticket'].sudo().search(
                ['&', ('state', 'in', ['assigned', 'in_progress', 'done']),
                 '|', ('assigned_to_id', '=', user.id),
                      ('ticket_type_id.it_support_group_id.user_ids', 'in', [user.id])],
                order='create_date desc')
            return request.render('ticketing_it.portal_it_assigned_tickets', {
                'tickets': tickets,
                'page_name': 'it_assigned_tickets',
            })

        @http.route(['/my/tickets/<int:ticket_id>/portal-start-work'], type='http',
                    auth='user', website=True, methods=['POST'], csrf=True)
        def portal_it_ticket_start_work(self, ticket_id, **kw):
            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/tickets')

            _is_assignee, can_start_work, _can_mark_done = self._it_ticket_assignee_flags(ticket)
            if not can_start_work:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "You are not authorised to start work on this ticket, "
                            "or it is not in the right state."
                        ),
                    )
                )

            try:
                ticket.sudo().action_start_work()
                return request.redirect('/my/tickets/%d' % ticket_id)
            except Exception as e:
                _logger.error("Portal IT ticket start-work failed for ticket %s: %s", ticket_id, e)
                request.env.cr.rollback()
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "Could not start work on this ticket. Please try again or contact IT."
                        ),
                    )
                )

        @http.route(['/my/tickets/<int:ticket_id>/portal-mark-done'], type='http',
                    auth='user', website=True, methods=['POST'], csrf=True)
        def portal_it_ticket_mark_done(self, ticket_id, **kw):
            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/tickets')

            _is_assignee, _can_start_work, can_mark_done = self._it_ticket_assignee_flags(ticket)
            if not can_mark_done:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "You are not authorised to mark this ticket done, "
                            "or it is not in the right state."
                        ),
                    )
                )

            try:
                ticket.sudo().action_done()
                return request.redirect('/my/tickets/%d' % ticket_id)
            except Exception as e:
                _logger.error("Portal IT ticket mark-done failed for ticket %s: %s", ticket_id, e)
                request.env.cr.rollback()
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "Could not mark this ticket done. Please try again or contact IT."
                        ),
                    )
                )

        @http.route(['/my/tickets/<int:ticket_id>/portal-it-reject'], type='http',
                    auth='user', website=True, methods=['POST'], csrf=True)
        def portal_it_ticket_it_reject(self, ticket_id, **kw):
            """Lets the assigned IT Support user reject a ticket they were handed —
            distinct from portal-reject, which is the Line/IT Manager approval-stage
            rejection. Valid from either 'assigned' or 'in_progress', i.e. anywhere
            can_start_work or can_mark_done would currently be true. Writes the
            rejection fields directly rather than via do_reject(), since that
            method's state guard is written for the approval-stage flow only."""
            ticket = request.env['it.ticket'].sudo().browse(ticket_id)
            if not ticket.exists():
                return request.redirect('/my/tickets')

            _is_assignee, can_start_work, can_mark_done = self._it_ticket_assignee_flags(ticket)
            if not (can_start_work or can_mark_done):
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "You are not authorised to reject this ticket, "
                            "or it is not in the right state."
                        ),
                    )
                )

            remarks = (kw.get('it_rejection_remarks') or '').strip()
            if not remarks:
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus("Please provide a remark for rejecting this ticket."),
                    )
                )

            redirect_to = kw.get('redirect_to') or '/my/tickets/%d' % ticket_id

            try:
                ticket.sudo().write({
                    'state': 'rejected',
                    'rejection_reason': remarks,
                    'rejected_by_id': request.env.uid,
                })
                ticket.message_post(body=_(
                    'Rejected by IT Support (%s). Reason: %s'
                ) % (request.env.user.name, remarks))
                if ticket.employee_id and ticket.employee_id.user_id:
                    ticket._notify('ticketing_it.email_template_rejection', ticket.employee_id.user_id)
                return request.redirect(redirect_to)
            except Exception as e:
                _logger.error("Portal IT ticket IT-reject failed for ticket %s: %s", ticket_id, e)
                request.env.cr.rollback()
                return request.redirect(
                    '/my/tickets/%d?error=1&error_msg=%s' % (
                        ticket_id,
                        urllib.parse.quote_plus(
                            "Could not reject this ticket: %s" % str(e)
                        ),
                    )
                )

    _logger.info("ticketing_it: ITTicketPortalOverride registered successfully")

except ImportError as e:
    _logger.warning("ticketing_it: could not override portal ticket detail: %s", e)