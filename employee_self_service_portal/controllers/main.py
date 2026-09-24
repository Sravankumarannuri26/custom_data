# controllers/main.py
import pytz

from odoo import http, fields
from odoo.http import request
from odoo.tools import html2plaintext
from .access_helpers import check_portal_access, has_feature_access
import html
import json
import pytz
import logging
import base64
import io
import json as json_lib
from odoo.exceptions import ValidationError
import pikepdf
import traceback
import urllib.parse
from datetime import  timedelta
import re

# Set up logger
_logger = logging.getLogger(__name__)

# Constants for model names and URLs
# CRM_TAG_MODEL = 'crm.tag'
# CRM_REDIRECT_URL = '/my/employee/crm'
HR_EMPLOYEE_MODEL = 'hr.employee'
HR_ATTENDANCE_MODEL = 'hr.attendance'
# CRM_LEAD_MODEL = 'crm.lead'
# CRM_STAGE_MODEL = 'crm.stage'
MY_EMPLOYEE_URL = '/my/employee'


def get_user_timezone():
    """Get the user's timezone (or fallback to company or UTC)."""
    import pytz
    user_tz = request.env.user.tz or request.env.company.timezone or 'UTC'
    return user_tz


def get_local_datetime(dt=None):
    """Convert UTC datetime to user's local timezone."""
    import pytz
    from datetime import datetime

    if dt is None:
        dt = datetime.now()

    user_tz = get_user_timezone()
    user_pytz = pytz.timezone(user_tz)

    if hasattr(dt, 'tzinfo') and dt.tzinfo:
        # If datetime already has tzinfo, convert to user timezone
        return dt.astimezone(user_pytz)
    else:
        # Assume the datetime is UTC if no tzinfo
        utc_dt = dt.replace(tzinfo=pytz.UTC)
        return utc_dt.astimezone(user_pytz)


# def _process_tag_ids(post):
#     """Refactored to reduce cognitive complexity."""
#     tag_ids = []
#     # Get tag ids from post (handle both list and string cases)
#     if hasattr(post, 'getlist'):
#         tag_ids = post.getlist('tag_ids[]') or post.getlist('tag_ids')
#     else:
#         tag_ids = post.get('tag_ids[]', []) or post.get('tag_ids', [])
#         if isinstance(tag_ids, str):
#             tag_ids = tag_ids.split(',') if ',' in tag_ids else [tag_ids]
#     if not isinstance(tag_ids, list):
#         tag_ids = [tag_ids]
#     tag_id_list = []
#     for tag in tag_ids or []:
#         if not tag:
#             continue
#         try:
#             tag_id_list.append(int(tag))
#         except (ValueError, TypeError):
#             tag_rec = request.env[CRM_TAG_MODEL].sudo().search([('name', '=', tag)], limit=1)
#             if not tag_rec:
#                 tag_rec = request.env[CRM_TAG_MODEL].sudo().create({'name': tag})
#             tag_id_list.append(tag_rec.id)
#     tag_id_list = [int(t) for t in tag_id_list if t]
#     import logging
#     _logger = logging.getLogger(__name__)
#     _logger.info('ESS Portal: tag_id_list to write: %s', tag_id_list)
#     return tag_id_list


# def _process_partner_field(field_value, field_name='partner_id'):
#     """Process partner field - handle existing IDs or create new partners."""
#     if not field_value:
#         return False
#
#     # Try to convert to int (existing partner ID)
#     try:
#         partner_id = int(field_value)
#         # Verify partner exists
#         partner = request.env['res.partner'].sudo().browse(partner_id)
#         if partner.exists():
#             return partner_id
#     except (ValueError, TypeError):
#         pass
#
#     # Field value is a string - create new partner
#     if isinstance(field_value, str) and field_value.strip():
#         partner_name = field_value.strip()
#
#         # Check if partner already exists by name
#         existing_partner = request.env['res.partner'].sudo().search([
#             ('name', '=ilike', partner_name),
#             ('is_company', '=', True),
#             ('company_id', '=', request.env.company.id)
#         ], limit=1)
#
#         if existing_partner:
#             return existing_partner.id
#
#         # Create new partner
#         # partner_vals = {'name': partner_name}
#
#         # For point of contact, set as individual (not company)
#         # if field_name == 'point_of_contact_id':
#         #   partner_vals['is_company'] = False
#         # else:
#         # For main customer, default to company
#         #    partner_vals['is_company'] = True
#
#         # new_partner = request.env['res.partner'].sudo().create(partner_vals)
#
#     #  import logging
#     # _logger = logging.getLogger(__name__)
#     # _logger.info('ESS Portal: Created new partner: %s (ID: %s)', partner_name, new_partner.id)
#
#     # return new_partner.id
#
#     return False


class PortalEmployee(http.Controller):

    def _get_many2one_id(self, value, model_name, field_name='name'):
        """Helper to safely get ID from either int or string"""
        if not value:
            return False
        try:
            return int(value)
        except (ValueError, TypeError):
            record = request.env[model_name].sudo().search([
                (field_name, '=', value)
            ], limit=1)
            return record.id if record else False

    def _get_employee(self):
        return request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)

    @http.route(MY_EMPLOYEE_URL, type='http', auth='user', website=True)
    def portal_employee_profile(self, **kw):
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        countries = request.env['res.country'].sudo().search([], order='name')
        latest_request = request.env['hr.profile.change.request'].sudo().search(
            [('employee_id', '=', employee.id)], order='id desc', limit=1
        )
        notification = self._get_notification(latest_request)
        return request.render('employee_self_service_portal.portal_employee_profile_personal', {
            'employee': employee,
            'section': 'personal',
            'countries': countries,
            'notification': notification,
        })

    @http.route(MY_EMPLOYEE_URL + '/attendance/checkin', type='http', auth='user', methods=['POST'], website=True)
    def check_in(self, **post):
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=1&error_msg=' + urllib.parse.quote_plus(
            "Check-in is temporarily unavailable. Please contact HR directly."
        ))

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL + '?error=employee_not_found')

        # Enhanced validation and duplicate prevention
        try:
            # Check for existing open attendance
            existing_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], limit=1)

            if existing_attendance:
                return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=already_checked_in')

            # Validate check-in time (business hours)
            from datetime import datetime
            import pytz

            # Get user's timezone (or use company timezone as fallback)
            user_tz = request.env.user.tz or request.env.company.timezone or 'UTC'
            user_pytz = pytz.timezone(user_tz)

            # Get current time in user's timezone
            utc_now = datetime.now(pytz.UTC)
            local_now = utc_now.astimezone(user_pytz)
            current_time = local_now.time()

            # Basic business hours validation (6 AM to 11 PM)
            from datetime import time
            min_time = time(6, 0)  # 6:00 AM
            max_time = time(23, 0)  # 11:00 PM

            if not (min_time <= current_time <= max_time):
                return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=invalid_time')

            # Location and other data
            in_latitude = post.get('in_latitude')
            in_longitude = post.get('in_longitude')
            check_in_location = post.get('check_in_location')

            # Log location data for debugging
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(
                f"Check-in location data - lat: {in_latitude}, long: {in_longitude}, location: {check_in_location}")
            _logger.info(f"User timezone: {user_tz}, Local time: {local_now}")

            # Check if it's a late arrival (after 9:30 AM)
            late_threshold = time(9, 30)
            is_late = current_time > late_threshold

            # If no location is provided, try to get a default one
            if not check_in_location:
                check_in_location = post.get('location') or 'Check-in from Portal'

            # Use user's timezone to properly record time
            # Use format_datetime to create a datetime string with timezone info
            local_check_in = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())

            vals = {
                'employee_id': employee.id,
                'check_in': fields.Datetime.now(),  # Server will convert this appropriately
                'check_in_location': check_in_location,
            }

            # Make sure we convert latitude/longitude to float if provided
            try:
                if in_latitude:
                    vals['in_latitude'] = float(in_latitude)
                if in_longitude:
                    vals['in_longitude'] = float(in_longitude)
            except (ValueError, TypeError):
                _logger.warning(f"Invalid latitude/longitude values: {in_latitude}, {in_longitude}")

            # Create attendance record
            attendance = request.env[HR_ATTENDANCE_MODEL].sudo().create(vals)

            # Log successful check-in
            _logger.info(f"Check-in successful for employee {employee.name} at {local_now}")

            return request.redirect(MY_EMPLOYEE_URL + '/attendance?success=checked_in')

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Check-in failed: %s", e)
            return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=checkin_failed')

    @http.route(MY_EMPLOYEE_URL + '/attendance/quick-checkin', type='http', auth='user', methods=['POST'], website=True,
                csrf=False)
    def quick_check_in(self, **post):
        """Quick check-in from dashboard"""
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        return request.make_response(json.dumps({
            'status': 'error',
            'message': 'Check-in is temporarily unavailable. Please contact HR directly.'
        }), headers={'Content-Type': 'application/json'})

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.make_response(json.dumps({'status': 'error', 'message': 'Employee not found'}),
                                         headers={'Content-Type': 'application/json'})

        try:
            # REMOVED: Check for existing open attendance
            # We now allow multiple check-ins per day, so we don't need to validate
            # if there's an existing open attendance

            # Validate check-in time (business hours) - consistent with attendance page logic
            from datetime import datetime, time
            now = datetime.now()
            current_time = now.time()

            # Basic business hours validation (6 AM to 11 PM)
            min_time = time(6, 0)  # 6:00 AM
            max_time = time(23, 0)  # 11:00 PM

            if not (min_time <= current_time <= max_time):
                return request.make_response(json.dumps({
                    'status': 'error',
                    'message': 'Check-in not allowed at this time (6 AM - 11 PM only)'
                }), headers={'Content-Type': 'application/json'})

            # Get location data from POST request
            in_latitude = post.get('in_latitude')
            in_longitude = post.get('in_longitude')
            check_in_location = post.get('check_in_location') or post.get('location') or 'Quick Check-in from Dashboard'

            # Create attendance record
            vals = {
                'employee_id': employee.id,
                'check_in': fields.Datetime.now(),
                'check_in_location': check_in_location,
            }

            # Make sure we convert latitude/longitude to float if provided
            try:
                if in_latitude:
                    vals['in_latitude'] = float(in_latitude)
                if in_longitude:
                    vals['in_longitude'] = float(in_longitude)
            except (ValueError, TypeError):
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Invalid quick check-in latitude/longitude values: {in_latitude}, {in_longitude}")

            attendance = request.env[HR_ATTENDANCE_MODEL].sudo().create(vals)

            # Log successful check-in
            _logger.info(f"Quick check-in successful for employee {employee.name} at {now}")

            return request.make_response(json.dumps({'status': 'success', 'message': 'Checked in successfully'}),
                                         headers={'Content-Type': 'application/json'})

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Quick check-in failed: %s", e)
            return request.make_response(json.dumps({'status': 'error', 'message': 'Check-in failed'}),
                                         headers={'Content-Type': 'application/json'})

    @http.route(MY_EMPLOYEE_URL + '/attendance/checkout', type='http', auth='user', methods=['POST'], website=True)
    def check_out(self, **post):
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=1&error_msg=' + urllib.parse.quote_plus(
            "Check-out is temporarily unavailable. Please contact HR directly."
        ))

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL + '?error=employee_not_found')

        try:
            # Find the last open attendance record
            last_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], order='check_in desc', limit=1)

            if not last_attendance:
                return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=no_checkin_found')

            # Validate minimum work duration (at least 30 minutes)
            from datetime import datetime, timedelta
            import pytz

            # Get user's timezone (or use company timezone as fallback)
            user_tz = request.env.user.tz or request.env.company.timezone or 'UTC'
            user_pytz = pytz.timezone(user_tz)

            # Get current time in user's timezone
            utc_now = datetime.now(pytz.UTC)
            local_now = utc_now.astimezone(user_pytz)

            check_in_time = fields.Datetime.from_string(last_attendance.check_in)

            # Convert check_in_time to user timezone for proper comparison
            check_in_time_local = check_in_time.replace(tzinfo=pytz.UTC).astimezone(user_pytz)

            # Re-enabled 30-minute validation
            min_duration = timedelta(minutes=30)
            if (local_now - check_in_time_local) < min_duration:
                return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=minimum_duration_not_met')

            # Location and other data
            out_latitude = post.get('out_latitude')
            out_longitude = post.get('out_longitude')
            check_out_location = post.get('check_out_location')

            # Log location data for debugging
            import logging
            _logger = logging.getLogger(__name__)
            _logger.info(
                f"Check-out location data - lat: {out_latitude}, long: {out_longitude}, location: {check_out_location}")
            _logger.info(f"User timezone: {user_tz}, Local time: {local_now}")

            # Check if it's an early departure (before 5:30 PM)
            from datetime import time
            early_threshold = time(17, 30)
            current_time = local_now.time()
            is_early_departure = current_time < early_threshold

            # If no location is provided, try to get a default one
            if not check_out_location:
                check_out_location = post.get('location') or 'Check-out from Portal'

            # Use format_datetime to create a datetime string with timezone info
            local_check_out = fields.Datetime.context_timestamp(request.env.user, fields.Datetime.now())

            vals = {
                'check_out': fields.Datetime.now(),  # Server will convert this appropriately
                'check_out_location': check_out_location,
                'is_auto_checkout': False,  # Explicit manual checkout
            }

            # Make sure we convert latitude/longitude to float if provided
            try:
                if out_latitude:
                    vals['out_latitude'] = float(out_latitude)
                if out_longitude:
                    vals['out_longitude'] = float(out_longitude)
            except (ValueError, TypeError):
                _logger.warning(f"Invalid latitude/longitude values: {out_latitude}, {out_longitude}")

            # Update attendance record
            last_attendance.sudo().write(vals)

            # Re-browse to get updated computed fields
            updated_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().browse(last_attendance.id)

            # Log successful check-out with worked hours
            _logger.info(
                f"Check-out successful for employee {employee.name}. Worked hours: {updated_attendance.worked_hours}")

            return request.redirect(MY_EMPLOYEE_URL + '/attendance?success=checked_out')

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Check-out failed: %s", e)
            return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=checkout_failed')

    @http.route(MY_EMPLOYEE_URL + '/attendance/quick-checkout', type='http', auth='user', methods=['POST'],
                website=True, csrf=False)
    def quick_check_out(self, **post):
        """Quick check-out from dashboard"""
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        return request.make_response(json.dumps({
            'status': 'error',
            'message': 'Check-out is temporarily unavailable. Please contact HR directly.'
        }), headers={'Content-Type': 'application/json'})

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.make_response(json.dumps({'status': 'error', 'message': 'Employee not found'}),
                                         headers={'Content-Type': 'application/json'})

        try:
            # Find the last open attendance record
            last_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_out', '=', False)
            ], order='check_in desc', limit=1)

            if not last_attendance:
                return request.make_response(json.dumps({'status': 'error', 'message': 'No active check-in found'}),
                                             headers={'Content-Type': 'application/json'})

            # Validate minimum work duration (at least 30 minutes)
            from datetime import datetime, timedelta
            import pytz

            # Get user's timezone (or use company timezone as fallback)
            user_tz = request.env.user.tz or request.env.company.timezone or 'UTC'
            user_pytz = pytz.timezone(user_tz)

            # Get current time in user's timezone
            utc_now = datetime.now(pytz.UTC)
            local_now = utc_now.astimezone(user_pytz)

            check_in_time = fields.Datetime.from_string(last_attendance.check_in)

            # Convert check_in_time to user timezone for proper comparison
            check_in_time_local = check_in_time.replace(tzinfo=pytz.UTC).astimezone(user_pytz)

            # Re-enabled 30-minute validation
            min_duration = timedelta(minutes=30)
            if (local_now - check_in_time_local) < min_duration:
                return request.make_response(json.dumps({
                    'status': 'error',
                    'message': 'Minimum work duration not met (30 minutes required)'
                }), headers={'Content-Type': 'application/json'})

            # Get location data from POST request
            out_latitude = post.get('out_latitude')
            out_longitude = post.get('out_longitude')
            check_out_location = post.get('check_out_location') or post.get(
                'location') or 'Quick Check-out from Dashboard'

            # Update attendance record
            vals = {
                'check_out': fields.Datetime.now(),
                'check_out_location': check_out_location,
                'is_auto_checkout': False,  # Explicit manual checkout
            }

            # Make sure we convert latitude/longitude to float if provided
            try:
                if out_latitude:
                    vals['out_latitude'] = float(out_latitude)
                if out_longitude:
                    vals['out_longitude'] = float(out_longitude)
            except (ValueError, TypeError):
                import logging
                _logger = logging.getLogger(__name__)
                _logger.warning(f"Invalid quick check-out latitude/longitude values: {out_latitude}, {out_longitude}")

            last_attendance.sudo().write(vals)

            # Get worked hours
            updated_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().browse(last_attendance.id)
            worked_hours = round(updated_attendance.worked_hours, 2)

            return request.make_response(json.dumps({
                'status': 'success',
                'message': f'Checked out successfully. Worked {worked_hours} hours'
            }), headers={'Content-Type': 'application/json'})

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Quick check-out failed: %s", e)
            return request.make_response(json.dumps({'status': 'error', 'message': 'Check-out failed'}),
                                         headers={'Content-Type': 'application/json'})

    @http.route(MY_EMPLOYEE_URL + '/attendance', type='http', auth='user', website=True)
    @check_portal_access('attendance')
    def portal_attendance_history(self, **kwargs):
        from datetime import datetime
        import pytz

        # Get user's timezone
        user_timezone = get_user_timezone()
        user_pytz = pytz.timezone(user_timezone)

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)

        # Get current time in user's timezone
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(user_pytz)

        # Use current month/year as default if not provided
        month = int(kwargs.get('month', local_now.month))
        year = int(kwargs.get('year', local_now.year))

        domain = [('employee_id', '=', employee.id)]
        if month and year:
            from calendar import monthrange
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
            domain += [('check_in', '>=', start_date.strftime('%Y-%m-%d 00:00:00')),
                       ('check_in', '<=', end_date.strftime('%Y-%m-%d 23:59:59'))]

        attendances = request.env[HR_ATTENDANCE_MODEL].sudo().search(
            domain, order='check_in desc', limit=50)  # Increased limit for better analytics

        today_att = None
        today_str = local_now.strftime('%Y-%m-%d')

        # Find today's attendance based on user's timezone
        for att in attendances:
            if att.check_in:
                check_in_local = fields.Datetime.context_timestamp(request.env.user, att.check_in)
                if check_in_local.strftime('%Y-%m-%d') == today_str:
                    today_att = att
                    break

        # Enhanced analytics
        analytics_data = self._get_attendance_analytics(employee, month, year)

        # For dropdowns
        current_year = local_now.year
        years = list(range(current_year - 5, current_year + 2))
        months = [
            {'value': i, 'name': datetime(2000, i, 1).strftime('%B')} for i in range(1, 13)
        ]

        # Status messages
        success_message = None
        error_message = None

        if kwargs.get('success') == 'checked_in':
            success_message = "Successfully checked in!"
        elif kwargs.get('success') == 'checked_out':
            success_message = "Successfully checked out!"
        elif kwargs.get('error') == 'already_checked_in':
            error_message = "You are already checked in. Please check out first."
        elif kwargs.get('error') == 'no_checkin_found':
            error_message = "No active check-in found."
        elif kwargs.get('error') == 'invalid_time':
            error_message = f"Check-in not allowed at this time (6 AM - 11 PM only). Your local time: {local_now.strftime('%I:%M %p')} ({user_timezone})."
        elif kwargs.get('error') == 'minimum_duration_not_met':
            error_message = "Minimum work duration not met (30 minutes required)."
        elif kwargs.get('error'):
            error_message = "An error occurred. Please try again."

        return request.render('employee_self_service_portal.portal_attendance', {
            'attendances': attendances,
            'employee': employee,
            'today_att': today_att,
            'selected_month': month,
            'selected_year': year,
            'years': years,
            'months': months,
            'analytics': analytics_data,
            'success_message': success_message,
            'error_message': error_message,
            'user_timezone': user_timezone,
            'format_datetime': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%I:%M %p') if dt else '',
            'format_date': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%d/%m/%Y') if dt else '',
            'format_day': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%A') if dt else '',
        })

    def _get_attendance_analytics(self, employee, month, year):
        """Calculate comprehensive attendance analytics with timezone awareness"""
        from datetime import datetime, timedelta, time
        from calendar import monthrange
        from collections import defaultdict
        import pytz

        # Get user's timezone
        user_timezone = get_user_timezone()
        user_pytz = pytz.timezone(user_timezone)

        # Date range for the selected month in user's timezone
        start_date = datetime(year, month, 1, tzinfo=user_pytz)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59, tzinfo=user_pytz)

        # Convert to UTC for database query
        start_date_utc = start_date.astimezone(pytz.UTC)
        end_date_utc = end_date.astimezone(pytz.UTC)

        # Get all attendance records for the month
        attendances = request.env[HR_ATTENDANCE_MODEL].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', start_date_utc),
            ('check_in', '<=', end_date_utc)
        ])

        # Group attendances by day for accurate day counting (using local timezone)
        attendance_by_day = defaultdict(list)
        for att in attendances:
            # Convert check_in time to user's timezone for day grouping
            check_in_local = fields.Datetime.context_timestamp(request.env.user, att.check_in)
            day_key = check_in_local.strftime('%Y-%m-%d')
            attendance_by_day[day_key].append(att)

        # Calculate metrics
        total_days = len(attendance_by_day)  # Unique days with attendance

        # Calculate total hours per day and then sum them up
        total_hours = 0
        for day, day_attendances in attendance_by_day.items():
            day_hours = sum(att.worked_hours for att in day_attendances if att.worked_hours)
            total_hours += day_hours

        avg_hours = total_hours / total_days if total_days > 0 else 0

        # Calculate late arrivals by day - only count one late arrival per day
        # Define late threshold (9:30 AM)
        late_threshold = time(9, 30)
        late_arrivals = 0

        for day, day_attendances in attendance_by_day.items():
            # Sort by check-in time to get the first check-in of the day
            day_attendances.sort(key=lambda x: x.check_in)
            # Convert check-in time to user's timezone
            first_check_in = fields.Datetime.context_timestamp(request.env.user, day_attendances[0].check_in)
            # Check if first check-in of the day was late
            if first_check_in.time() > late_threshold:
                late_arrivals += 1

        # Working days in month (excluding weekends)
        working_days = 0
        current_date = start_date.date()
        while current_date <= end_date.date():
            if current_date.weekday() < 5:  # Monday=0, Sunday=6
                working_days += 1
            current_date += timedelta(days=1)

        # Attendance percentage
        attendance_percentage = (total_days / working_days * 100) if working_days > 0 else 0

        # Early departures (before 5:30 PM) - count only days with early departure
        early_threshold = time(17, 30)
        early_departures = 0

        for day, day_attendances in attendance_by_day.items():
            # Check if any attendance records for the day had an early departure
            early_departure = False
            for att in day_attendances:
                if att.check_out:
                    # Convert check-out time to user's timezone
                    check_out_local = fields.Datetime.context_timestamp(request.env.user, att.check_out)
                    if check_out_local.time() < early_threshold:
                        early_departure = True
                        break
            if early_departure:
                early_departures += 1

        # Overtime (more than 8.5 hours per day)
        overtime_days = 0
        for day, day_attendances in attendance_by_day.items():
            day_hours = sum(att.worked_hours for att in day_attendances if att.worked_hours)
            if day_hours > 8.5:
                overtime_days += 1

        # This week's data
        # Get current time in user's timezone
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(user_pytz)

        # Calculate week start in user's timezone
        week_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=local_now.weekday())
        week_start_utc = week_start.astimezone(pytz.UTC)

        week_attendances = request.env[HR_ATTENDANCE_MODEL].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', week_start_utc),
            ('check_in', '<=', utc_now)
        ])

        # Group week attendances by day for consistent calculation
        week_attendance_by_day = defaultdict(list)
        for att in week_attendances:
            # Convert check_in time to user's timezone for day grouping
            check_in_local = fields.Datetime.context_timestamp(request.env.user, att.check_in)
            day_key = check_in_local.strftime('%Y-%m-%d')
            week_attendance_by_day[day_key].append(att)

        # Calculate total hours per day and then sum them up
        this_week_hours = 0
        for day, day_attendances in week_attendance_by_day.items():
            day_hours = sum(att.worked_hours for att in day_attendances if att.worked_hours)
            this_week_hours += day_hours

        return {
            'total_days': total_days,
            'total_hours': round(total_hours, 2),
            'avg_hours': round(avg_hours, 2),
            'working_days': working_days,
            'attendance_percentage': round(attendance_percentage, 1),
            'late_arrivals': late_arrivals,
            'early_departures': early_departures,
            'overtime_days': overtime_days,
            'this_week_hours': round(this_week_hours, 2),
            'month_name': datetime(year, month, 1).strftime('%B %Y')
        }

    @http.route(MY_EMPLOYEE_URL + '/attendance/analytics', type='http', auth='user', website=True)
    def portal_attendance_analytics(self, **kwargs):
        """Dedicated analytics page for attendance"""
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL)

        from datetime import datetime
        import pytz

        # Get user's timezone
        user_timezone = get_user_timezone()
        user_pytz = pytz.timezone(user_timezone)

        # Get current time in user's timezone
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(user_pytz)

        # Get analytics for current month and last 3 months
        analytics_months = []
        for i in range(4):
            from datetime import timedelta
            month_date = local_now.replace(day=1) - timedelta(days=i * 30)
            month_analytics = self._get_attendance_analytics(employee, month_date.month, month_date.year)
            analytics_months.append(month_analytics)

        return request.render('employee_self_service_portal.portal_attendance_analytics', {
            'employee': employee,
            'analytics_months': analytics_months,
            'current_month': analytics_months[0] if analytics_months else {},
            'user_timezone': user_timezone,
            'format_datetime': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%I:%M %p') if dt else '',
            'format_date': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%d/%m/%Y') if dt else '',
            'format_day': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%A') if dt else '',
        })

    @http.route(MY_EMPLOYEE_URL + '/attendance/export', type='http', auth='user', website=True)
    def portal_attendance_export(self, **kwargs):
        """Export attendance data to Excel"""
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL)

        try:
            import io
            import xlsxwriter
            from datetime import datetime, timedelta, time

            # Get date range (default: current month)
            now = datetime.now()
            start_date = kwargs.get('start_date')
            end_date = kwargs.get('end_date')

            if not start_date:
                start_date = now.replace(day=1).strftime('%Y-%m-%d')
            if not end_date:
                from calendar import monthrange
                last_day = monthrange(now.year, now.month)[1]
                end_date = now.replace(day=last_day).strftime('%Y-%m-%d')

            # Get attendance data
            attendances = request.env[HR_ATTENDANCE_MODEL].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', start_date + ' 00:00:00'),
                ('check_in', '<=', end_date + ' 23:59:59')
            ], order='check_in desc')

            # Create Excel file
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Attendance Report')

            # Define formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4472C4',
                'font_color': 'white',
                'border': 1
            })

            date_format = workbook.add_format({'num_format': 'dd/mm/yyyy'})
            time_format = workbook.add_format({'num_format': 'hh:mm AM/PM'})
            hours_format = workbook.add_format({'num_format': '0.00'})

            # Headers
            headers = [
                'Date', 'Day', 'Check-In Time', 'Check-In Location',
                'Check-Out Time', 'Check-Out Location', 'Worked Hours', 'Status'
            ]

            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            # Data rows
            for row, att in enumerate(attendances, 1):
                check_in_date = att.check_in.date() if att.check_in else None
                day_name = att.check_in.strftime('%A') if att.check_in else ''
                check_in_time = att.check_in.time() if att.check_in else None
                check_out_time = att.check_out.time() if att.check_out else None

                # Determine status
                status = 'Complete' if att.check_out else 'Active'
                if att.check_in and att.check_in.time() > time(9, 30):
                    status += ' (Late)'
                if att.check_out and att.check_out.time() < time(17, 30):
                    status += ' (Early)'

                worksheet.write(row, 0, check_in_date, date_format)
                worksheet.write(row, 1, day_name)
                worksheet.write(row, 2, check_in_time, time_format)
                worksheet.write(row, 3, att.check_in_location or '')
                worksheet.write(row, 4, check_out_time, time_format)
                worksheet.write(row, 5, att.check_out_location or '')
                worksheet.write(row, 6, att.worked_hours or 0, hours_format)
                worksheet.write(row, 7, status)

            # Summary section
            summary_row = len(attendances) + 3
            worksheet.write(summary_row, 0, 'SUMMARY', header_format)
            worksheet.write(summary_row + 1, 0, 'Total Days:')
            worksheet.write(summary_row + 1, 1, len(attendances))
            worksheet.write(summary_row + 2, 0, 'Total Hours:')
            worksheet.write(summary_row + 2, 1, sum(att.worked_hours for att in attendances if att.worked_hours),
                            hours_format)
            worksheet.write(summary_row + 3, 0, 'Average Hours/Day:')
            avg_hours = sum(att.worked_hours for att in attendances if att.worked_hours) / len(
                attendances) if attendances else 0
            worksheet.write(summary_row + 3, 1, avg_hours, hours_format)

            # Auto-adjust column widths
            worksheet.set_column('A:A', 12)  # Date
            worksheet.set_column('B:B', 10)  # Day
            worksheet.set_column('C:C', 15)  # Check-in time
            worksheet.set_column('D:D', 30)  # Check-in location
            worksheet.set_column('E:E', 15)  # Check-out time
            worksheet.set_column('F:F', 30)  # Check-out location
            worksheet.set_column('G:G', 12)  # Worked hours
            worksheet.set_column('H:H', 15)  # Status

            workbook.close()
            output.seek(0)

            # Generate filename
            filename = f"attendance_report_{employee.name}_{start_date}_to_{end_date}.xlsx"
            filename = filename.replace(' ', '_').replace('/', '-')

            # Return file
            return request.make_response(
                output.getvalue(),
                headers=[
                    ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                    ('Content-Disposition', f'attachment; filename="{filename}"')
                ]
            )

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error("Attendance export failed: %s", e)
            return request.redirect(MY_EMPLOYEE_URL + '/attendance?error=export_failed')

    @http.route(MY_EMPLOYEE_URL + '/edit', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_edit(self, **post):
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL)
        if http.request.httprequest.method == 'POST':
            vals = {}

            if post.get('work_email'):
                import re
                email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                if re.match(email_pattern, post.get('work_email')):
                    vals['work_email'] = post.get('work_email')

            if post.get('work_phone'):
                vals['work_phone'] = post.get('work_phone')
            if post.get('birthday'):
                vals['birthday'] = post.get('birthday')
            if post.get('gender'):
                vals['gender'] = post.get('gender')
            if post.get('marital'):
                vals['marital'] = post.get('marital')

                # Identity documents
            if post.get('emirates_id_number'):
                vals['emirates_id_number'] = post.get('emirates_id_number')
            if post.get('emirates_expiry_date'):
                vals['emirates_expiry_date'] = post.get('emirates_expiry_date')
            if post.get('issue_date'):
                vals['issue_date'] = post.get('issue_date')
            if post.get('expiry_date'):
                vals['expiry_date'] = post.get('expiry_date')
            if post.get('passport_id'):
                vals['passport_id'] = post.get('passport_id')
            if post.get('ssnid'):
                vals['ssnid'] = post.get('ssnid')
            if post.get('issue_countries_id'):
                vals['issue_countries_id'] = self._get_many2one_id(
                    post.get('issue_countries_id'), 'res.country')

                # Contact information
            # Write regular fields
            try:
                employee.sudo().write(vals)
            except Exception as e:
                _logger.error("Error saving employee data: %s", str(e))

            # Write private fields separately with sudo
            private_vals = {}
            if post.get('private_email'):
                private_vals['private_email'] = post.get('private_email')
            if post.get('private_phone'):
                private_vals['private_phone'] = post.get('private_phone')
            if post.get('private_street'):
                private_vals['private_street'] = post.get('private_street')
            if post.get('private_street2'):
                private_vals['private_street2'] = post.get('private_street2')
            if post.get('private_city'):
                private_vals['private_city'] = post.get('private_city')
            if post.get('private_zip'):
                private_vals['private_zip'] = post.get('private_zip')

            if private_vals:
                try:
                    # Use env with superuser to bypass private field restrictions
                    request.env['hr.employee'].sudo().browse(employee.id).write(private_vals)
                    _logger.info("Private fields saved: %s", list(private_vals.keys()))
                except Exception as e:
                    _logger.error("Error saving private fields: %s", str(e))

                # Emergency contact
            if post.get('emergency_contact'):
                vals['emergency_contact'] = post.get('emergency_contact')
            if post.get('emergency_phone'):
                vals['emergency_phone'] = post.get('emergency_phone')

                # Private Contact (from inherited template)
            # if post.get('private_email'):
            #     vals['private_email'] = post.get('private_email')
            # if post.get('private_phone'):
            #     vals['private_phone'] = post.get('private_phone')

            # Personal Information (from inherited template)
            # if post.get('legal_name'):
            #     vals['legal_name'] = post.get('legal_name')
            # if post.get('place_of_birth'):
            #     vals['place_of_birth'] = post.get('place_of_birth')

            # Visa & Work Permit (from inherited template)
            if post.get('visa_no'):
                vals['visa_no'] = post.get('visa_no')
            if post.get('permit_no'):
                vals['permit_no'] = post.get('permit_no')

                # Citizenship (from inherited template)
            if post.get('identification_id'):
                vals['identification_id'] = post.get('identification_id')

                # Family (from inherited template)
            if post.get('study_field'):
                vals['study_field'] = post.get('study_field')
            if post.get('certificate'):
                vals['certificate'] = post.get('certificate')
            if post.get('children'):
                try:
                    vals['children'] = int(post.get('children'))
                except (ValueError, TypeError):
                    pass
            # Personal Details
            # vals['work_email'] = post.get('work_email')
            # vals['work_phone'] = post.get('work_phone')
            # vals['birthday'] = post.get('birthday')
            # vals['gender'] = post.get('gender')
            # vals['marital'] = post.get('marital')
            # # Experience & Skills
            # vals['x_experience'] = post.get('x_experience')
            # vals['x_skills'] = post.get('x_skills')
            # # Certifications
            # vals['x_certifications'] = post.get('x_certifications')
            # # Bank Details
            # vals['x_bank_account'] = post.get('x_bank_account')
            # vals['x_bank_name'] = post.get('x_bank_name')
            # vals['x_ifsc'] = post.get('x_ifsc')
            # Only update fields that are present in the form
            vals = {k: v for k, v in vals.items() if v is not None}
            if vals:
                employee.sudo().write(vals)
            return request.redirect(MY_EMPLOYEE_URL)
        return request.render('employee_self_service_portal.portal_employee_edit', {
            'employee': employee,
        })

    @http.route('/my/ess', type='http', auth='user', website=True)
    def portal_ess_dashboard(self, **kwargs):
        # Set enhanced dashboard as default
        return self._render_ess_dashboard('employee_self_service_portal.portal_ess_dashboard_enhanced', **kwargs)

    @http.route('/my/ess/classic', type='http', auth='user', website=True)
    def portal_ess_dashboard_classic(self, **kwargs):
        # Keep the classic view accessible via /my/ess/classic
        return self._render_ess_dashboard('employee_self_service_portal.portal_ess_dashboard', **kwargs)

    # ---------------------------------------------------------------------------
    # IT Ticket routes (added from updated version)
    # ---------------------------------------------------------------------------

    @http.route('/my/ess/tickets/new', type='http', auth='user', website=True)
    def portal_ess_ticket_new(self, **kw):
        """Show create ticket form from ESS dashboard"""
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        # NEW - check both line_manager_id (custom) and parent_id (standard)
        # parent_id (Account Manager) takes priority — this is the actual approver
        line_manager = None
        if employee.parent_id and employee.parent_id.user_id:
            line_manager = employee.parent_id.user_id
        elif hasattr(employee, 'line_manager_id') and employee.line_manager_id:
            manager_emp = employee.line_manager_id
            if manager_emp.user_id:
                line_manager = manager_emp.user_id

        # ── NEW: pass categories (for grouped dropdown) ──
        ticket_categories = request.env['it.ticket.category'].sudo().search(
            [('active', '=', True)], order='sequence, name'
        )
        # All ticket types (sub-categories) — JS will filter by selected category
        ticket_types = request.env['it.ticket.type'].sudo().search(
            [], order='category_id, sequence, name'
        )

        values = {
            'employee': employee,
            'line_manager': line_manager,
            'page_name': 'ess_dashboard',
            'ticket_categories': ticket_categories,  # ← NEW
            'ticket_types': ticket_types,
            'error': kw.get('error'),
            'error_msg': kw.get('error_msg', ''),
        }
        return request.render('employee_self_service_portal.portal_ess_ticket_form', values)

    @http.route(['/my/tickets', '/my/tickets/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_tickets(self, page=1, sortby=None, filterby=None, **kw):
        """Display all IT tickets for the current portal user"""

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        # Base domain - tickets created by this employee
        domain = [('employee_id', '=', employee.id)]

        # Sorting options
        searchbar_sortings = {
            'date': {'label': 'Newest First', 'order': 'create_date desc'},
            'name': {'label': 'Ticket Number', 'order': 'name'},
            'state': {'label': 'Status', 'order': 'state'},
        }

        # Filter options
        searchbar_filters = {
            'all': {'label': 'All', 'domain': []},
            'pending': {'label': 'Pending Approval', 'domain': [('state', 'in', ['manager_approval', 'it_approval'])]},
            'active': {'label': 'Active', 'domain': [('state', 'in', ['assigned', 'in_progress'])]},
            'done': {'label': 'Completed', 'domain': [('state', '=', 'done')]},
            'rejected': {'label': 'Rejected', 'domain': [('state', '=', 'rejected')]},
        }

        # Default sort and filter
        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'

        order = searchbar_sortings[sortby]['order']
        domain += searchbar_filters[filterby]['domain']

        # Get tickets
        tickets = request.env['it.ticket'].sudo().search(domain, order=order)

        values = {
            'tickets': tickets,
            'page_name': 'tickets',
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
            'employee': employee,
        }

        return request.render('employee_self_service_portal.portal_my_tickets', values)

    @http.route(['/my/tickets/<int:ticket_id>'], type='http', auth='user', website=True)
    def portal_my_ticket_detail(self, ticket_id, **kw):
        """Display single ticket details"""

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        # Get ticket (only if it belongs to this employee)
        ticket = request.env['it.ticket'].sudo().search([
            ('id', '=', ticket_id),
            ('employee_id', '=', employee.id)
        ], limit=1)

        if not ticket:
            return request.redirect('/my/tickets')

        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'it.ticket'),
            ('res_id', '=', ticket.id)
        ])

        values = {
            'ticket': ticket,
            'page_name': 'tickets',
            'ticket_attachments': attachments,
            'employee': employee,
        }

        return request.render('employee_self_service_portal.portal_my_ticket_detail', values)

    @http.route('/my/ess/tickets/submit', type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def portal_ess_ticket_submit(self, **post):
        """Submit new IT ticket from ESS dashboard"""
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        if not post.get('subject') or not post.get('ticket_type_id') or not post.get('description'):
            return request.redirect('/my/ess/tickets/new?error=1&error_msg=Please+fill+all+required+fields')

        required_date = post.get('required_date')
        if required_date:
            required_date_obj = fields.Date.from_string(required_date)
            today_date = fields.Date.today()
            _logger.info("ESS required_date_obj: %s | today: %s", required_date_obj, today_date)
            if required_date_obj < today_date:
                _logger.warning("ESS: Past required_date attempted: %s", required_date_obj)
                return request.redirect(
                    '/my/ess/tickets/new?error=1&error_msg=Required+Date+cannot+be+in+the+past'
                )

        try:
            ticket_type_id = post.get('ticket_type_id')
            if ticket_type_id:
                ticket_type_id = int(ticket_type_id)

            resolved_line_manager_id = False
            if post.get('line_manager_id'):
                resolved_line_manager_id = int(post['line_manager_id'])
            elif employee.line_manager_id and employee.line_manager_id.user_id:
                resolved_line_manager_id = employee.line_manager_id.user_id.id

            ticket = request.env['it.ticket'].sudo().create({
                'employee_id': employee.id,
                'ticket_type_id': ticket_type_id,
                'priority': post.get('priority', '1'),
                'subject': post.get('subject'),
                'description': post.get('description'),
                'required_date': required_date or False,
                'submitted_date': fields.Datetime.now(),
                'line_manager_id': resolved_line_manager_id,
            })

            attachment = request.httprequest.files.get('attachment')
            if attachment and attachment.filename:
                attachment_content = attachment.read()
                request.env['ir.attachment'].sudo().create({
                    'name': attachment.filename,
                    'type': 'binary',
                    'datas': base64.b64encode(attachment_content),
                    'res_model': 'it.ticket',
                    'res_id': ticket.id,
                    'mimetype': attachment.mimetype,
                })
                _logger.info("Attachment %s added to Ticket %s", attachment.filename, ticket.name)

            _logger.info("IT Ticket %s created from ESS portal by %s", ticket.name, employee.name)

            # Message reflects the ticket's ACTUAL first-step state:
            # - workflow_level '0' -> state becomes 'assigned' at create time -> "IT Support" direct
            # - workflow_level '1'/'2'/'3' -> state always starts as 'manager_approval' -> "Line Manager"
            #   (IT Manager and HR are never the FIRST step in this workflow — they only get
            #    involved after Line Manager approves, so there's no separate branch for them here)
            routed_to = 'it_support' if ticket.state == 'assigned' else 'line_manager'
            return request.redirect('/my/ess?ticket_success=%s' % routed_to)

        except Exception as e:
            _logger.error("Error creating IT ticket from ESS portal: %s", e)
            request.env.cr.rollback()
            return request.redirect('/my/ess/tickets/new?error=1&error_msg=Failed+to+create+ticket.+Please+try+again.')

    # ---------------------------------------------------------------------------
    # End IT Ticket routes
    # ---------------------------------------------------------------------------

    # Leave route start

    def _ess_net_balance(self, employee, leave_type):
        Alloc = request.env['hr.leave.allocation'].sudo()
        Leave = request.env['hr.leave'].sudo()

        allocated = sum(Alloc.search([
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', leave_type.id),
            ('state', '=', 'validate'),
        ]).mapped('number_of_days'))

        committed = sum(Leave.search([
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', leave_type.id),
            ('state', 'not in', ['draft', 'refuse', 'cancel']),
        ]).mapped('number_of_days'))

        return allocated - committed

    def _get_leave_balances(self, employee):
        leave_types = request.env['hr.leave.type'].with_context(
            employee_id=employee.id
        ).sudo().search([('active', '=', True)])

        unlocked_frozen_type_ids = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('x_frozen_unlocked', '=', True),
            ('holiday_status_id.x_is_frozen', '=', True),
        ]).mapped('holiday_status_id').ids

        balances = []
        for idx, lt in enumerate(leave_types):
            max_days = lt.max_leaves
            used = lt.leaves_taken
            is_accrual = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
                ('allocation_type', '=', 'accrual'),
            ]) > 0

            if is_accrual:
                remaining = self._ess_net_balance(employee, lt)
            else:
                remaining = lt.virtual_remaining_leaves

            allows_negative = getattr(lt, 'allows_negative', False)

            has_allocation = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', lt.id),
                ('state', '=', 'validate'),
            ]) > 0

            if not (has_allocation or used > 0 or remaining != 0):
                continue

            balances.append({
                'id': lt.id,
                'name': lt.name,
                'max_days': max_days,
                'used': used,
                'remaining': remaining,
                'allows_negative': allows_negative,
                'color_slot': lt.color if lt.color else idx,
                'is_frozen': getattr(lt, 'x_is_frozen', False),
                'is_unlocked': lt.id in unlocked_frozen_type_ids,
            })
        return balances

    @http.route(
        ['/my/leaves', '/my/leaves/page/<int:page>'],
        type='http', auth='user', website=True
    )
    def portal_my_leaves(self, page=1, sortby=None, filterby=None, **kw):
        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        balances = self._get_leave_balances(employee)

        leave_types = request.env['hr.leave.type'].with_context(
            employee_id=employee.id
        ).sudo().search([('active', '=', True)])
        unlocked_frozen_type_ids = request.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('x_frozen_unlocked', '=', True),
            ('holiday_status_id.x_is_frozen', '=', True),
        ]).mapped('holiday_status_id').ids
        all_active_leaves = request.env['hr.leave'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'not in', ['refuse', 'cancel']),
        ])

        def _selectable(lt):
            if lt.max_leaves <= 0:
                return False
            if getattr(lt, 'x_is_frozen', False) and lt.id not in unlocked_frozen_type_ids:
                return False
            return True

        leave_types = leave_types.filtered(_selectable)

        searchbar_sortings = {
            'date': {'label': 'Newest First', 'order': 'date_from desc'},
            'state': {'label': 'Status', 'order': 'state'},
            'type': {'label': 'Leave Type', 'order': 'holiday_status_id'},
        }

        searchbar_filters = {
            'all': {
                'label': 'All',
                'domain': [],
            },
            'pending': {
                'label': 'Pending',
                'domain': [('state', 'in', ['draft', 'confirm', 'validate1'])],
            },
            'approved': {
                'label': 'Approved',
                'domain': [('state', '=', 'validate')],
            },
            'rejected': {
                'label': 'Rejected',
                'domain': [('state', '=', 'refuse')],
            },
            'cancelled': {
                'label': 'Cancelled',
                'domain': [('state', '=', 'cancel')],
            },
        }

        if not sortby:
            sortby = 'date'
        if not filterby:
            filterby = 'all'

        order = searchbar_sortings[sortby]['order']
        domain = [
                     ('employee_id', '=', employee.id),
                 ] + searchbar_filters[filterby]['domain']

        page = max(int(page or 1), 1)
        per_page = 5
        Leave = request.env['hr.leave'].sudo()
        total_count = Leave.search_count(domain)
        total_pages = (total_count + per_page - 1) // per_page
        if total_pages and page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        leave_requests = Leave.search(domain, order=order, limit=per_page, offset=offset)
        approval_required = employee.company_id.leave_approval_required

        line_manager = None
        if employee.line_manager_id and employee.line_manager_id.user_id:
            line_manager = employee.line_manager_id.user_id

        success_message = None
        error_message = kw.get('error_msg', '')

        if kw.get('success') == '1':
            success_message = 'Your leave request has been submitted successfully.'
        elif kw.get('success') == '2':
            success_message = 'Your leave request has been cancelled.'
        elif kw.get('success') == '3':
            success_message = 'Reminder sent successfully to your manager.'
        elif kw.get('success') == 'applied_approved':
            success_message = ('Leave application is successful, based on your '
                               'leave basket, it is approved.')
        require_doc_map = {
            str(lt.id): bool(getattr(lt, 'support_document', False))
            for lt in leave_types
        }
        require_doc_json = json.dumps(require_doc_map)
        request_unit_map = {
            str(lt.id): lt.request_unit
            for lt in leave_types
        }
        request_unit_json = json.dumps(request_unit_map)

        backup_employees = request.env['hr.employee'].sudo().search([
            ('id', '!=', employee.id),
            ('active', '=', True),
        ], order='name')

        holiday_recs = request.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', False),
        ])
        holiday_map = {}
        user_tz = pytz.timezone(request.env.user.tz or 'UTC')
        for h in holiday_recs:
            if not h.date_from:
                continue
            start = h.date_from
            end = h.date_to or h.date_from
            total_days = max(int(round((end - start).total_seconds() / 86400)), 1)
            for i in range(total_days):
                slice_mid = start + timedelta(days=i, hours=12)
                local_mid = pytz.utc.localize(slice_mid).astimezone(user_tz)
                holiday_map[local_mid.date().strftime('%Y-%m-%d')] = h.name or 'Public Holiday'
        holiday_json = json.dumps(holiday_map)

        values = {
            'employee': employee,
            'line_manager': line_manager,
            'balances': balances,
            'leave_types': leave_types,
            'leave_requests': leave_requests,
            'require_doc_json': require_doc_json,
            'request_unit_json': request_unit_json,
            'page_name': 'my_leaves',
            'page': page,
            'total_pages': total_pages,
            'total_count': total_count,
            'holiday_json': holiday_json,
            'backup_employees': backup_employees,
            'approval_required': approval_required,
            'all_active_leaves': all_active_leaves,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'sortby': sortby,
            'filterby': filterby,
            'success_message': success_message,
            'error': kw.get('error'),
            'error_message': error_message,
        }
        return request.render(
            'employee_self_service_portal.portal_my_leaves', values
        )

    def _friendly_leave_error(self, raw):
        raw_l = (raw or '').lower()
        if 'no valid allocation' in raw_l:
            return ("You don't have enough leave balance for this request. "
                    "Please check your available days or contact HR.")
        if 'overlap' in raw_l or 'already' in raw_l:
            return ("This request overlaps with an existing leave. "
                    "Please choose different dates.")
        if 'duration' in raw_l:
            return "The selected dates don't include any valid working days."
        return raw

    def _friendly_cancel_error(self, raw):
        raw_l = (raw or '').lower()
        if 'past' in raw_l or 'in the past' in raw_l:
            return ("You can't cancel a leave request whose dates are in the past. "
                    "Please contact HR if something needs to be corrected.")
        if 'delete' in raw_l or 'unlink' in raw_l:
            return ("This leave request can't be cancelled directly. "
                    "Please contact HR for help.")
        return "Couldn't cancel this leave request. Please try again or contact HR."

    def _ess_leave_balance_for(self, employee, leave_type):
        is_accrual = request.env['hr.leave.allocation'].sudo().search_count([
            ('employee_id', '=', employee.id),
            ('holiday_status_id', '=', leave_type.id),
            ('state', '=', 'validate'),
            ('allocation_type', '=', 'accrual'),
        ]) > 0
        if is_accrual:
            return self._ess_net_balance(employee, leave_type)
        return leave_type.with_context(
            employee_id=employee.id
        ).sudo().virtual_remaining_leaves

    def _ess_leave_notify_recipients(self, employee):
        company = request.env.company.sudo()
        emp = employee.sudo()
        candidates = [
            emp.work_email,
            company.leave_hr_department_email,
            emp.line_manager_id.work_email if emp.line_manager_id else None,
            emp.parent_id.work_email if emp.parent_id else None,
            company.leave_hr_manager_id.work_email if company.leave_hr_manager_id else None,
            company.leave_delivery_head_id.work_email if company.leave_delivery_head_id else None,
        ]
        seen, result = set(), []
        for email in candidates:
            e = (email or '').strip()
            if e and e.lower() not in seen:
                seen.add(e.lower())
                result.append(e)
        return result

    @http.route(
        '/my/leaves/submit',
        type='http', auth='user', website=True, methods=['POST'], csrf=True
    )
    def portal_leave_submit(self, **post):
        # TEMPORARILY DISABLED — leave application paused, per Odoo team issue.
        # Remove this early return to re-enable.
        return request.redirect(
            '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                "Applying for leave is temporarily unavailable. Please contact HR "
                "directly for any leave requests during this period."
            )
        )

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        leave_type_id = post.get('leave_type_id')
        date_from_str = post.get('date_from')
        date_to_str = post.get('date_to')
        reason = post.get('reason', '').strip()
        is_half_day = post.get('is_half_day') == '1'
        from_period = post.get('request_date_from_period') or 'am'
        to_period = post.get('request_date_to_period') or 'pm'

        if not leave_type_id or not date_from_str or not date_to_str:
            return request.redirect(
                '/my/leaves?error=1&error_msg=Please+fill+all+required+fields'
            )

        try:
            date_from_obj = fields.Date.from_string(date_from_str)
            date_to_obj = fields.Date.from_string(date_to_str)

            if date_to_obj < date_from_obj:
                return request.redirect(
                    '/my/leaves?error=1&error_msg=End+date+cannot+be+before+start+date'
                )

            overlapping = request.env['hr.leave'].sudo().search([
                ('employee_id', '=', employee.id),
                ('state', 'not in', ['refuse', 'draft', 'cancel']),
                ('date_from', '<=', fields.Datetime.from_string(str(date_to_obj) + ' 23:59:59')),
                ('date_to', '>=', fields.Datetime.from_string(str(date_from_obj) + ' 00:00:00')),
            ], limit=1)

            if overlapping:
                overlap_from = overlapping.date_from.strftime('%d %b %Y') if overlapping.date_from else ''
                overlap_to = overlapping.date_to.strftime('%d %b %Y') if overlapping.date_to else ''
                msg = f'You+already+have+a+leave+request+from+{overlap_from}+to+{overlap_to}.+Overlapping+dates+are+not+allowed.'
                return request.redirect(f'/my/leaves?error=1&error_msg={msg.replace(" ", "+")}')

        except Exception as e:
            _logger.error("ESS Leave Submit: date parse error: %s", e)
            return request.redirect(
                '/my/leaves?error=1&error_msg=Invalid+date+format'
            )

        try:
            leave_type_id_int = int(leave_type_id)
            leave_type = request.env['hr.leave.type'].sudo().browse(leave_type_id_int)
            if not leave_type.exists():
                return request.redirect(
                    '/my/leaves?error=1&error_msg=Invalid+leave+type+selected'
                )
        except Exception as e:
            _logger.error("ESS Leave Submit: leave type lookup failed: %s", e)
            return request.redirect(
                '/my/leaves?error=1&error_msg=Invalid+leave+type'
            )

        attachment = request.httprequest.files.get('leave_attachment')
        has_file = bool(attachment and attachment.filename)
        requires_doc = getattr(leave_type, 'support_document', False)
        if requires_doc and not has_file:
            return request.redirect(
                '/my/leaves?error=1&error_msg=A+supporting+document+is+required+for+this+leave+type.'
            )

        if attachment and attachment.filename:
            allowed_exts = ('.pdf', '.doc', '.docx', '.png', '.jpg', '.jpeg', '.xlsx', '.txt')
            fname_lower = attachment.filename.lower()
            if not fname_lower.endswith(allowed_exts):
                return request.redirect(
                    '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                        "Invalid file type. Allowed: PDF, DOC, DOCX, PNG, JPG, JPEG, XLSX, TXT."
                    )
                )
            attachment.seek(0, 2)
            file_size = attachment.tell()
            attachment.seek(0)
            if file_size > 10 * 1024 * 1024:
                return request.redirect(
                    '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                        "File is too large. Maximum allowed size is 10MB."
                    )
                )

        if getattr(leave_type, 'x_is_frozen', False):
            unlocked = request.env['hr.leave.allocation'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('holiday_status_id', '=', leave_type.id),
                ('state', '=', 'validate'),
                ('x_frozen_unlocked', '=', True),
            ])
            if not unlocked:
                return request.redirect(
                    '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                        "This leave type is currently locked. Please contact HR to request access."
                    )
                )

        try:
            requested_days = self._ess_count_workdays(date_from_obj, date_to_obj)
            if is_half_day and requested_days == 1:
                requested_days = 0.5
            current_balance = self._ess_leave_balance_for(employee, leave_type)
            allowed_excess = leave_type.max_allowed_negative if leave_type.allows_negative else 0
            if current_balance - requested_days < -allowed_excess:
                return request.redirect(
                    '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                        "You do not have enough leave balance for this request. "
                        "Please reach out to HR for support."
                    )
                )

        except Exception as bal_err:
            _logger.error("ESS Leave Submit: balance check failed: %s", bal_err)
            return request.redirect(
                '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                    "Could not verify your leave balance. Please reach out to HR for support."
                )
            )

        backup_type = (post.get('backup_type') or '').strip()
        backup_employee_id = post.get('backup_employee_id')
        backup_name = (post.get('backup_name') or '').strip()
        backup_email = (post.get('backup_email') or '').strip()

        backup_required = date_to_obj > fields.Date.today()

        if backup_required:
            if backup_type == 'internal':
                if not backup_employee_id:
                    return request.redirect(
                        '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                            "Please select a backup person for this future-dated leave."
                        )
                    )
            elif backup_type == 'external':
                if not backup_name or not backup_email:
                    return request.redirect(
                        '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                            "Please provide both the name and email of your external backup."
                        )
                    )
                if not re.match(r"^[A-Za-z .'\-]{2,100}$", backup_name.strip()):
                    return request.redirect(
                        '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                            "Backup person name can only contain letters, spaces, "
                            "hyphens, apostrophes, and periods (2-100 characters)."
                        )
                    )
                if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", backup_email.strip()):
                    return request.redirect(
                        '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                            "Please enter a valid email address for the external backup."
                        )
                    )
            else:
                return request.redirect(
                    '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                        "Please nominate a backup person for this future-dated leave."
                    )
                )

        try:
            leave_vals = {
                'employee_id': employee.id,
                'holiday_status_id': leave_type_id_int,
                'request_date_from': date_from_obj,
                'request_date_to': date_to_obj,
                'name': reason or '/',
            }
            if leave_type.request_unit == 'half_day':
                leave_vals['request_date_from_period'] = from_period
                leave_vals['request_date_to_period'] = to_period
            leave = request.env['hr.leave'].sudo().create(leave_vals)

            if backup_required and backup_type:
                backup_vals = {'x_backup_type': backup_type}
                if backup_type == 'internal' and backup_employee_id:
                    backup_vals['x_backup_employee_id'] = int(backup_employee_id)
                elif backup_type == 'external':
                    backup_vals['x_backup_name'] = backup_name
                    backup_vals['x_backup_email'] = backup_email
                leave.sudo().write(backup_vals)

            try:
                attachment = request.httprequest.files.get('leave_attachment')
                if attachment and attachment.filename:
                    attachment.seek(0)
                    attachment_content = attachment.read()
                    if len(attachment_content) > 10 * 1024 * 1024:
                        _logger.warning(
                            "ESS Leave: attachment too large for leave %s, skipping",
                            leave.id
                        )
                    else:
                        request.env['ir.attachment'].sudo().create({
                            'name': attachment.filename,
                            'type': 'binary',
                            'datas': base64.b64encode(attachment_content),
                            'res_model': 'hr.leave',
                            'res_id': leave.id,
                            'mimetype': attachment.mimetype,
                        })
            except Exception as att_err:
                _logger.error(
                    "ESS Leave: attachment upload failed for leave %s: %s",
                    leave.id, att_err
                )



            if not approval_required:
                try:
                    leave_company = employee.company_id
                    leave.sudo().with_company(leave_company).with_context(
                        allowed_company_ids=[leave_company.id],
                        _ess_approved_sent=True,
                        _ess_negative_hr_sent=True,
                    ).action_approve()
                except Exception as appr_err:
                    import traceback
                    _logger.error(
                        "ESS Leave: auto-approve failed for leave %s: %s",
                        leave.id, appr_err
                    )
                    request.env.cr.rollback()
                    return request.redirect(
                        '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                            "Could not process your leave. Please reach out to HR for support."
                        )
                    )

            try:
                recipients = self._ess_leave_notify_recipients(employee)
                if recipients:
                    template = request.env.ref(
                        'employee_self_service_portal.email_template_leave_applied_notification',
                        raise_if_not_found=False
                    )
                    if template:
                        base_url = request.env['ir.config_parameter'].sudo() \
                            .get_param('web.base.url')
                        template.with_context(base_url=base_url).sudo().send_mail(
                            leave.id, force_send=True,
                            email_values={'email_to': ','.join(recipients)}
                        )
                        _logger.info(
                            "ESS Leave: applied notification sent for leave %s to %s",
                            leave.id, recipients
                        )
                    else:
                        _logger.warning(
                            "ESS Leave: applied template missing for leave %s", leave.id
                        )
            except Exception as mail_err:
                _logger.error(
                    "ESS Leave: applied notification failed for leave %s: %s",
                    leave.id, mail_err
                )

            try:
                if (leave.x_backup_type == 'internal'
                        and leave.x_backup_employee_id
                        and leave.x_backup_employee_id.work_email):
                    bk_template = request.env.ref(
                        'employee_self_service_portal.email_template_leave_backup_notification',
                        raise_if_not_found=False
                    )
                    if bk_template:
                        base_url = request.env['ir.config_parameter'].sudo() \
                            .get_param('web.base.url')
                        bk_template.with_context(base_url=base_url).sudo().send_mail(
                            leave.id, force_send=True,
                            email_values={'email_to': leave.x_backup_employee_id.work_email}
                        )
                        _logger.info(
                            "ESS Leave: backup notification sent for leave %s to %s",
                            leave.id, leave.x_backup_employee_id.work_email
                        )
            except Exception as bk_err:
                _logger.error(
                    "ESS Leave: backup notification failed for leave %s: %s",
                    leave.id, bk_err
                )

            if not approval_required:
                return request.redirect('/my/leaves?success=applied_approved')
            return request.redirect('/my/leaves?success=1')

        except ValidationError as ve:
            request.env.cr.rollback()
            raw_msg = ve.args[0] if ve.args else str(ve)
            friendly = self._friendly_leave_error(raw_msg)
            return request.redirect(
                '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(friendly)
            )
        except Exception as e:
            import traceback
            _logger.error(
                "ESS Leave Submit: create failed for employee %s: %s",
                employee.name, e
            )
            _logger.error(traceback.format_exc())
            request.env.cr.rollback()
            return request.redirect(
                '/my/leaves?error=1&error_msg=Failed+to+submit+leave.+Please+try+again.'
            )

    def _ess_count_workdays(self, date_from, date_to):
        if not date_from or not date_to or date_to < date_from:
            return 0
        days = 0
        cur = date_from
        while cur <= date_to:
            if cur.weekday() < 5:
                days += 1
            cur += timedelta(days=1)
        return days

    @http.route(
        '/my/leaves/<int:leave_id>',
        type='http', auth='user', website=True
    )
    def portal_leave_detail(self, leave_id, **kw):

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')

        leave = request.env['hr.leave'].sudo().search([
            ('id', '=', leave_id),
            ('employee_id', '=', employee.id),
        ], limit=1)

        if not leave:
            return request.redirect('/my/leaves')

        state_map = {
            'draft': ('Draft', 'secondary'),
            'confirm': ('Pending Approval', 'warning'),
            'validate1': ('Pending Approval', 'warning'),
            'validate': ('Approved', 'success'),
            'refuse': ('Rejected', 'danger'),
        }
        state_label, state_badge = state_map.get(
            leave.state, ('Unknown', 'secondary')
        )

        attachments = request.env['ir.attachment'].sudo().search([
            ('res_model', '=', 'hr.leave'),
            ('res_id', '=', leave.id),
        ])
        for att in attachments:
            if not att.access_token:
                att.generate_access_token()
        attachments.invalidate_recordset(['access_token'])

        line_manager = None
        if employee.line_manager_id and employee.line_manager_id.user_id:
            line_manager = employee.line_manager_id.user_id

        can_cancel = bool(
            leave.state in ('draft', 'confirm', 'validate1', 'validate')
            and leave.request_date_from
            and leave.request_date_from > fields.Date.today()
        )

        values = {
            'leave': leave,
            'employee': employee,
            'line_manager': line_manager,
            'state_label': state_label,
            'state_badge': state_badge,
            'attachments': attachments,
            'can_cancel': can_cancel,
            'page_name': 'my_leaves',
            'error': kw.get('error'),
            'error_message': kw.get('error_msg', ''),
            'refuse_reason': getattr(leave, 'reason_refusal', None) or getattr(leave, 'refuse_reason', None) or '',
        }
        return request.render(
            'employee_self_service_portal.portal_leave_detail', values
        )

    @http.route(
        '/my/leaves/<int:leave_id>/cancel',
        type='http', auth='user', website=True, methods=['POST'], csrf=True
    )
    def portal_leave_cancel(self, leave_id, **kw):
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        # Remove this early return to re-enable.
        return request.redirect(
            '/my/leaves/%d?error=1&error_msg=%s' % (
                leave_id,
                urllib.parse.quote_plus("This action is temporarily unavailable. Please contact HR directly.")
            )
        )

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')


        if leave.state in ('cancel', 'refuse'):
            return request.redirect(
                '/my/leaves/%d?error=1&error_msg=%s' % (
                    leave_id,
                    urllib.parse.quote_plus("This leave is already cancelled.")
                )
            )

        start_date = leave.request_date_from or (leave.date_from.date() if leave.date_from else None)
        if not start_date or start_date <= fields.Date.today():
            return request.redirect(
                '/my/leaves/%d?error=1&error_msg=%s' % (
                    leave_id,
                    urllib.parse.quote_plus(
                        "This leave can no longer be cancelled because it has "
                        "already started or is in the past. Please contact HR."
                    )
                )
            )

        try:
            leave.sudo().with_context(_ess_selfcancel=True)._action_user_cancel(
                'Cancelled by employee via portal'
            )
            try:
                hr_email = request.env.company.leave_hr_department_email
                emp_email = employee.work_email
                recipients = []
                for e in (hr_email, emp_email):
                    e = (e or '').strip()
                    if e and e not in recipients:
                        recipients.append(e)
                if recipients:
                    tmpl = request.env.ref(
                        'employee_self_service_portal.email_template_leave_cancelled_self',
                        raise_if_not_found=False
                    )
                    if tmpl:
                        base_url = request.env['ir.config_parameter'].sudo() \
                            .get_param('web.base.url')
                        tmpl.with_context(base_url=base_url).sudo().send_mail(
                            leave.id, force_send=True,
                            email_values={'email_to': ','.join(recipients)}
                        )
                        _logger.info(
                            "ESS Cancel: self-cancel email sent for leave %s to %s",
                            leave.id, recipients
                        )
            except Exception as mail_err:
                _logger.error(
                    "ESS Cancel: self-cancel email failed for leave %s: %s",
                    leave.id, mail_err
                )

            return request.redirect('/my/leaves?success=2')

        except Exception as e:
            import traceback
            _logger.error("ESS Cancel: failed for leave %s: %s", leave_id, e)
            _logger.error(traceback.format_exc())
            request.env.cr.rollback()
            friendly = self._friendly_cancel_error(str(e))
            return request.redirect(
                '/my/leaves/%d?error=1&error_msg=%s'
                % (leave_id, urllib.parse.quote_plus(friendly))
            )

    @http.route(
        '/my/leaves/<int:leave_id>/remind',
        type='http', auth='user', website=True, methods=['POST'], csrf=True
    )
    def portal_leave_remind(self, leave_id, **kw):
        # TEMPORARILY DISABLED — writes paused, per Odoo team issue.
        # Remove this early return to re-enable.
        return request.redirect(
            '/my/leaves?error=1&error_msg=' + urllib.parse.quote_plus(
                "This action is temporarily unavailable. Please contact HR directly."
            )
        )

        employee = self._get_employee()
        if not employee:
            return request.redirect('/my/ess')


        if leave.state not in ('confirm', 'validate1'):
            return request.redirect(
                '/my/leaves?error=1&error_msg=Reminder+can+only+be+sent+for+pending+leaves'
            )

        try:
            template = request.env.ref(
                'employee_self_service_portal.email_template_leave_reminder',
                raise_if_not_found=False
            )

            manager_email = (
                employee.line_manager_id.work_email
                if employee.line_manager_id else False
            )

            if template and manager_email:
                template.sudo().send_mail(
                    leave.id, force_send=True,
                    email_values={'email_to': manager_email}
                )
                _logger.info(
                    "ESS Reminder: sent (to=%s) for leave %s",
                    manager_email, leave.id
                )
            else:
                _logger.warning(
                    "ESS Reminder: no manager to notify for leave %s", leave.id
                )

            return request.redirect('/my/leaves?success=3#leave-requests-section')

        except Exception as e:
            _logger.error("ESS Portal: reminder failed for leave %s: %s", leave.id, e)
            return request.redirect(
                '/my/leaves?error=1&error_msg=Failed+to+send+reminder.+Please+try+again.'
            )

    def _is_line_manager(self):
        count = request.env['hr.employee'].sudo().search_count([
            ('line_manager_id.user_id', '=', request.env.user.id),
        ])
        return count > 0

    def _manager_pending_leaves(self):
        return request.env['hr.leave'].sudo().search([
            ('employee_id.line_manager_id.user_id', '=', request.env.user.id),
            ('state', 'in', ['confirm', 'validate1']),
        ], order='create_date desc')

    def _manager_processed_leaves(self, limit=50):
        return request.env['hr.leave'].sudo().search([
            ('employee_id.line_manager_id.user_id', '=', request.env.user.id),
            ('state', 'in', ['validate', 'refuse']),
        ], order='write_date desc', limit=limit)

    @http.route(['/my/approvals'], type='http', auth='user', website=True)
    def portal_my_approvals(self, filterby=None, **kw):
        if not self._is_line_manager():
            return request.redirect('/my/ess')

        searchbar_filters = {
            'pending': {'label': 'Pending', 'domain': [('state', '=', 'confirm')]},

            'approved': {'label': 'Approved', 'domain': [('state', 'in', ['validate1', 'validate'])]},
            'rejected': {
                'label': 'Rejected',
                'domain': [('state', '=', 'refuse')],
            },

        }

        if not filterby:
            filterby = 'pending'

        domain = [
                     ('employee_id.line_manager_id.user_id', '=', request.env.user.id),
                 ] + searchbar_filters[filterby]['domain']

        leaves = request.env['hr.leave'].sudo().search(domain, order='write_date desc')

        success_message = None
        if kw.get('success') == 'approved':
            success_message = 'Leave request approved.'
        elif kw.get('success') == 'rejected':
            success_message = 'Leave request rejected.'

        values = {
            'leaves': leaves,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'page_name': 'my_approvals',
            'success_message': success_message,
            'error': kw.get('error'),
            'error_message': kw.get('error_msg', ''),
        }
        return request.render(
            'employee_self_service_portal.portal_my_approvals', values
        )

    def _get_approvable_leave(self, leave_id):
        leave = request.env['hr.leave'].sudo().browse(int(leave_id))
        if not leave.exists():
            return False
        mgr_user = leave.employee_id.line_manager_id.user_id
        if not mgr_user or mgr_user.id != request.env.user.id:
            return False
        return leave

    @http.route(['/my/approvals/<int:leave_id>/approve'],
                type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_approval_approve(self, leave_id, **kw):
        if not self._is_line_manager():
            return request.redirect('/my/ess')

        leave = self._get_approvable_leave(leave_id)
        if not leave:
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "You are not authorised to act on this request."
                )
            )
        if leave.state not in ('confirm', 'validate1'):
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "This request is no longer pending."
                )
            )

        manager_emp = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)
        manager_name = manager_emp.name or request.env.user.name

        try:
            leave_company = leave.employee_id.company_id
            leave.with_company(leave_company).with_context(
                allowed_company_ids=[leave_company.id]
            ).action_approve()
            leave.message_post(
                body="Approved via portal by line manager: %s" % manager_name,
                subtype_xmlid='mail.mt_note',
            )
            _logger.info("ESS Portal Approval: leave %s approved by user %s",
                         leave.id, request.env.user.id)
            return request.redirect('/my/approvals?success=approved')
        except Exception as e:
            _logger.error("ESS Portal Approval: approve failed for leave %s: %s",
                          leave.id, e)
            request.env.cr.rollback()
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "Could not approve this request. Please try again or contact HR."
                )
            )

    @http.route(['/my/approvals/<int:leave_id>/reject'],
                type='http', auth='user', website=True,
                methods=['POST'], csrf=True)
    def portal_approval_reject(self, leave_id, **kw):
        if not self._is_line_manager():
            return request.redirect('/my/ess')

        leave = self._get_approvable_leave(leave_id)
        if not leave:
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "You are not authorised to act on this request."
                )
            )
        if leave.state not in ('confirm', 'validate1'):
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "This request is no longer pending."
                )
            )

        reason = (kw.get('reject_reason') or '').strip()
        manager_emp = request.env['hr.employee'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1)
        manager_name = manager_emp.name or request.env.user.name

        try:
            leave.action_refuse()
            note = "Rejected via portal by line manager: %s" % manager_name
            if reason:
                note += "<br/>Reason: %s" % reason
            leave.message_post(body=note, subtype_xmlid='mail.mt_note', )

            _logger.info("ESS Portal Approval: leave %s rejected by user %s",
                         leave.id, request.env.user.id)
            return request.redirect('/my/approvals?success=rejected')
        except Exception as e:
            _logger.error("ESS Portal Approval: reject failed for leave %s: %s",
                          leave.id, e)
            request.env.cr.rollback()
            return request.redirect(
                '/my/approvals?error=1&error_msg=' + urllib.parse.quote_plus(
                    "Could not reject this request. Please try again or contact HR."
                )
            )

    # End of leave route

    @http.route('/my/ess/enhanced', type='http', auth='user', website=True)
    def portal_ess_dashboard_enhanced(self, **kwargs):
        # Maintain this route for backward compatibility
        return self._render_ess_dashboard('employee_self_service_portal.portal_ess_dashboard_enhanced', **kwargs)

    def _render_ess_dashboard(self, template_name, **kwargs):
        """Common method to render dashboard with enhanced data"""
        import pytz

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)

        # Get dashboard statistics
        dashboard_data = {}

        if employee:
            # Enhanced dashboard data with more detailed analytics
            dashboard_data = self._get_enhanced_dashboard_data(employee)

            # Add feature access permissions
            dashboard_data.update({
                'has_attendance_access': has_feature_access('attendance'),
                # 'has_crm_access': has_feature_access('crm'),
                'has_expenses_access': has_feature_access('expenses'),
                'has_payslip_access': has_feature_access('payslip')
            })

        # Add view type for enhanced template
        dashboard_data['view_type'] = 'enhanced' if 'enhanced' in template_name else 'standard'

        # Add timezone-aware formatting functions
        user_timezone = get_user_timezone()
        dashboard_data.update({
            'user_timezone': user_timezone,
            'format_datetime': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%I:%M %p') if dt else '',
            'format_date': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%d/%m/%Y') if dt else '',
            'format_day': lambda dt: fields.Datetime.context_timestamp(request.env.user, dt).strftime(
                '%A') if dt else '',
        })

        return request.render(template_name, dashboard_data)

    def _get_enhanced_dashboard_data(self, employee):
        """Get comprehensive dashboard data for enhanced view"""
        from datetime import date, datetime, timedelta

        # Basic employee data
        dashboard_data = {'employee': employee}

        # Payslips data with enhanced analytics
        payslips = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id), ('state', 'in', ['paid'])
        ])
        payslips_count = len(payslips)

        # Latest payslip
        latest_payslip = request.env['hr.payslip'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['paid'])
        ], order='date_from desc', limit=1)

        # Enhanced attendance data - get ALL attendance records for today using user's timezone
        import pytz

        # Get user's timezone
        user_timezone = get_user_timezone()
        user_pytz = pytz.timezone(user_timezone)

        # Get current time in user's timezone
        utc_now = datetime.now(pytz.UTC)
        local_now = utc_now.astimezone(user_pytz)
        today_local = local_now.date()

        # Calculate today start and end in user's local timezone, then convert to UTC for database query
        local_day_start = datetime.combine(today_local, datetime.min.time()).replace(tzinfo=user_pytz)
        local_day_end = datetime.combine(today_local, datetime.max.time()).replace(tzinfo=user_pytz)

        # Convert to UTC for database query
        utc_day_start = local_day_start.astimezone(pytz.UTC)
        utc_day_end = local_day_end.astimezone(pytz.UTC)

        today_attendances = request.env[HR_ATTENDANCE_MODEL].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', utc_day_start),
            ('check_in', '<=', utc_day_end)
        ])

        # Weekly attendance summary in user's timezone
        week_start_local = today_local - timedelta(days=today_local.weekday())
        week_end_local = week_start_local + timedelta(days=6)

        # Convert to datetime with timezone
        week_start_dt = datetime.combine(week_start_local, datetime.min.time()).replace(tzinfo=user_pytz)
        week_end_dt = datetime.combine(week_end_local, datetime.max.time()).replace(tzinfo=user_pytz)

        # Convert to UTC for database query
        utc_week_start = week_start_dt.astimezone(pytz.UTC)
        utc_week_end = week_end_dt.astimezone(pytz.UTC)

        week_attendance = request.env[HR_ATTENDANCE_MODEL].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', utc_week_start),
            ('check_in', '<=', utc_week_end)
        ])

        # Calculate weekly hours using the day grouping approach for consistency
        from collections import defaultdict
        week_attendance_by_day = defaultdict(list)
        for att in week_attendance:
            day_key = att.check_in.strftime('%Y-%m-%d')
            week_attendance_by_day[day_key].append(att)

        # Calculate total hours per day and then sum them up
        weekly_hours = 0
        for day, day_attendances in week_attendance_by_day.items():
            day_hours = sum(att.worked_hours for att in day_attendances if att.worked_hours)
            weekly_hours += day_hours

        # Enhanced CRM data
        # user = request.env.user
        # crm_leads = request.env[CRM_LEAD_MODEL].sudo().search([('user_id', '=', user.id)])
        # crm_leads_count = len(crm_leads)
        #
        # # CRM analytics
        # new_leads = crm_leads.filtered(lambda l: l.stage_id.name in ['New', 'Qualification'] if l.stage_id else False)
        # won_leads = crm_leads.filtered(lambda l: l.stage_id.name == 'Won' if l.stage_id else False)
        # total_revenue = sum(crm_leads.mapped('expected_revenue'))

        # Enhanced Expense statistics
        today_dt = datetime.now().date()
        first_day_month = today_dt.replace(day=1)

        current_month_expenses = request.env['hr.expense'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '>=', first_day_month),
            ('date', '<=', today_dt)
        ])

        # Year-to-date expenses
        year_start = today_dt.replace(month=1, day=1)
        ytd_expenses = request.env['hr.expense'].sudo().search([
            ('employee_id', '=', employee.id),
            ('date', '>=', year_start),
            ('date', '<=', today_dt)
        ])

        expenses_count = len(current_month_expenses)
        current_month_total = sum(current_month_expenses.mapped('total_amount'))
        ytd_total = sum(ytd_expenses.mapped('total_amount'))

        # Expense breakdown by status
        submitted_expenses = current_month_expenses.filtered(lambda x: x.sheet_id and x.sheet_id.state == 'submit')
        approved_expenses = current_month_expenses.filtered(lambda x: x.sheet_id and x.sheet_id.state == 'approve')
        draft_expenses = current_month_expenses.filtered(lambda x: not x.sheet_id or x.sheet_id.state == 'draft')

        expense_stats = {
            'total_count': expenses_count,
            'total_amount': current_month_total,
            'ytd_total': ytd_total,
            'submitted_count': len(submitted_expenses),
            'submitted_amount': sum(submitted_expenses.mapped('total_amount')),
            'approved_count': len(approved_expenses),
            'approved_amount': sum(approved_expenses.mapped('total_amount')),
            'draft_count': len(draft_expenses),
            'draft_amount': sum(draft_expenses.mapped('total_amount')),
            'pending_count': len(submitted_expenses),
        }

        # Recent activities (for enhanced dashboard)
        recent_activities = []

        # Add recent attendance - show the most recent attendance for the activity feed
        if today_attendances:
            # Get most recent attendance record
            most_recent = today_attendances[0] if len(today_attendances) > 0 else None

            if most_recent:
                recent_activities.append({
                    'type': 'attendance',
                    'title': 'Checked In' if not most_recent.check_out else 'Completed Work Day',
                    'description': f"At {most_recent.check_in.strftime('%I:%M %p')}" if not most_recent.check_out else f"Worked {most_recent.worked_hours:.2f} hours",
                    'time': most_recent.check_in,
                    'icon': 'clock-o',
                    'color': 'primary'
                })

        # Add recent CRM activities
        # if crm_leads_count > 0:
        #     recent_activities.append({
        #         'type': 'crm',
        #         'title': 'CRM Active',
        #         'description': f"{crm_leads_count} leads to manage",
        #         'time': datetime.now(),
        #         'icon': 'briefcase',
        #         'color': 'info'
        #     })

        # Add recent expenses
        if current_month_expenses:
            recent_activities.append({
                'type': 'expense',
                'title': 'Expense Updates',
                'description': f"{len(current_month_expenses)} expenses this month",
                'time': datetime.now(),
                'icon': 'money',
                'color': 'warning'
            })

        # Sort activities by time
        recent_activities.sort(key=lambda x: x['time'], reverse=True)

        # Performance metrics (for enhanced dashboard)
        performance_metrics = {
            'attendance_rate': self._calculate_attendance_rate(employee, today_local),
            # 'crm_conversion_rate': (len(won_leads) / crm_leads_count * 100) if crm_leads_count > 0 else 0,
            'expense_avg_amount': current_month_total / expenses_count if expenses_count > 0 else 0,
            'weekly_hours': weekly_hours,
            'monthly_targets': self._get_monthly_targets(employee),
        }

        # IT Tickets data for dashboard
        it_tickets_count = 0
        it_tickets_pending = 0
        it_tickets_recent = None
        try:
            it_tickets_count = request.env['it.ticket'].search_count([
                ('employee_id', '=', employee.id)
            ])
            it_tickets_pending = request.env['it.ticket'].search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'manager_approval', 'it_approval'])
            ])
            it_tickets_recent = request.env['it.ticket'].search([
                ('employee_id', '=', employee.id)
            ], order='create_date desc', limit=3)
        except Exception:
            pass


        leave_pending_count = 0
        leave_approved_count = 0
        leave_balance_days = 0
        try:
            leave_pending_count = request.env['hr.leave'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['confirm', 'validate1']),
            ])
            leave_approved_count = request.env['hr.leave'].sudo().search_count([
                ('employee_id', '=', employee.id),
                ('state', '=', 'validate'),
            ])
            balances = self._get_leave_balances(employee)
            leave_balance_days = round(sum(
                b['remaining'] for b in balances
                if 'annual' in b['name'].lower()
            ), 1)
        except Exception:
            pass

        approvals_pending_count = 0
        approvals_approved_count = 0
        approvals_rejected_count = 0
        try:
            if self._is_line_manager():
                base = [('employee_id.line_manager_id.user_id', '=', request.env.user.id)]
                approvals_pending_count = request.env['hr.leave'].sudo().search_count(
                    base + [('state', '=', 'confirm')]
                )
                approvals_approved_count = request.env['hr.leave'].sudo().search_count(
                    base + [('state', 'in', ['validate1', 'validate'])]
                )
                approvals_rejected_count = request.env['hr.leave'].sudo().search_count(
                    base + [('state', '=', 'refuse')]
                )
        except Exception:
            pass

        form16_count = 0
        latest_form16 = None
        if employee and employee.currency_id.name == 'INR':
            form16_records = request.env['hr.employee.form16'].sudo().search(
                [('employee_id', '=', employee.id)], order='financial_year desc'
            )
            form16_count = len(form16_records)
            latest_form16 = form16_records[0] if form16_records else None


        dashboard_data.update({
            'form16_count': form16_count,
            'latest_form16': latest_form16,
            'payslips_count': payslips_count,
            'latest_payslip': latest_payslip,
            'today_attendances': today_attendances,
            'weekly_hours': weekly_hours,
            # 'crm_leads_count': crm_leads_count,
            # 'crm_analytics': {
            #     'total_leads': crm_leads_count,
            #     'new_leads': len(new_leads),
            #     'won_leads': len(won_leads),
            #     'total_revenue': total_revenue,
            #     'conversion_rate': (len(won_leads) / crm_leads_count * 100) if crm_leads_count > 0 else 0
            # },
            'expenses_count': expenses_count,
            'expense_stats': expense_stats,
            'recent_activities': recent_activities[:5],  # Top 5 recent activities
            'performance_metrics': performance_metrics,
            'it_tickets_count': it_tickets_count,
            'it_tickets_pending': it_tickets_pending,
            'it_tickets_recent': it_tickets_recent,
            'leave_pending_count': leave_pending_count,
            'leave_approved_count': leave_approved_count,
            'leave_balance_days': leave_balance_days,
            'is_line_manager': self._is_line_manager(),
            'approvals_pending_count': approvals_pending_count,
            'approvals_approved_count': approvals_approved_count,
            'approvals_rejected_count': approvals_rejected_count,
        })

        return dashboard_data

    def _calculate_attendance_rate(self, employee, today_local):
        """Calculate monthly attendance rate using timezone-aware dates"""
        from datetime import datetime, timedelta
        import pytz

        # Get user's timezone
        user_timezone = get_user_timezone()
        user_pytz = pytz.timezone(user_timezone)

        # Get first day of current month in user's timezone
        first_day_local = today_local.replace(day=1)

        # Count working days (excluding weekends)
        working_days = 0
        current_date = first_day_local
        while current_date <= today_local:
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                working_days += 1
            current_date += timedelta(days=1)

        # Convert dates to datetime with timezone
        first_day_dt = datetime.combine(first_day_local, datetime.min.time()).replace(tzinfo=user_pytz)
        today_dt = datetime.combine(today_local, datetime.max.time()).replace(tzinfo=user_pytz)

        # Convert to UTC for database query
        utc_first_day = first_day_dt.astimezone(pytz.UTC)
        utc_today = today_dt.astimezone(pytz.UTC)

        # Count actual attendance days
        attendance_records = request.env[HR_ATTENDANCE_MODEL].sudo().search([
            ('employee_id', '=', employee.id),
            ('check_in', '>=', utc_first_day),
            ('check_in', '<=', utc_today)
        ])

        # Get unique days using user's timezone for accurate day counting
        attended_days = set()
        for att in attendance_records:
            # Convert each check-in time to user's timezone to get the local date
            local_date = fields.Datetime.context_timestamp(request.env.user, att.check_in).date()
            attended_days.add(local_date)

        return (len(attended_days) / working_days * 100) if working_days > 0 else 0

    def _get_monthly_targets(self, employee):
        """Get monthly targets for the employee (placeholder)"""
        return {
            'attendance_target': 95,  # 95% attendance rate
            'crm_leads_target': 10,  # 10 leads per month
            'expense_budget': 2000,  # $2000 monthly expense budget
        }

    def _get_notification(self, latest_request):
        """Return notification dict based on latest HR change request state."""
        if not latest_request:
            return None

        if latest_request.state == 'approved':
            reviewed_by = latest_request.reviewed_by.name or 'HR'
            review_date = (
                latest_request.review_date.strftime('%d %b %Y')
                if latest_request.review_date else ''
            )
            return {
                'type': 'success',
                'title': 'Profile Update Approved',
                'message': (
                    f'Your profile change request {latest_request.name} '
                    f'was approved by {reviewed_by}'
                    f'{" on " + review_date if review_date else ""}. '
                    f'Your records have been updated.'
                ),
                'reason': None,
                'request_name': latest_request.name,
                'reviewed_by': reviewed_by,
            }

        elif latest_request.state == 'rejected':
            reviewed_by = latest_request.reviewed_by.name or 'HR'
            return {
                'type': 'danger',
                'title': 'Profile Update Rejected',
                'message': (
                    f'Your profile change request {latest_request.name} '
                    f'was rejected by {reviewed_by}. '
                    f'Please correct and resubmit.'
                ),
                'reason': latest_request.rejection_reason or 'No reason provided.',
                'request_name': latest_request.name,
                'reviewed_by': reviewed_by,
            }

        elif latest_request.state == 'pending':
            return {
                'type': 'warning',
                'title': 'Profile Update Pending',
                'message': (
                    f'Your profile change request {latest_request.name} '
                    f'is awaiting HR review.'
                ),
                'reason': None,
                'request_name': latest_request.name,
                'reviewed_by': '',
            }

        return None

    @http.route(MY_EMPLOYEE_URL + '/personal', type='http', auth='user', website=True, methods=['GET', 'POST'],
                csrf=False)
    def portal_employee_personal(self, **post):
        try:
            employee = self._get_employee()

            countries = request.env['res.country'].sudo().search([], order='name')

            _logger.info("portal_employee_profile - Countries count: %s", len(countries))

            if request.httprequest.method == 'POST':
                try:
                    vals = {}

                    # Basic information
                    if post.get('work_email'):
                        import re
                        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                        if re.match(email_pattern, post.get('work_email')):
                            vals['work_email'] = post.get('work_email')
                        else:
                            return request.make_json_response({
                                'success': False,
                                'error': 'Invalid email format'
                            })

                    if post.get('work_phone'):
                        vals['work_phone'] = post.get('work_phone')
                    if post.get('birthday'):
                        vals['birthday'] = post.get('birthday')
                    if post.get('sex'):
                        vals['sex'] = post.get('sex')
                    if post.get('marital'):
                        vals['marital'] = post.get('marital')
                    if post.get('children'):
                        try:
                            vals['children'] = int(post.get('children'))
                        except (ValueError, TypeError):
                            pass
                    if post.get('study_field'):
                        vals['study_field'] = post.get('study_field')
                    if post.get('l10n_in_relationship'):
                        vals['l10n_in_relationship'] = post.get('l10n_in_relationship')

                    # Identity documents
                    if post.get('emirates_id_number'):
                        vals['emirates_id_number'] = post.get('emirates_id_number')
                    if post.get('emirates_issue_date'):
                        vals['emirates_issue_date'] = post.get('emirates_issue_date')
                    if post.get('emirates_expiry_date'):
                        vals['emirates_expiry_date'] = post.get('emirates_expiry_date')
                    if post.get('ssnid'):
                        vals['ssnid'] = post.get('ssnid')
                    if post.get('issue_date'):
                        vals['issue_date'] = post.get('issue_date')
                    if post.get('expiry_date'):
                        vals['expiry_date'] = post.get('expiry_date')

                    if post.get('issue_countries_id'):
                        try:
                            vals['issue_countries_id'] = int(post.get('issue_countries_id'))
                        except (ValueError, TypeError):
                            country = request.env['res.country'].sudo().search([
                                ('name', '=', post.get('issue_countries_id'))
                            ], limit=1)
                            if country:
                                vals['issue_countries_id'] = country.id

                    # Nationality
                    if post.get('country_id'):
                        try:
                            vals['country_id'] = int(post.get('country_id'))
                        except (ValueError, TypeError):
                            country = request.env['res.country'].sudo().search([
                                ('name', '=', post.get('country_id'))
                            ], limit=1)
                            if country:
                                vals['country_id'] = country.id

                    # Contact information
                    if post.get('private_email'):
                        vals['private_email'] = post.get('private_email')
                    if post.get('private_phone'):
                        vals['private_phone'] = post.get('private_phone')
                    if post.get('private_street'):
                        vals['private_street'] = post.get('private_street')
                    if post.get('private_street2'):
                        vals['private_street2'] = post.get('private_street2')
                    if post.get('private_city'):
                        vals['private_city'] = post.get('private_city')
                    if post.get('private_zip'):
                        vals['private_zip'] = post.get('private_zip')
                    if post.get('e_private_city'):
                        vals['e_private_city'] = post.get('e_private_city')

                    # Emergency contact
                    if post.get('emergency_contact'):
                        vals['emergency_contact'] = post.get('emergency_contact')
                    if post.get('emergency_phone'):
                        vals['emergency_phone'] = post.get('emergency_phone')

                    # Dependent Details - Child 1
                    if post.get('dependent_child_name_1') is not None:
                        vals['dependent_child_name_1'] = post.get('dependent_child_name_1', '').strip()
                    if post.get('dependent_child_dob_1'):
                        vals['dependent_child_dob_1'] = post.get('dependent_child_dob_1')
                    if post.get('dependent_child_gender_1'):
                        vals['dependent_child_gender_1'] = post.get('dependent_child_gender_1')
                    if post.get('dependent_child_passport_no') is not None:
                        vals['dependent_child_passport_no'] = post.get('dependent_child_passport_no', '').strip()
                    if post.get('dependent_child_passport_issue_date_1'):
                        vals['dependent_child_passport_issue_date_1'] = post.get(
                            'dependent_child_passport_issue_date_1')
                    if post.get('dependent_child_passport_expiry_date_1'):
                        vals['dependent_child_passport_expiry_date_1'] = post.get(
                            'dependent_child_passport_expiry_date_1')

                    # General Information
                    if post.get('u_private_city'):
                        vals['u_private_city'] = post.get('u_private_city')
                    if post.get('industry_start_date'):
                        vals['industry_start_date'] = post.get('industry_start_date')
                    if post.get('experience'):
                        vals['experience'] = post.get('experience')
                    if post.get('current_role'):
                        vals['current_role'] = post.get('current_role')
                    if post.get('current_address'):
                        vals['current_address'] = post.get('current_address')
                    if post.get('phone_code_1'):
                        vals['phone_code_1'] = post.get('phone_code_1')

                    # Emergency Contact UAE
                    if post.get('emergency_contact_person_name'):
                        vals['emergency_contact_person_name'] = post.get('emergency_contact_person_name')
                    if post.get('emergency_contact_person_phone'):
                        vals['emergency_contact_person_phone'] = post.get('emergency_contact_person_phone')
                    if post.get('alternate_mobile_number'):
                        vals['alternate_mobile_number'] = post.get('alternate_mobile_number')
                    if post.get('emergency_contact_person_name_1'):
                        vals['emergency_contact_person_name_1'] = post.get('emergency_contact_person_name_1')
                    if post.get('emergency_contact_person_phone_1'):
                        vals['emergency_contact_person_phone_1'] = post.get('emergency_contact_person_phone_1')
                    if post.get('second_alternative_number'):
                        vals['second_alternative_number'] = post.get('second_alternative_number')
                    if post.get('home_land_line_no'):
                        vals['home_land_line_no'] = post.get('home_land_line_no')

                    # Spouse Info
                    if post.get('spouse_passport_no'):
                        vals['spouse_passport_no'] = post.get('spouse_passport_no')
                    if post.get('spouse_passport_issue_date'):
                        vals['spouse_passport_issue_date'] = post.get('spouse_passport_issue_date')
                    if post.get('spouse_passport_expiry_date'):
                        vals['spouse_passport_expiry_date'] = post.get('spouse_passport_expiry_date')
                    if post.get('spouse_visa_no'):
                        vals['spouse_visa_no'] = post.get('spouse_visa_no')
                    if post.get('spouse_visa_expire_date'):
                        vals['spouse_visa_expire_date'] = post.get('spouse_visa_expire_date')
                    if post.get('spouse_emirates_id_no'):
                        vals['spouse_emirates_id_no'] = post.get('spouse_emirates_id_no')
                    if post.get('spouse_emirates_issue_date'):
                        vals['spouse_emirates_issue_date'] = post.get('spouse_emirates_issue_date')
                    if post.get('spouse_emirates_id_expiry_date'):
                        vals['spouse_emirates_id_expiry_date'] = post.get('spouse_emirates_id_expiry_date')
                    if post.get('spouse_aadhar_no'):
                        vals['spouse_aadhar_no'] = post.get('spouse_aadhar_no')

                    # Father Mother Info
                    if post.get('father_name'):
                        vals['father_name'] = post.get('father_name')
                    if post.get('father_dob'):
                        vals['father_dob'] = post.get('father_dob')
                    if post.get('mother_name'):
                        vals['mother_name'] = post.get('mother_name')
                    if post.get('mother_dob'):
                        vals['mother_dob'] = post.get('mother_dob')

                    # Employee Details
                    if post.get('employee_nominee_name'):
                        vals['employee_nominee_name'] = post.get('employee_nominee_name')
                    if post.get('employee_nominee_contact_no'):
                        vals['employee_nominee_contact_no'] = post.get('employee_nominee_contact_no')
                    if post.get('domain_worked'):
                        vals['domain_worked'] = post.get('domain_worked')
                    if post.get('primary_skill'):
                        vals['primary_skill'] = post.get('primary_skill')
                    if post.get('secondary_skill'):
                        vals['secondary_skill'] = post.get('secondary_skill')
                    if post.get('tool_used'):
                        vals['tool_used'] = post.get('tool_used')

                    # Last Organisation Info  ← FIXED: was wrongly indented inside tool_used block
                    if post.get('last_organisation_name'):
                        vals['last_organisation_name'] = post.get('last_organisation_name')
                    if post.get('last_location'):
                        vals['last_location'] = post.get('last_location')
                    if post.get('last_salary_per_annum_currency'):
                        vals['last_salary_per_annum_currency'] = post.get('last_salary_per_annum_currency')
                    if post.get('last_salary_per_annum_amt'):
                        try:
                            vals['last_salary_per_annum_amt'] = float(post.get('last_salary_per_annum_amt'))
                        except (ValueError, TypeError):
                            pass
                    if post.get('reason_for_leaving'):
                        vals['reason_for_leaving'] = post.get('reason_for_leaving')
                    if post.get('last_report_manager_name'):
                        vals['last_report_manager_name'] = post.get('last_report_manager_name')
                    if post.get('last_report_manager_designation'):
                        vals['last_report_manager_designation'] = post.get('last_report_manager_designation')
                    if post.get('last_report_manager_mob_no'):
                        vals['last_report_manager_mob_no'] = post.get('last_report_manager_mob_no')
                    if post.get('last_report_manager_mail'):
                        import re
                        email_pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
                        if re.match(email_pattern, post.get('last_report_manager_mail')):
                            vals['last_report_manager_mail'] = post.get('last_report_manager_mail')
                        else:
                            return request.make_json_response({
                                'success': False,
                                'error': 'Invalid Reporting Manager email format'
                            })

                    # Many2one - Child 1 Passport Issuing Country
                    if post.get('dependent_child_passport_issuing_countries_1_id'):
                        try:
                            vals['dependent_child_passport_issuing_countries_1_id'] = int(
                                post.get('dependent_child_passport_issuing_countries_1_id')
                            )
                        except (ValueError, TypeError):
                            country = request.env['res.country'].sudo().search([
                                ('name', '=', post.get('dependent_child_passport_issuing_countries_1_id'))
                            ], limit=1)
                            if country:
                                vals['dependent_child_passport_issuing_countries_1_id'] = country.id

                    if post.get('dependent_child_visa_no_1') is not None:
                        vals['dependent_child_visa_no_1'] = post.get('dependent_child_visa_no_1', '').strip()
                    if post.get('dependent_child_visa_expiration_date_1'):
                        vals['dependent_child_visa_expiration_date_1'] = post.get(
                            'dependent_child_visa_expiration_date_1')
                    if post.get('dependent_child_emirates_id_no_1') is not None:
                        vals['dependent_child_emirates_id_no_1'] = post.get('dependent_child_emirates_id_no_1',
                                                                            '').strip()
                    if post.get('dependent_child_emirates_id_issue_date_1'):
                        vals['dependent_child_emirates_id_issue_date_1'] = post.get(
                            'dependent_child_emirates_id_issue_date_1')
                    if post.get('dependent_child_emirates_id_expiry_date_1'):
                        vals['dependent_child_emirates_id_expiry_date_1'] = post.get(
                            'dependent_child_emirates_id_expiry_date_1')
                    if post.get('dependent_child_aadhar_no_1') is not None:
                        vals['dependent_child_aadhar_no_1'] = post.get('dependent_child_aadhar_no_1', '').strip()

                    # Personal information
                    if post.get('legal_name'):
                        vals['legal_name'] = post.get('legal_name')
                    if post.get('place_of_birth'):
                        vals['place_of_birth'] = post.get('place_of_birth')

                    # Document and personal details
                    if post.get('whatsapp'):
                        vals['whatsapp'] = post.get('whatsapp')
                    if post.get('house_no'):
                        vals['house_no'] = post.get('house_no')
                    if post.get('area_name'):
                        vals['area_name'] = post.get('area_name')
                    if post.get('city'):
                        vals['city'] = post.get('city')
                    if post.get('zip_code'):
                        vals['zip_code'] = post.get('zip_code')
                    if post.get('linkedin'):
                        vals['linkedin'] = post.get('linkedin')

                    # Visa and work permit
                    if post.get('visa_no'):
                        vals['visa_no'] = post.get('visa_no')
                    if post.get('permit_no'):
                        vals['permit_no'] = post.get('permit_no')

                    # Social Media Details
                    if post.get('facebook_profile') is not None:
                        vals['facebook_profile'] = post.get('facebook_profile', '').strip()
                    if post.get('insta_profile') is not None:
                        vals['insta_profile'] = post.get('insta_profile', '').strip()
                    if post.get('twitter_profile') is not None:
                        vals['twitter_profile'] = post.get('twitter_profile', '').strip()

                    # Career Details
                    if post.get('career_break_detail') is not None:
                        vals['career_break_detail'] = post.get('career_break_detail', '').strip()

                    # Industry Details
                    if post.get('industry_ref_name') is not None:
                        vals['industry_ref_name'] = post.get('industry_ref_name', '').strip()
                    if post.get('industry_ref_email') is not None:
                        vals['industry_ref_email'] = post.get('industry_ref_email', '').strip()
                    if post.get('industry_ref_mob_no') is not None:
                        vals['industry_ref_mob_no'] = post.get('industry_ref_mob_no', '').strip()
                    if post.get('home_country_id_name') is not None:
                        vals['home_country_id_name'] = post.get('home_country_id_name', '').strip()
                    if post.get('home_country_id_number') is not None:
                        vals['home_country_id_number'] = post.get('home_country_id_number', '').strip()

                    # Citizenship
                    if post.get('identification_id'):
                        vals['identification_id'] = post.get('identification_id')
                    if post.get('passport_id'):
                        vals['passport_id'] = post.get('passport_id')
                    if post.get('mother_tongue_name'):
                        vals['mother_tongue_name'] = post.get('mother_tongue_name')
                    if post.get('language_known_name') is not None:
                        vals['language_known_name'] = post.get('language_known_name', '').strip()

                    # Selection field with validation
                    allowed_blood_groups = ['a_pos', 'a_neg', 'b_pos', 'b_neg', 'ab_pos', 'ab_neg', 'o_pos', 'o_neg',
                                            'unknown']
                    if post.get('blood_group') and post.get('blood_group') in allowed_blood_groups:
                        vals['blood_group'] = post.get('blood_group')

                    # Certificate - selection field with validation
                    allowed_certificates = ['graduate', 'bachelor', 'master', 'doctor', 'other']
                    if post.get('certificate') and post.get('certificate') in allowed_certificates:
                        vals['certificate'] = post.get('certificate')

                    # Checkbox field - always set True or False
                    vals['is_non_resident'] = True if post.get('is_non_resident') == 'on' else False

                    # Single write call - all fields together
                    _logger.info("Writing vals to employee %s: %s", employee.id, list(vals.keys()))
                    employee.sudo().write(vals)
                    _logger.info("Successfully wrote vals for employee %s", employee.id)

                    # Handle document uploads
                    self._handle_document_uploads(employee, request.httprequest.files)

                    return request.make_json_response({
                        'success': True,
                        'message': 'Personal details updated successfully'
                    })

                except Exception as e:
                    _logger.error("Error in portal_employee_personal POST: %s", str(e))
                    import traceback
                    _logger.error("Traceback: %s", traceback.format_exc())
                    return request.make_json_response({
                        'success': False,
                        'error': str(e)
                    })

            # GET - pass all required variables to template
            notification = None
            try:
                latest_request = request.env['hr.profile.change.request'].sudo().search(
                    [('employee_id', '=', employee.id)], order='id desc', limit=1
                )
                notification = self._get_notification(latest_request)
            except Exception as e:
                _logger.warning("Could not load notification for employee %s: %s", employee.id, str(e))

                # Build portal_overlay from last pending/rejected submission
                portal_overlay = {}
                if (hasattr(employee, 'last_portal_submission')
                        and employee.last_portal_submission
                        and getattr(employee, 'last_submission_state', '') in ('pending', 'rejected')):
                    try:
                        import json
                        portal_overlay = json.loads(employee.last_portal_submission)
                    except Exception:
                        portal_overlay = {}

                return request.render('employee_self_service_portal.portal_employee_profile_personal', {
                    'employee': employee,
                    'section': 'personal',
                    'countries': countries,
                    'notification': notification,
                    'portal_overlay': portal_overlay,  # ← FIX
                })

        except Exception as e:
            _logger.error("Fatal error in portal_employee_personal: %s", str(e))
            import traceback
            _logger.error("Traceback: %s", traceback.format_exc())
            return request.redirect('/my/employee')

        return request.render('employee_self_service_portal.portal_employee_profile_personal', {
            'employee': employee,
            'section': 'personal',
        })

    @http.route(MY_EMPLOYEE_URL + '/upload-photo', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def portal_employee_upload_photo(self, **post):
        """Handle employee photo upload"""
        # TEMPORARILY DISABLED — writes paused
        return request.make_json_response({
            'success': False,
            'error': 'Profile photo upload is temporarily unavailable. Please contact HR for any changes.'
        })

        try:
            employee = self._get_employee()

            # Get uploaded file
            photo_file = request.httprequest.files.get('photo')
            if not photo_file:
                return request.make_json_response({
                    'success': False,
                    'error': 'No photo file provided'
                })

            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif']
            if photo_file.content_type not in allowed_types:
                return request.make_json_response({
                    'success': False,
                    'error': 'Invalid file type. Please upload JPG, PNG, or GIF only.'
                })

            # Validate file size (5MB max)
            max_size = 5 * 1024 * 1024  # 5MB
            photo_file.seek(0, 2)  # Seek to end
            file_size = photo_file.tell()
            photo_file.seek(0)  # Seek back to beginning

            if file_size > max_size:
                return request.make_json_response({
                    'success': False,
                    'error': 'File too large. Maximum size is 5MB.'
                })

            # Read and encode image
            import base64
            photo_data = base64.b64encode(photo_file.read())

            # Update employee image
            employee.sudo().write({
                'image_1920': photo_data
            })

            return request.make_json_response({
                'success': True,
                'message': 'Photo uploaded successfully',
                'image_url': f'/web/image/hr.employee/{employee.id}/image_1920/150x150'
            })

        except Exception as e:
            return request.make_json_response({
                'success': False,
                'error': f'Upload failed: {str(e)}'
            })

    @http.route(MY_EMPLOYEE_URL + '/export-pdf', type='http', auth='user', website=True)
    def portal_employee_export_pdf(self, **kwargs):
        """Export employee profile as PDF"""
        try:
            employee = self._get_employee()

            # Create PDF using reportlab or return HTML for now
            html_content = request.env['ir.qweb']._render('employee_self_service_portal.profile_pdf_template', {
                'employee': employee,
                'company': request.env.company,
            })

            # Convert HTML to PDF (simplified version)
            pdf_data = html_content.encode('utf-8')

            return request.make_response(
                pdf_data,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="profile_{employee.name.replace(" ", "_")}.pdf"')
                ]
            )

        except Exception as e:
            return request.redirect('/my/employee/personal?error=export_failed')

    def _handle_document_uploads(self, employee, files):
        """Handle document file uploads"""
        try:
            import base64

            # Handle Emirates ID file
            emirates_file = files.get('emirates_id_file')
            if emirates_file and emirates_file.filename:
                file_data = base64.b64encode(emirates_file.read())
                employee.sudo().write({
                    'emirates_id_file': file_data,
                    'emirates_id_filename': emirates_file.filename,
                })

            # Handle Passport file
            passport_file = files.get('passport_file')
            if passport_file and passport_file.filename:
                file_data = base64.b64encode(passport_file.read())
                employee.sudo().write({
                    'passport_file': file_data,
                    'passport_filename': passport_file.filename,
                })

            # Handle Other Documents
            other_file = files.get('other_documents')
            if other_file and other_file.filename:
                file_data = base64.b64encode(other_file.read())
                employee.sudo().write({
                    'other_documents': file_data,
                    'other_documents_filename': other_file.filename,
                })

        except Exception as e:
            _logger.error("Error handling document uploads: %s", str(e))

    def _save_employee_document(self, employee, file, doc_type):
        """Save individual document file"""
        try:
            import base64

            # Validate file size (10MB max)
            max_size = 10 * 1024 * 1024
            file.seek(0, 2)
            file_size = file.tell()
            file.seek(0)

            if file_size > max_size:
                return

            # Read file data
            file_data = base64.b64encode(file.read())

            attachment = request.env['ir.attachment'].sudo().create({
                'name': f"{doc_type} - {file.filename}",
                'datas': file_data,
                'res_model': 'hr.employee',
                'res_id': employee.id,
                'public': False,
                'type': 'binary',
            })

            return attachment

        except Exception as e:
            _logger.error(f"Error saving document {file.filename}: {str(e)}")
            return None

    @http.route(MY_EMPLOYEE_URL + '/experience', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_experience(self, **post):
        employee = self._get_employee()
        if request.httprequest.method == 'POST':
            action = post.get('action')
            try:
                if action == 'upload_resume':
                    resume_file = request.httprequest.files.get('resume_file')
                    if not resume_file or not resume_file.filename:
                        return request.make_json_response({'success': False, 'error': 'No file provided.'})

                    allowed_types = [
                        'application/pdf',
                        'application/msword',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    ]
                    if resume_file.content_type not in allowed_types:
                        return request.make_json_response(
                            {'success': False, 'error': 'Only PDF, DOC, and DOCX files are allowed.'})

                    file_content = resume_file.read()
                    if len(file_content) > 10 * 1024 * 1024:
                        return request.make_json_response(
                            {'success': False, 'error': 'File size must not exceed 10 MB.'})

                    import base64
                    file_data = base64.b64encode(file_content).decode()

                    payload = {
                        '_resume_change': {
                            'filename': resume_file.filename,
                            'mimetype': resume_file.content_type or 'application/octet-stream',
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json_lib.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    request.env['ir.attachment'].sudo().create({
                        'name': resume_file.filename,
                        'datas': file_data,
                        'res_model': 'hr.profile.change.request',
                        'res_id': pcr.id,
                        'mimetype': resume_file.content_type or 'application/octet-stream',
                        'description': 'Resume submitted by employee for approval',
                    })
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'add_skill':

                    batch_raw = post.get('batch_skills', '')

                    if batch_raw:

                        try:
                            batch_skills = json_lib.loads(batch_raw)
                        except Exception:
                            return request.make_json_response({'success': False, 'error': 'Invalid batch data.'})

                        if not batch_skills:
                            return request.make_json_response({'success': False, 'error': 'No skills provided.'})

                        for item in batch_skills:
                            skill = request.env['hr.skill'].sudo().browse(int(item.get('skill_id', 0)))
                            if not skill.exists():
                                return request.make_json_response({
                                    'success': False,
                                    'error': f'Skill "{item.get("skill_name", "")}" no longer exists.'
                                })

                        payload = {
                            '_skill_change': {
                                'cert_action': 'add_batch',
                                'skills': batch_skills,
                                # list of {skill_id, skill_name, level_id, level_name, type_id, type_name}
                            }
                        }
                        pcr = request.env['hr.profile.change.request'].sudo().create({
                            'employee_id': employee.id,
                            'submitted_data': json_lib.dumps(payload),
                            'state': 'draft',
                        })
                        pcr.action_submit()
                        return request.make_json_response({'success': True, 'reference': pcr.name})

                    else:
                        # Single skill
                        skill_id = int(post.get('skill_id', 0) or 0)
                        level_id = int(post.get('level_id', 0) or 0)
                        type_id = int(post.get('type_id', 0) or 0)
                        skill_name = post.get('skill_name', '')
                        level_name = post.get('level_name', '')
                        type_name = post.get('type_name', '')

                        if not skill_id:
                            return request.make_json_response({'success': False, 'error': 'Skill is required.'})
                        skill = request.env['hr.skill'].sudo().browse(skill_id)
                        if not skill.exists():
                            return request.make_json_response({'success': False, 'error': 'Skill not found.'})

                        payload = {
                            '_skill_change': {
                                'cert_action': 'add',
                                'skill_id': skill_id,
                                'skill_name': skill_name,
                                'level_id': level_id,
                                'level_name': level_name,
                                'type_id': type_id or skill.skill_type_id.id,
                                'type_name': type_name,
                            }
                        }
                        pcr = request.env['hr.profile.change.request'].sudo().create({
                            'employee_id': employee.id,
                            'submitted_data': json_lib.dumps(payload),
                            'state': 'draft',
                        })
                        pcr.action_submit()
                        return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'edit_skill':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    level_id = int(post.get('level_id', 0) or 0)
                    level_name = post.get('level_name', '')

                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found.'})

                    payload = {
                        '_skill_change': {
                            'cert_action': 'edit',
                            'skill_record_id': record_id,
                            'skill_name': skill_record.skill_id.name,
                            'type_name': skill_record.skill_type_id.name,
                            'level_id': level_id,
                            'level_name': level_name,
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json_lib.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                elif action == 'delete_skill':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response({'success': False, 'error': 'Record not found.'})

                    payload = {
                        '_skill_change': {
                            'cert_action': 'delete',
                            'skill_record_id': record_id,
                            'skill_name': skill_record.skill_id.name,
                            'type_name': skill_record.skill_type_id.name,
                        }
                    }
                    pcr = request.env['hr.profile.change.request'].sudo().create({
                        'employee_id': employee.id,
                        'submitted_data': json_lib.dumps(payload),
                        'state': 'draft',
                    })
                    pcr.action_submit()
                    return request.make_json_response({'success': True, 'reference': pcr.name})

                else:
                    return request.make_json_response({'success': False, 'error': 'Unknown action.'})

            except Exception as e:
                import traceback
                _logger.error("Experience portal error: %s\n%s", str(e), traceback.format_exc())
                return request.make_json_response({'success': False, 'error': str(e)})

        # ── GET
        skill_types = request.env['hr.skill.type'].sudo().search([
            ('is_certification', '=', False)
        ], order='name')

        all_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')

        all_levels = request.env['hr.skill.level'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='skill_type_id, name')

        skill_data = {'skills': {}, 'levels': {}}
        for sk in all_skills:
            tid = str(sk.skill_type_id.id)
            skill_data['skills'].setdefault(tid, [])
            skill_data['skills'][tid].append({'id': str(sk.id), 'name': sk.name})
        for lv in all_levels:
            tid = str(lv.skill_type_id.id)
            skill_data['levels'].setdefault(tid, [])
            skill_data['levels'][tid].append({'id': str(lv.id), 'name': lv.name})

        employee_skills = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.is_certification', '=', False),
        ], order='skill_type_id, id')

        pending_skill_pcrs = request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
        ], order='create_date desc')

        pending_skill_changes = []
        for pcr in pending_skill_pcrs:
            try:
                data = json_lib.loads(pcr.submitted_data or '{}')
                skill_change = data.get('_skill_change')
                if not skill_change:
                    continue
                action_type = skill_change.get('cert_action', '')
                if action_type == 'add_batch':
                    # One PCR, multiple skills — expand to one row each
                    for item in skill_change.get('skills', []):
                        pending_skill_changes.append({
                            'pcr_name': pcr.name,
                            'cert_action': 'add',
                            'type_name': item.get('type_name', '—'),
                            'skill_name': item.get('skill_name', '—'),
                            'level_name': item.get('level_name', '—'),
                        })
                else:
                    pending_skill_changes.append({
                        'pcr_name': pcr.name,
                        'cert_action': action_type,
                        'type_name': skill_change.get('type_name', '—'),
                        'skill_name': skill_change.get('skill_name', '—'),
                        'level_name': skill_change.get('level_name', '—'),
                    })
            except Exception:
                continue
        pending_resume_change = None
        for pcr in pending_skill_pcrs:
            try:
                data = json_lib.loads(pcr.submitted_data or '{}')
                resume_change = data.get('_resume_change')
                if not resume_change:
                    continue
                pending_resume_change = {
                    'pcr_name': pcr.name,
                    'filename': resume_change.get('filename', '—'),
                }
                break
            except Exception:
                continue

        return request.render(
            'employee_self_service_portal.portal_employee_profile_experience', {
                'employee': employee,
                'section': 'experience',
                'employee_skills': employee_skills,
                'skill_types': skill_types,
                'skill_data_json': json_lib.dumps(skill_data),
                'pending_skill_changes': pending_skill_changes,
                'pending_resume_change': pending_resume_change,
            }
        )


    @http.route(MY_EMPLOYEE_URL + '/certification', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_certification(self, **post):
        employee = self._get_employee()

        skill_types = request.env['hr.skill.type'].sudo().search([
            ('is_certification', '=', 'True')
        ])
        certificate_skills = request.env['hr.skill'].sudo().search([
            ('skill_type_id', 'in', skill_types.ids)
        ], order='name')

        if request.httprequest.method == 'POST':
            action = post.get('action')
            try:
                import base64

                attachment_data = None
                attachment_name = None
                attachment_mime = None
                attachment_file = request.httprequest.files.get('attachment_file')
                if attachment_file and attachment_file.filename:
                    attachment_data = base64.b64encode(attachment_file.read()).decode()
                    attachment_name = attachment_file.filename
                    attachment_mime = attachment_file.content_type or 'application/octet-stream'

                if action == 'add_certification':
                    skill_id = int(post.get('skill_id', 0) or 0)
                    if not skill_id:
                        return request.make_json_response({'success': False, 'error': 'Certificate Name is required.'})

                    skill = request.env['hr.skill'].sudo().browse(skill_id)
                    if not skill.exists():
                        return request.make_json_response({'success': False, 'error': 'Selected skill not found.'})

                    cert_payload = {
                        'cert_action': 'add',
                        'skill_id': skill_id,
                        'skill_name': skill.name,
                        'skill_type_id': skill.skill_type_id.id,
                        'valid_from': post.get('valid_from') or '',
                        'valid_to': post.get('valid_to') or '',
                        'has_attachment': bool(attachment_data),
                        'attachment_name': attachment_name or '',
                    }
                    if attachment_data:
                        cert_payload['attachment_data'] = attachment_data
                        cert_payload['attachment_mime'] = attachment_mime

                elif action == 'edit_certification':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response(
                            {'success': False, 'error': 'Record not found or access denied.'})

                    cert_payload = {
                        'cert_action': 'edit',
                        'skill_record_id': record_id,
                        'skill_name': skill_record.skill_id.name,
                        'valid_from': post.get('valid_from') or '',
                        'valid_to': post.get('valid_to') or '',
                        'has_attachment': bool(attachment_data),
                        'attachment_name': attachment_name or '',
                    }
                    if attachment_data:
                        cert_payload['attachment_data'] = attachment_data
                        cert_payload['attachment_mime'] = attachment_mime

                elif action == 'delete_certification':
                    record_id = int(post.get('skill_record_id', 0) or 0)
                    skill_record = request.env['hr.employee.skill'].sudo().browse(record_id)
                    if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                        return request.make_json_response(
                            {'success': False, 'error': 'Record not found or access denied.'})

                    cert_payload = {
                        'cert_action': 'delete',
                        'skill_record_id': record_id,
                        'skill_name': skill_record.skill_id.name,
                    }
                else:
                    return request.make_json_response({'success': False, 'error': 'Unknown action.'})

                import json as json_lib
                pcr = request.env['hr.profile.change.request'].sudo().create({
                    'employee_id': employee.id,
                    'submitted_data': json_lib.dumps({'_cert_change': cert_payload}),
                    'state': 'draft',
                })
                pcr.action_submit()

                if attachment_data:
                    request.env['ir.attachment'].sudo().create({
                        'name': attachment_name,
                        'datas': attachment_data,
                        'res_model': 'hr.profile.change.request',
                        'res_id': pcr.id,
                        'mimetype': attachment_mime,
                        'description': 'Certification attachment submitted by employee',
                    })

                return request.make_json_response({
                    'success': True,
                    'message': 'Your certification change has been submitted for HR approval.',
                    'reference': pcr.name,
                })

            except Exception as e:
                import traceback
                _logger.error("Certification portal error: %s\n%s", str(e), traceback.format_exc())
                return request.make_json_response({'success': False, 'error': str(e)})

        import json as json_lib

        certifications = request.env['hr.employee.skill'].sudo().search([
            ('employee_id', '=', employee.id),
            ('skill_type_id.is_certification', '=', True),
        ], order='id desc')

        pending_pcrs = request.env['hr.profile.change.request'].sudo().search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'pending'),
        ], order='id desc')

        pending_cert_changes = []
        for pcr in pending_pcrs:
            if not pcr.submitted_data:
                continue
            try:
                data = json_lib.loads(pcr.submitted_data)
                cert_change = data.get('_cert_change')
                if not cert_change:
                    continue

                pcr_attachment = request.env['ir.attachment'].sudo().search([
                    ('res_model', '=', 'hr.profile.change.request'),
                    ('res_id', '=', pcr.id),
                ], limit=1)

                pending_cert_changes.append({
                    'pcr_name': pcr.name,
                    'pcr_id': pcr.id,
                    'cert_action': cert_change.get('cert_action', ''),
                    'skill_name': cert_change.get('skill_name', '—'),
                    'valid_from': cert_change.get('valid_from') or '',
                    'valid_to': cert_change.get('valid_to') or '',
                    'attachment_name': cert_change.get('attachment_name') or '',
                    'pcr_attachment': pcr_attachment or False,
                    'skill_record_id': cert_change.get('skill_record_id', None),
                })
            except Exception:
                continue

        return request.render(
            'employee_self_service_portal.portal_employee_profile_certification', {
                'employee': employee,
                'section': 'certification',
                'certifications': certifications,
                'certificate_skills': certificate_skills,
                'pending_cert_changes': pending_cert_changes,
            }
        )

    @http.route('/portal/attachment/preview/<int:attachment_id>', type='http', auth='user', website=True)
    def preview_attachment(self, attachment_id, **kwargs):

        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not attachment.exists():
            return request.not_found()

        employee = self._get_employee()

        if attachment.res_model == 'hr.employee.skill' and attachment.res_id:
            skill_record = request.env['hr.employee.skill'].sudo().browse(attachment.res_id)
            if not skill_record.exists() or skill_record.employee_id.id != employee.id:
                return request.not_found()


        elif attachment.res_model == 'hr.profile.change.request' and attachment.res_id:
            pcr = request.env['hr.profile.change.request'].sudo().browse(attachment.res_id)
            if not pcr.exists() or pcr.employee_id.id != employee.id:
                return request.not_found()

        else:
            return request.not_found()

        return request.env['ir.binary']._get_stream_from(attachment).get_response(
            as_attachment=False
        )

    @http.route(MY_EMPLOYEE_URL + '/bank', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_employee_bank(self, **post):
        employee = self._get_employee()
        if request.httprequest.method == 'POST':
            vals = {
                'x_bank_account': post.get('x_bank_account'),
                'x_bank_name': post.get('x_bank_name'),
                'x_ifsc': post.get('x_ifsc'),
            }
            employee.sudo().write({k: v for k, v in vals.items() if v is not None})
        return request.render('employee_self_service_portal.portal_employee_profile_bank', {
            'employee': employee,
            'section': 'bank',
        })

    @http.route(
        MY_EMPLOYEE_URL + '/orgchart',
        type='http', auth='user', website=True, methods=['GET']
    )
    def portal_employee_orgchart(self, **post):
        employee = self._get_employee()
        return request.render(
            'employee_self_service_portal.portal_employee_profile_orgchart',
            {
                'employee': employee,
                'section': 'orgchart',
            }
        )

    # @http.route('/my/employee/crm', type='http', auth='user', website=True)
    # @check_portal_access('crm')
    # def portal_employee_crm(self, **kwargs):
    #     employee = self._get_employee()
    #     user = request.env.user
    #
    #     # Build base domain
    #     domain = [('user_id', '=', user.id), ('type', '=', 'opportunity')]
    #
    #     # Apply filters based on parameters
    #     stage_filter = kwargs.get('stage')
    #     if stage_filter:
    #         domain.append(('stage_id', '=', int(stage_filter)))
    #
    #     practice_filter = kwargs.get('practice')
    #     if practice_filter:
    #         # Only apply practice filter if the field exists on the model
    #         lead_model = request.env['crm.lead']
    #         if 'practice_id' in lead_model._fields:
    #             domain.append(('practice_id', '=', int(practice_filter)))
    #
    #     industry_filter = kwargs.get('industry')
    #     if industry_filter:
    #         # Only apply industry filter if the field exists on the model
    #         lead_model = request.env['crm.lead']
    #         if 'industry_id' in lead_model._fields:
    #             domain.append(('industry_id', '=', int(industry_filter)))
    #
    #     priority_filter = kwargs.get('priority')
    #     if priority_filter:
    #         domain.append(('priority', '=', priority_filter))
    #
    #     customer_filter = kwargs.get('customer')
    #     if customer_filter:
    #         domain.append(('partner_id.name', 'ilike', customer_filter))
    #
    #     # Date range filters
    #     date_from = kwargs.get('date_from')
    #     if date_from:
    #         domain.append(('create_date', '>=', date_from + ' 00:00:00'))
    #
    #     date_to = kwargs.get('date_to')
    #     if date_to:
    #         domain.append(('create_date', '<=', date_to + ' 23:59:59'))
    #
    #     # Activity due date filters - filter through activity_ids
    #     activity_due_from = kwargs.get('activity_due_from')
    #     if activity_due_from:
    #         domain.append(('activity_ids.date_deadline', '>=', activity_due_from))
    #
    #     activity_due_to = kwargs.get('activity_due_to')
    #     if activity_due_to:
    #         domain.append(('activity_ids.date_deadline', '<=', activity_due_to))
    #
    #     # Quick activity filters
    #     quick_activity = kwargs.get('quick_activity')
    #     if quick_activity:
    #         from datetime import date, timedelta
    #         today = date.today()
    #
    #         if quick_activity == 'today':
    #             domain.append(('activity_ids.date_deadline', '=', today))
    #         elif quick_activity == 'yesterday':
    #             yesterday = today - timedelta(days=1)
    #             domain.append(('activity_ids.date_deadline', '=', yesterday))
    #         elif quick_activity == 'tomorrow':
    #             tomorrow = today + timedelta(days=1)
    #             domain.append(('activity_ids.date_deadline', '=', tomorrow))
    #         elif quick_activity == 'past':
    #             domain.append(('activity_ids.date_deadline', '<', today))
    #         elif quick_activity == 'future':
    #             domain.append(('activity_ids.date_deadline', '>', today))
    #         elif quick_activity == 'this_week':
    #             # Monday of current week
    #             monday = today - timedelta(days=today.weekday())
    #             sunday = monday + timedelta(days=6)
    #             domain.append(('activity_ids.date_deadline', '>=', monday))
    #             domain.append(('activity_ids.date_deadline', '<=', sunday))
    #         elif quick_activity == 'overdue':
    #             domain.append(('activity_ids.date_deadline', '<', today))
    #         elif quick_activity == 'no_activities':
    #             domain.append(('activity_ids', '=', False))
    #
    #     # Tags filter
    #     tags_filter = kwargs.get('tags')
    #     if tags_filter:
    #         try:
    #             # Handle both single tag and multiple tags
    #             if isinstance(tags_filter, str):
    #                 tag_ids = [int(tags_filter)]
    #             else:
    #                 tag_ids = [int(tag) for tag in tags_filter if tag]
    #
    #             if tag_ids:
    #                 # Check if tag_ids field exists
    #                 lead_model = request.env['crm.lead']
    #                 if 'tag_ids' in lead_model._fields:
    #                     domain.append(('tag_ids', 'in', tag_ids))
    #         except (ValueError, TypeError):
    #             pass  # Skip invalid tag values
    #
    #     leads = request.env['crm.lead'].sudo().search(domain, order='priority desc, create_date desc')
    #
    #     # Custom sorting by nearest activity date
    #     def get_next_activity_date(lead):
    #         """Get the nearest activity date for sorting"""
    #         if not lead.activity_ids:
    #             return date.max  # Leads without activities go to the end
    #
    #         next_activity = lead.activity_ids.sorted('date_deadline')
    #         if next_activity and next_activity[0].date_deadline:
    #             activity_date = next_activity[0].date_deadline
    #             # Convert datetime to date if needed
    #             if hasattr(activity_date, 'date'):
    #                 return activity_date.date()
    #             return activity_date
    #         return date.max
    #
    #     # Sort leads by nearest activity date, then by priority, then by create date
    #     from datetime import date
    #     leads = leads.sorted(key=lambda lead: (
    #         get_next_activity_date(lead),  # Nearest activity first
    #         -int(lead.priority or '0'),  # Higher priority first (reversed)
    #         -lead.id  # Newer leads first (reversed by ID)
    #     ))
    #
    #     # Get filter options for dropdowns - show ALL available options, not just used ones
    #     all_user_leads = request.env['crm.lead'].sudo().search([('user_id', '=', user.id)])
    #
    #     # Get ALL stages available in the system
    #     stages = request.env['crm.stage'].sudo().search([], order='sequence, name')
    #
    #     # Handle practices safely - check if model and field exist
    #     practices = []
    #     try:
    #         if 'practice_id' in all_user_leads._fields:
    #             # Try different possible model names for practice and get ALL practices
    #             practice_model = None
    #             for model_name in ['x_practice', 'crm.practice', 'practice', 'x_crm_practice']:
    #                 try:
    #                     practice_model = request.env[model_name]
    #                     break
    #                 except KeyError:
    #                     continue
    #
    #             if practice_model:
    #                 practices = practice_model.sudo().search([], order='name')
    #     except Exception:
    #         practices = []
    #
    #     industries = []
    #     try:
    #         if 'industry_id' in all_user_leads._fields:
    #             # Get ALL industries available in the system
    #             industries = request.env['crm.industry'].sudo().search([('active', '=', True)], order='name')
    #     except Exception:
    #         industries = []
    #
    #     # Get tags for filter options - show ALL available tags
    #     tags = []
    #     try:
    #         if 'tag_ids' in all_user_leads._fields:
    #             # Get ALL tags available in the system
    #             tags = request.env['crm.tag'].sudo().search([], order='name')
    #     except Exception:
    #         tags = []
    #
    #     # Process leads to add computed fields for template
    #     import datetime
    #     import re
    #     from odoo import fields
    #
    #     today = datetime.date.today()
    #     processed_leads = []
    #
    #     for lead in leads:
    #         lead_data = {
    #             'record': lead,
    #             'activity_summary': self._get_activity_summary(lead),
    #             'next_activity_info': self._get_next_activity_info(lead, today),
    #             'recent_note_info': self._get_recent_note_info(lead),
    #         }
    #         processed_leads.append(lead_data)
    #
    #     # Check if enhanced view is requested
    #     view_type = kwargs.get('view', 'list')  # Default to list view instead of enhanced view
    #     template_name = 'employee_self_service_portal.portal_employee_crm_enhanced' if view_type == 'enhanced' else 'employee_self_service_portal.portal_employee_crm'
    #
    #     # Calculate dashboard KPIs for enhanced view
    #     dashboard_kpis = {}
    #     if view_type == 'enhanced':
    #         all_user_leads_current = request.env['crm.lead'].sudo().search([('user_id', '=', user.id)])
    #         dashboard_kpis = self._calculate_dashboard_kpis(all_user_leads_current, today)
    #
    #     return request.render(template_name, {
    #         'employee': employee,
    #         'leads': leads,  # Keep original for compatibility
    #         'processed_leads': processed_leads,
    #         'stages': stages,  # Add stages for dropdown
    #         'filter_stages': stages,  # Filter options
    #         'filter_practices': practices,
    #         'filter_industries': industries,
    #         'filter_tags': tags,
    #         'dashboard_kpis': dashboard_kpis,  # For enhanced view
    #         'view_type': view_type,  # Current view type
    #         # Current filter values for maintaining state
    #         'current_filters': {
    #             'stage': stage_filter or '',
    #             'practice': practice_filter or '',
    #             'industry': industry_filter or '',
    #             'priority': priority_filter or '',
    #             'customer': customer_filter or '',
    #             'date_from': date_from or '',
    #             'date_to': date_to or '',
    #             'activity_due_from': activity_due_from or '',
    #             'activity_due_to': activity_due_to or '',
    #             'quick_activity': quick_activity or '',
    #             'tags': tags_filter or '',
    #             'view': view_type,
    #         }
    #     })
    #
    # def _get_activity_summary(self, lead):
    #     """Get activity summary for a lead"""
    #     activity_count = len(lead.activity_ids)
    #     return {
    #         'count': activity_count,
    #         'has_activities': activity_count > 0
    #     }
    #
    # def _get_next_activity_info(self, lead, today):
    #     """Get next activity information with relative date"""
    #     if not lead.activity_ids:
    #         return {'has_activity': False}
    #
    #     next_activity = lead.activity_ids.sorted('date_deadline')[0]
    #     activity_date = next_activity.date_deadline
    #
    #     if not activity_date:
    #         return {
    #             'has_activity': True,
    #             'activity_type': next_activity.activity_type_id.name,
    #             'user_name': next_activity.user_id.name,
    #             'relative_date': 'No date',
    #             'badge_class': 'badge-secondary'
    #         }
    #
    #     # Convert to date if it's datetime
    #     if hasattr(activity_date, 'date'):
    #         activity_date = activity_date.date()
    #
    #     date_diff = (activity_date - today).days
    #
    #     # Determine relative date text and badge class
    #     if date_diff == 0:
    #         relative_date = 'Today'
    #         badge_class = 'badge-warning'
    #     elif date_diff == 1:
    #         relative_date = 'Tomorrow'
    #         badge_class = 'badge-info'
    #     elif date_diff == -1:
    #         relative_date = 'Yesterday'
    #         badge_class = 'badge-danger'
    #     elif date_diff < 0:
    #         relative_date = f'Overdue {abs(date_diff)} days'
    #         badge_class = 'badge-danger'
    #     else:
    #         relative_date = f'Due in {date_diff} days'
    #         badge_class = 'badge-info'
    #
    #     return {
    #         'has_activity': True,
    #         'activity_type': next_activity.activity_type_id.name,
    #         'user_name': next_activity.user_id.name,
    #         'relative_date': relative_date,
    #         'badge_class': badge_class
    #     }
    #
    # def _get_recent_contact_note(self, contact):
    #     """Get the most recent CRM lead 'Notes' tab (description field) for a given contact/partner."""
    #     leads = request.env['crm.lead'].sudo().search([
    #         ('partner_id', '=', contact.id),
    #     ], order='write_date desc')
    #
    #     for lead in leads:
    #         if lead.description:
    #             plain_note = html2plaintext(lead.description).strip()
    #             if plain_note:
    #                 note = plain_note
    #                 if len(note) > 47:
    #                     note = note[:47] + '...'
    #                 return note
    #
    #     return '-'
    #
    # def _get_recent_note_info(self, lead):
    #     """Get recent note information"""
    #     import re
    #
    #     recent_notes = lead.message_ids.filtered(
    #         lambda m: m.message_type == 'comment' and m.body and m.body.strip()
    #     )
    #
    #     if not recent_notes:
    #         return {'has_note': False}
    #
    #     recent_note = recent_notes[0]
    #
    #     # Clean HTML tags from body
    #     clean_body = re.sub(r'<[^>]+>', '', recent_note.body or '').strip()
    #
    #     # Truncate if too long
    #     if len(clean_body) > 47:
    #         clean_body = clean_body[:47] + '...'
    #
    #     # Format date
    #     date_str = ''
    #     if recent_note.date:
    #         date_str = recent_note.date.strftime('%m/%d %H:%M')
    #
    #     return {
    #         'has_note': True,
    #         'author_name': recent_note.author_id.name or 'System',
    #         'date_str': date_str,
    #         'clean_body': clean_body,
    #         'full_body': recent_note.body or ''
    #     }
    #
    # def _calculate_dashboard_kpis(self, leads, today):
    #     """Calculate KPIs for the enhanced CRM dashboard"""
    #     from datetime import timedelta
    #
    #     total_leads = len(leads)
    #
    #     # Count leads by stage
    #     new_leads = leads.filtered(lambda l: l.stage_id.name in ['New', 'Qualification'] if l.stage_id else False)
    #     in_progress_leads = leads.filtered(
    #         lambda l: l.stage_id.name in ['Qualified', 'Proposition'] if l.stage_id else False)
    #     won_leads = leads.filtered(lambda l: l.stage_id.name == 'Won' if l.stage_id else False)
    #
    #     # Calculate revenue
    #     total_revenue = sum(leads.mapped('expected_revenue'))
    #     won_revenue = sum(won_leads.mapped('expected_revenue'))
    #
    #     # Activity metrics
    #     overdue_activities = 0
    #     today_activities = 0
    #
    #     for lead in leads:
    #         for activity in lead.activity_ids:
    #             if activity.date_deadline:
    #                 activity_date = activity.date_deadline
    #                 if hasattr(activity_date, 'date'):
    #                     activity_date = activity_date.date()
    #
    #                 if activity_date < today:
    #                     overdue_activities += 1
    #                 elif activity_date == today:
    #                     today_activities += 1
    #
    #     # Conversion rate (won leads / total leads)
    #     conversion_rate = (len(won_leads) / total_leads * 100) if total_leads > 0 else 0
    #
    #     return {
    #         'total_leads': total_leads,
    #         'new_leads': len(new_leads),
    #         'in_progress_leads': len(in_progress_leads),
    #         'won_leads': len(won_leads),
    #         'total_revenue': total_revenue,
    #         'won_revenue': won_revenue,
    #         'overdue_activities': overdue_activities,
    #         'today_activities': today_activities,
    #         'conversion_rate': round(conversion_rate, 1),
    #     }
    #
    # @http.route('/my/employee/crm/create', type='http', auth='user', website=True, methods=['GET', 'POST'])
    # def portal_employee_crm_create(self, **post):
    #     user = request.env.user
    #     if request.httprequest.method == 'POST':
    #         # Process partner_id (customer) - handle creation of new customers
    #         # Process partner_id (customer) - handle creation of new customers
    #         partner_id = _process_partner_field(post.get('partner_id'), 'partner_id')
    #
    #         # Process point_of_contact_id - handle creation of new contacts
    #         point_of_contact_id = _process_partner_field(post.get('point_of_contact_id'), 'point_of_contact_id')
    #
    #         # Link the typed Company name to the customer's parent company
    #         company_name = (post.get('company_name') or '').strip()
    #         if company_name and partner_id:
    #             company = request.env['res.partner'].sudo().search([
    #                 ('name', '=ilike', company_name),
    #                 ('is_company', '=', True),
    #             ], limit=1)
    #             if not company:
    #                 company = request.env['res.partner'].sudo().create({
    #                     'name': company_name,
    #                     'is_company': True,
    #                 })
    #             request.env['res.partner'].sudo().browse(partner_id).write({
    #                 'parent_id': company.id
    #             })
    #
    #         vals = {
    #             'name': post.get('name'),
    #             'partner_id': partner_id,
    #             'email_from': post.get('email_from'),
    #             'phone': post.get('phone'),
    #             'expected_revenue': post.get('expected_revenue') or 0.0,
    #             'user_id': user.id,
    #             'stage_id': post.get('stage_id') or False,
    #             'description': post.get('description'),
    #             'probability': post.get('probability') or 0.0,
    #             'date_deadline': post.get('date_deadline') or False,
    #             # TechCarrot CRM MLR custom fields
    #             'point_of_contact_id': point_of_contact_id,
    #             'practice_id': post.get('practice_id') or False,
    #             'deal_manager_id': post.get('deal_manager_id') or False,
    #             'client_proposal_submission_date': post.get('client_proposal_submission_date') or False,
    #             'proposal_submitted_date': post.get('proposal_submitted_date') or False,
    #             'engaged_presales': bool(post.get('engaged_presales')),
    #             'industry_id': post.get('industry_id') or False,
    #             'type_id': post.get('type_id') or False,
    #         }
    #         lead = request.env['crm.lead'].sudo().create(vals)
    #         tag_id_list = _process_tag_ids(post)
    #         # Always update tag_ids, even if empty (to allow clearing all tags)
    #         lead.sudo().write({'tag_ids': [(6, 0, tag_id_list)]})
    #         return request.redirect(CRM_REDIRECT_URL)
    #     partners = request.env['res.partner'].sudo().search([('active', '=', True), ('is_company', '=', True)])
    #     # Get contacts for point of contact field
    #     contacts = request.env['res.partner'].sudo().search([('is_company', '=', False)])
    #     stages = request.env['crm.stage'].sudo().search([])
    #     all_tags = request.env[CRM_TAG_MODEL].sudo().search([])
    #     # Show all users (internal and portal) as salespersons
    #     salespersons = request.env['hr.employee'].sudo().search([('active', '=', True)])
    #     # Get TechCarrot CRM MLR related data
    #     practices = request.env['crm.practice'].sudo().search([('active', '=', True)])
    #     industries = request.env['crm.industry'].sudo().search([('active', '=', True)])
    #     lead_types = request.env['crm.lead.type'].sudo().search([('active', '=', True)])
    #     employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
    #     current_user_id = request.env.user.id
    #     return request.render('employee_self_service_portal.portal_employee_crm_create', {
    #         'partners': partners,
    #         'contacts': contacts,
    #         'stages': stages,
    #         'all_tags': all_tags,
    #         'salespersons': salespersons,
    #         'practices': practices,
    #         'industries': industries,
    #         'lead_types': lead_types,
    #         'employees': employees,
    #         'current_user_id': current_user_id,
    #     })
    #
    # @http.route('/my/employee/crm/edit/<int:lead_id>', type='http', auth='user', website=True, methods=['GET', 'POST'])
    # def portal_employee_crm_edit(self, lead_id, **post):
    #     lead = request.env[CRM_LEAD_MODEL].sudo().browse(lead_id)
    #     user = request.env.user
    #     if not lead or lead.user_id.id != user.id:
    #         return request.redirect(CRM_REDIRECT_URL)
    #     if request.httprequest.method == 'POST':
    #         # Process point_of_contact_id - handle creation of new contacts
    #         point_of_contact_id = _process_partner_field(post.get('point_of_contact_id'), 'point_of_contact_id')
    #
    #         vals = {
    #             'name': post.get('name'),
    #             'email_from': post.get('email_from'),
    #             'phone': post.get('phone'),
    #             'description': post.get('description'),
    #             'date_deadline': post.get('date_deadline'),
    #             # TechCarrot CRM MLR custom fields
    #             'point_of_contact_id': point_of_contact_id,
    #             'practice_id': post.get('practice_id') or False,
    #             'deal_manager_id': post.get('deal_manager_id') or False,
    #             'client_proposal_submission_date': post.get('client_proposal_submission_date') or False,
    #             'proposal_submitted_date': post.get('proposal_submitted_date') or False,
    #             'engaged_presales': bool(post.get('engaged_presales')),
    #             'industry_id': post.get('industry_id') or False,
    #             'type_id': post.get('type_id') or False,
    #         }
    #         # Convert probability and expected_revenue to float if present
    #         prob = post.get('probability')
    #         if prob:
    #             try:
    #                 vals['probability'] = float(prob)
    #             except Exception:
    #                 pass
    #         exp_rev = post.get('expected_revenue')
    #         if exp_rev:
    #             try:
    #                 vals['expected_revenue'] = float(exp_rev)
    #             except Exception:
    #                 pass
    #         # Validate stage_id
    #         stage_id = post.get('stage_id')
    #         if stage_id:
    #             try:
    #                 stage_id_int = int(stage_id)
    #                 stage = request.env[CRM_STAGE_MODEL].sudo().browse(stage_id_int)
    #                 if stage.exists():
    #                     vals['stage_id'] = stage_id_int
    #             except Exception:
    #                 pass
    #         lead.sudo().write({k: v for k, v in vals.items() if v is not None})
    #         tag_id_list = _process_tag_ids(post)
    #         lead.sudo().write({'tag_ids': [(6, 0, tag_id_list)]})
    #         return request.redirect(CRM_REDIRECT_URL)
    #     stages = request.env[CRM_STAGE_MODEL].sudo().search([])
    #     partners = request.env['res.partner'].sudo().search([])
    #     # Get contacts for point of contact field
    #     contacts = request.env['res.partner'].sudo().search([('is_company', '=', False)])
    #     all_tags = request.env[CRM_TAG_MODEL].sudo().search([])
    #     salespersons = request.env['res.users'].sudo().search([('active', '=', True)])
    #     # Get TechCarrot CRM MLR related data
    #     practices = request.env['crm.practice'].sudo().search([('active', '=', True)])
    #     industries = request.env['crm.industry'].sudo().search([('active', '=', True)])
    #     lead_types = request.env['crm.lead.type'].sudo().search([('active', '=', True)])
    #     employees = request.env['hr.employee'].sudo().search([('active', '=', True)])
    #     activity_types = request.env['mail.activity.type'].sudo().search([])
    #     default_activity_type_id = request.env.ref('mail.mail_activity_data_todo').id if request.env.ref(
    #         'mail.mail_activity_data_todo', raise_if_not_found=False) else (
    #             activity_types and activity_types[0].id or False)
    #     return request.render('employee_self_service_portal.portal_employee_crm_edit', {
    #         'lead': lead,
    #         'stages': stages,
    #         'all_tags': all_tags,
    #         'partners': partners,
    #         'contacts': contacts,
    #         'salespersons': salespersons,
    #         'practices': practices,
    #         'industries': industries,
    #         'lead_types': lead_types,
    #         'employees': employees,
    #         'activity_types': activity_types,
    #         'default_activity_type_id': default_activity_type_id,
    #     })
    #
    # @http.route('/my/employee/crm/delete/<int:lead_id>', type='http', auth='user', website=True, methods=['POST'])
    # def portal_employee_crm_delete(self, lead_id, **post):
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     if lead and lead.user_id.id == user.id:
    #         lead.sudo().unlink()
    #     return request.redirect('/my/employee/crm')
    #
    # @http.route('/my/employee/crm/duplicate/<int:lead_id>', type='http', auth='user', website=True, methods=['POST'])
    # def portal_employee_crm_duplicate(self, lead_id, **post):
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     if lead and lead.user_id.id == user.id:
    #         lead.sudo().copy({'name': lead.name + ' (Copy)'})
    #     return request.redirect('/my/employee/crm')
    #
    # @http.route('/my/contacts', type='http', auth='user', website=True)
    # def portal_contacts_list(self, search='', success='', **kwargs):
    #     customer_ids = request.env['crm.lead'].sudo().search([
    #         ('partner_id', '!=', False)
    #     ]).mapped('partner_id').ids
    #
    #     domain = [('id', 'in', customer_ids)]
    #     if search:
    #         domain += ['|', '|', '|',
    #                    ('name', 'ilike', search),
    #                    ('email', 'ilike', search),
    #                    ('department', 'ilike', search),
    #                    ('customer_code', 'ilike', search)]
    #     contacts = request.env['res.partner'].sudo().search(domain, order='name')
    #     contact_notes = {c.id: self._get_recent_contact_note(c) for c in contacts}
    #     return request.render('employee_self_service_portal.portal_contacts_list', {
    #         'contacts': contacts,
    #         'contact_notes': contact_notes,
    #         'search': search,
    #         'success': success,
    #     })
    #
    # @http.route('/my/contacts/live_search', type='http', auth='user', website=True, csrf=False)
    # def portal_contacts_live_search(self, search='', **kwargs):
    #     customer_ids = request.env['crm.lead'].sudo().search([
    #         ('partner_id', '!=', False)
    #     ]).mapped('partner_id').ids
    #
    #     domain = [('id', 'in', customer_ids)]
    #     if search:
    #         domain += ['|', '|', '|','|',
    #                    ('name', 'ilike', search),
    #                    ('email', 'ilike', search),
    #                    ('department', 'ilike', search),
    #                    ('parent_id.name', 'ilike', search),
    #                    ('customer_code', 'ilike', search)]
    #     contacts = request.env['res.partner'].sudo().search(domain, order='name')
    #     contact_notes = {c.id: self._get_recent_contact_note(c) for c in contacts}
    #     return request.render('employee_self_service_portal.portal_contacts_results_block', {
    #         'contacts': contacts,
    #         'contact_notes': contact_notes,
    #     })
    #
    # @http.route('/my/contacts/create', type='http', auth='user', website=True, methods=['GET', 'POST'])
    # def portal_contacts_create(self, **post):
    #     if request.httprequest.method == 'POST':
    #         email = (post.get('email') or '').strip()
    #         if email:
    #             existing = request.env['res.partner'].sudo().search([
    #                 ('email', '=ilike', email)
    #             ], limit=1)
    #             if existing:
    #                 return request.render('employee_self_service_portal.portal_contacts_create_form', {
    #                     'error': 'A contact with this email already exists: %s' % existing.name,
    #                     'post': post,
    #                 })
    #
    #         name = (post.get('name') or '').upper()
    #
    #         company_name = (post.get('parent_id') or '').strip().upper()
    #         parent_id = False
    #         if company_name:
    #             company = request.env['res.partner'].sudo().search([
    #                 ('name', '=ilike', company_name),
    #                 ('is_company', '=', True),
    #             ], limit=1)
    #             if not company:
    #                 company = request.env['res.partner'].sudo().create({
    #                     'name': company_name,
    #                     'is_company': True,
    #                 })
    #             parent_id = company.id
    #
    #         partner = request.env['res.partner'].sudo().create({
    #             'name': name,
    #             'email': email or False,
    #             'phone': post.get('phone') or False,
    #             'department': post.get('department') or False,
    #             'function': post.get('function') or False,
    #             'parent_id': parent_id,
    #             'is_company': True,
    #         })
    #
    #         request.env['crm.lead'].sudo().create({
    #             'name': name,
    #             'partner_id': partner.id,
    #             'contact_name': name,
    #             'email_from': email or False,
    #             'phone': post.get('phone') or False,
    #             'function': post.get('function') or False,
    #             'type': 'lead',
    #         })
    #
    #         return request.redirect('/my/contacts?success=created')
    #     return request.render('employee_self_service_portal.portal_contacts_create_form', {})
    #
    # @http.route('/my/contacts/<int:partner_id>/edit', type='http', auth='user', website=True, methods=['GET', 'POST'])
    # def portal_contacts_edit(self, partner_id, **post):
    #     customer_ids = request.env['crm.lead'].sudo().search([
    #         ('partner_id', '!=', False)
    #     ]).mapped('partner_id').ids
    #     if partner_id not in customer_ids:
    #         return request.not_found()
    #
    #     contact = request.env['res.partner'].sudo().browse(partner_id)
    #
    #     if request.httprequest.method == 'POST':
    #         email = (post.get('email') or '').strip()
    #         if email:
    #             existing = request.env['res.partner'].sudo().search([
    #                 ('email', '=ilike', email),
    #                 ('id', '!=', partner_id),
    #             ], limit=1)
    #             if existing:
    #                 return request.render('employee_self_service_portal.portal_contacts_edit_form', {
    #                     'error': 'A contact with this email already exists: %s' % existing.name,
    #                     'post': post,
    #                     'contact': contact,
    #                 })
    #
    #         name = (post.get('name') or '').upper()
    #
    #         company_name = (post.get('parent_id') or '').strip().upper()
    #         parent_id = False
    #         if company_name:
    #             company = request.env['res.partner'].sudo().search([
    #                 ('name', '=ilike', company_name),
    #                 ('is_company', '=', True),
    #                 ('id', '!=', partner_id),
    #             ], limit=1)
    #             if not company:
    #                 company = request.env['res.partner'].sudo().create({
    #                     'name': company_name,
    #                     'is_company': True,
    #                 })
    #             parent_id = company.id
    #
    #         vals = {
    #             'name': name,
    #             'email': email or False,
    #             'phone': post.get('phone') or False,
    #             'department': post.get('department') or False,
    #             'function': post.get('function') or False,
    #             'parent_id': parent_id,
    #         }
    #         contact.write(vals)
    #
    #         leads = request.env['crm.lead'].sudo().search([('partner_id', '=', partner_id)])
    #         if leads:
    #             leads.write({
    #                 'name': name,
    #                 'contact_name': name,
    #                 'email_from': email or False,
    #                 'phone': post.get('phone') or False,
    #                 'function': post.get('function') or False,
    #             })
    #
    #         return request.redirect('/my/contacts?success=updated')
    #
    #     return request.render('employee_self_service_portal.portal_contacts_edit_form', {'contact': contact})
    #
    #
    #
    # @http.route('/my/employee/crm/log_note/<int:lead_id>', type='http', auth='user', website=True, methods=['POST'])
    # def portal_employee_crm_log_note(self, lead_id, **post):
    #     import logging
    #     _logger = logging.getLogger(__name__)
    #     lead = request.env[CRM_LEAD_MODEL].sudo().browse(lead_id)
    #     user = request.env.user
    #     note = post.get('note')
    #     file_keys = list(request.httprequest.files.keys())
    #     _logger.info('ESS Portal: Received file keys: %s', file_keys)
    #     files = []
    #     if hasattr(request.httprequest.files, 'getlist'):
    #         files = request.httprequest.files.getlist('attachments')
    #     elif 'attachments' in request.httprequest.files:
    #         file = request.httprequest.files['attachments']
    #         if file:
    #             files = [file]
    #     _logger.info('ESS Portal: Number of files in attachments: %s', len(files))
    #     for f in files:
    #         _logger.info('ESS Portal: File received: filename=%s content_type=%s', getattr(f, 'filename', None),
    #                      getattr(f, 'content_type', None))
    #     # Allow log note with or without text, as long as there are files or a note
    #     if lead and (note or files) and lead.user_id.id == user.id:
    #         msg = lead.message_post(body=note or '', message_type='comment', author_id=user.partner_id.id)
    #         import base64
    #         attachment_ids = []
    #         for file in files:
    #             try:
    #                 file.seek(0)
    #             except Exception:
    #                 pass
    #             file_content = file.read()
    #             if file_content:
    #                 if isinstance(file_content, str):
    #                     file_content = file_content.encode('utf-8')
    #                 encoded_content = base64.b64encode(file_content).decode('utf-8')
    #                 attachment = request.env['ir.attachment'].sudo().create({
    #                     'name': file.filename,
    #                     'datas': encoded_content,
    #                     'res_model': 'crm.lead',
    #                     'res_id': lead.id,
    #                     'mimetype': file.mimetype,
    #                     'type': 'binary',
    #                     'public': True,
    #                 })
    #                 attachment_ids.append(attachment.id)
    #                 _logger.info('ESS Portal: Created attachment id=%s name=%s res_model=%s res_id=%s', attachment.id,
    #                              attachment.name, attachment.res_model, attachment.res_id)
    #         if attachment_ids:
    #             msg.sudo().write({'attachment_ids': [(4, att_id) for att_id in attachment_ids]})
    #     return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #
    # @http.route('/my/employee/crm/add_activity/<int:lead_id>', type='http', auth='user', website=True, methods=['POST'])
    # def portal_employee_crm_add_activity(self, lead_id, **post):
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     summary = post.get('summary')
    #     date_deadline = post.get('date_deadline')
    #     note = post.get('note')
    #     activity_type_id = post.get('activity_type_id')
    #     assigned_user_id = post.get('assigned_user_id')
    #     if lead and summary and date_deadline and lead.user_id.id == user.id:
    #         activity_type_xmlid = None
    #         activity_type_name = ''
    #         if activity_type_id:
    #             activity_type = request.env['mail.activity.type'].sudo().browse(int(activity_type_id))
    #             external_ids = activity_type.get_external_id()
    #             activity_type_xmlid = external_ids.get(activity_type.id)
    #             activity_type_name = activity_type.name
    #         if not activity_type_xmlid:
    #             activity_type_xmlid = 'mail.mail_activity_data_todo'
    #             activity_type_name = 'To Do'
    #         assigned_uid = int(assigned_user_id) if assigned_user_id else user.id
    #         assigned_user = request.env['res.users'].sudo().browse(assigned_uid)
    #         lead.activity_schedule(
    #             activity_type_xmlid,
    #             summary=summary,
    #             note=note,
    #             date_deadline=date_deadline,
    #             user_id=assigned_uid
    #         )
    #         # Log in chatter, escape note
    #         msg = f"Activity created: <b>{activity_type_name}</b> - <b>{summary}</b> (Assigned to: {assigned_user.name}, Due: {date_deadline})"
    #         if note:
    #             msg += f"<br/>Note: {html.escape(note)}"
    #         lead.message_post(body=msg)
    #
    #     # Check if request came from modal (via referer or special parameter)
    #     referer = request.httprequest.environ.get('HTTP_REFERER', '')
    #     if 'activity_modal' in referer or post.get('from_modal'):
    #         return request.redirect('/my/employee/crm')
    #     else:
    #         return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #
    # @http.route('/my/employee/crm/activity_done/<int:activity_id>', type='http', auth='user', website=True,
    #             methods=['POST'])
    # def portal_employee_crm_activity_done(self, activity_id, **post):
    #     activity = request.env['mail.activity'].sudo().browse(activity_id)
    #     lead_id = int(request.params.get('lead_id', 0))
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     # Security: Only allow if user owns the lead
    #     if activity and lead and lead.user_id.id == user.id and activity.res_model == 'crm.lead' and activity.res_id == lead.id:
    #         try:
    #             activity.action_done()
    #         except Exception:
    #             pass
    #
    #     # Check if request came from modal
    #     referer = request.httprequest.environ.get('HTTP_REFERER', '')
    #     if 'activity_modal' in referer or post.get('from_modal'):
    #         return request.redirect('/my/employee/crm')
    #     else:
    #         return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #
    # @http.route('/my/employee/crm/activity_edit/<int:activity_id>', type='http', auth='user', website=True,
    #             methods=['GET', 'POST'])
    # def portal_employee_crm_activity_edit(self, activity_id, **post):
    #     activity = request.env['mail.activity'].sudo().browse(activity_id)
    #     lead_id = int(request.params.get('lead_id', 0))
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     if not (
    #             activity and lead and lead.user_id.id == user.id and activity.res_model == 'crm.lead' and activity.res_id == lead.id):
    #         return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #     if request.httprequest.method == 'POST':
    #         vals = {}
    #         if post.get('summary') is not None:
    #             vals['summary'] = post.get('summary')
    #         if post.get('date_deadline') is not None:
    #             vals['date_deadline'] = post.get('date_deadline')
    #         if post.get('note') is not None:
    #             vals['note'] = post.get('note')
    #         if post.get('activity_type_id'):
    #             vals['activity_type_id'] = int(post.get('activity_type_id'))
    #         if post.get('user_id'):
    #             vals['user_id'] = int(post.get('user_id'))
    #         if vals:
    #             activity.sudo().write(vals)
    #             # Log in chatter, escape note
    #             activity_type_name = activity.activity_type_id.name or ''
    #             assigned_user = activity.user_id
    #             msg = f"Activity updated: <b>{activity_type_name}</b> - <b>{activity.summary}</b> (Assigned to: {assigned_user.name}, Due: {activity.date_deadline})"
    #             if activity.note:
    #                 msg += f"<br/>Note: {html.escape(activity.note)}"
    #             lead.message_post(body=msg)
    #         return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #     # GET: render a simple edit form (reuse activity_types and salespersons from lead edit)
    #     activity_types = request.env['mail.activity.type'].sudo().search([])
    #     salespersons = request.env['res.users'].sudo().search([('active', '=', True)])
    #     return request.render('employee_self_service_portal.portal_employee_crm_activity_edit', {
    #         'activity': activity,
    #         'lead': lead,
    #         'activity_types': activity_types,
    #         'salespersons': salespersons,
    #     })
    #
    # @http.route('/my/employee/crm/activity_delete/<int:activity_id>', type='http', auth='user', website=True,
    #             methods=['POST'])
    # def portal_employee_crm_activity_delete(self, activity_id, **post):
    #     activity = request.env['mail.activity'].sudo().browse(activity_id)
    #     lead_id = int(request.params.get('lead_id', 0))
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #     if activity and lead and lead.user_id.id == user.id and activity.res_model == 'crm.lead' and activity.res_id == lead.id:
    #         try:
    #             activity_type_name = activity.activity_type_id.name or ''
    #             summary = activity.summary or ''
    #             assigned_user = activity.user_id
    #             due = activity.date_deadline or ''
    #             note = activity.note or ''
    #             msg = f"Activity deleted: <b>{activity_type_name}</b> - <b>{summary}</b> (Assigned to: {assigned_user.name}, Due: {due})"
    #             if note:
    #                 msg += f"<br/>Note: {html.escape(note)}"
    #             activity.sudo().unlink()
    #             lead.message_post(body=msg)
    #         except Exception:
    #             pass
    #
    #     # Check if request came from modal
    #     referer = request.httprequest.environ.get('HTTP_REFERER', '')
    #     if 'activity_modal' in referer or post.get('from_modal'):
    #         return request.redirect('/my/employee/crm')
    #     else:
    #         return request.redirect(f'/my/employee/crm/edit/{lead_id}')
    #
    # @http.route('/my/employee/crm/activity_modal/<int:lead_id>/<string:action>', type='http', auth='user', website=True)
    # def portal_employee_crm_activity_modal(self, lead_id, action, **kwargs):
    #     """Route to handle activity modal content loading"""
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #
    #     # Security check - only allow access to own leads
    #     if not lead or lead.user_id.id != user.id:
    #         return '<div class="alert alert-danger">Access denied</div>'
    #
    #     # Common data for both views
    #     activity_types = request.env['mail.activity.type'].sudo().search([])
    #     default_activity_type_id = request.env.ref('mail.mail_activity_data_todo').id if request.env.ref(
    #         'mail.mail_activity_data_todo', raise_if_not_found=False) else (
    #             activity_types and activity_types[0].id or False)
    #     salespersons = request.env['res.users'].sudo().search([('active', '=', True)])
    #
    #     # Get today's date for comparison
    #     from datetime import date
    #     today = date.today()
    #
    #     context = {
    #         'lead': lead,
    #         'activity_types': activity_types,
    #         'default_activity_type_id': default_activity_type_id,
    #         'salespersons': salespersons,
    #         'today': today,
    #     }
    #
    #     if action == 'view':
    #         return request.render('employee_self_service_portal.portal_employee_crm_activity_modal_view', context)
    #     elif action == 'add':
    #         return request.render('employee_self_service_portal.portal_employee_crm_activity_modal_add', context)
    #     else:
    #         return '<div class="alert alert-danger">Invalid action</div>'

    # @http.route(MY_EMPLOYEE_URL + '/expenses', type='http', auth='user', website=True)
    # @check_portal_access('expenses')
    # def portal_expense_history(self, **kwargs):
    #     employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.uid)], limit=1)
    #     company_id = employee.company_id.id
    #     domain = [('employee_id', '=', employee.id)]
    #     # Filtering logic
    #     status = kwargs.get('status')
    #     if status:
    #         if status == 'withdrawn' or status == 'cancel':
    #             domain += [('sheet_id.state', '=', 'cancel')]
    #         else:
    #             domain += [('sheet_id.state', '=', status)]
    #     category = kwargs.get('category')
    #     if category:
    #         domain += [('product_id', '=', int(category))]
    #     date = kwargs.get('date')
    #     if date:
    #         domain += [('date', '=', date)]
    #     expenses = request.env['hr.expense'].sudo().search(domain, order='date desc')
    #
    #     # Filter categories by the employee's company
    #     categories = request.env['product.product'].sudo().search([
    #         ('can_be_expensed', '=', True),
    #         '|',
    #         ('company_id', '=', False),
    #         ('company_id', '=', company_id)
    #     ])
    #
    #     # Ensure we have access to the company currency
    #     company_currency = employee.company_id.currency_id
    #
    #     return request.render('employee_self_service_portal.portal_expense', {
    #         'expenses': expenses,
    #         'employee': employee,
    #         'categories': categories,
    #         'selected_status': status or '',
    #         'selected_category': category or '',  # Pass as string
    #         'selected_date': date or '',
    #         'company_currency': company_currency,
    #     })
    #
    # @http.route(MY_EMPLOYEE_URL + '/expenses/submit', type='http', auth='user', website=True, methods=['GET', 'POST'])
    # def portal_expense_submit(self, **post):
    #     import logging
    #     import base64
    #     _logger = logging.getLogger(__name__)
    #
    #     employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.uid)], limit=1)
    #     company_id = employee.company_id.id
    #
    #     # Use product_id as category (many2one to product.product, can_be_expensed=True)
    #     # Filter by employee's company
    #     categories = request.env['product.product'].sudo().search([
    #         ('can_be_expensed', '=', True),
    #         '|',
    #         ('company_id', '=', False),
    #         ('company_id', '=', company_id)
    #     ])
    #     errors = []
    #     success = None
    #
    #     if request.httprequest.method == 'POST':
    #         # Enhanced validation
    #         validation_errors = self._validate_expense_data(post)
    #         if validation_errors:
    #             errors.extend(validation_errors)
    #         else:
    #             try:
    #                 # Create expense record
    #                 vals = {
    #                     'name': post.get('name'),
    #                     'date': post.get('date'),
    #                     'employee_id': employee.id,
    #                     'total_amount': float(post.get('total_amount')),
    #                     'product_id': int(post.get('category_id')),
    #                     'description': post.get('notes', ''),
    #                     'company_id': company_id,  # Set the company_id to employee's company
    #                     'currency_id': employee.company_id.currency_id.id,  # Set currency based on employee's company
    #                 }
    #                 expense = request.env['hr.expense'].sudo().create(vals)
    #                 _logger.info("Created expense record with ID: %d", expense.id)
    #
    #                 # Handle file attachment
    #                 attachment = request.httprequest.files.get('attachment')
    #                 if attachment and attachment.filename:
    #                     try:
    #                         attachment_vals = {
    #                             'name': attachment.filename,
    #                             'datas': base64.b64encode(attachment.read()),
    #                             'res_model': 'hr.expense',
    #                             'res_id': expense.id,
    #                             'mimetype': attachment.content_type or 'application/octet-stream',
    #                             'description': 'Expense Receipt',
    #                         }
    #                         attachment_record = request.env['ir.attachment'].sudo().create(attachment_vals)
    #                         _logger.info("Created attachment with ID: %d for expense: %d", attachment_record.id, expense.id)
    #                     except Exception as attachment_error:
    #                         _logger.warning("Failed to save attachment: %s", str(attachment_error))
    #                         errors.append("Attachment could not be saved, but expense was created successfully.")
    #
    #                 # Find or create expense sheet and add expense
    #                 sheet = self._get_or_create_expense_sheet(employee, expense)
    #
    #                 success = 'Expense submitted successfully with receipt.' if attachment else 'Expense submitted successfully.'
    #                 _logger.info("Expense submission completed successfully")
    #
    #             except Exception as e:
    #                 _logger.error("Error creating expense: %s", str(e))
    #                 errors.append('Error submitting expense: %s' % str(e))
    #
    #     # Ensure we have access to the company currency
    #     company_currency = employee.company_id.currency_id
    #
    #     return request.render('employee_self_service_portal.portal_expense_submit', {
    #         'employee': employee,
    #         'categories': categories,
    #         'errors': errors if errors else None,
    #         'success': success,
    #         'company_currency': company_currency,
    #     })
    #
    def _validate_expense_data(self, post):
        """Validate expense submission data"""
        import logging
        _logger = logging.getLogger(__name__)
        errors = []

        # Get employee for company-specific validations
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        currency_symbol = employee.company_id.currency_id.symbol or '$'

        # Required field validation
        required_fields = {
            'name': 'Description',
            'date': 'Date',
            'total_amount': 'Amount',
            'category_id': 'Category'
        }

        for field, label in required_fields.items():
            if not post.get(field):
                errors.append(f'{label} is required.')

        # Amount validation
        try:
            amount = float(post.get('total_amount', 0))
            if amount <= 0:
                errors.append('Amount must be greater than 0.')
            elif amount > 50000:  # Business rule: max expense limit
                errors.append(f'Amount cannot exceed {currency_symbol}50,000.')
        except (ValueError, TypeError):
            errors.append('Amount must be a valid number.')

        # Date validation
        if post.get('date'):
            try:
                from datetime import datetime
                expense_date = datetime.strptime(post.get('date'), '%Y-%m-%d').date()
                today = datetime.now().date()
                if expense_date > today:
                    errors.append('Expense date cannot be in the future.')
            except ValueError:
                errors.append('Invalid date format.')

        # Duplicate expense detection
        if post.get('date') and post.get('total_amount') and post.get('category_id'):
            try:
                employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
                existing_expense = request.env['hr.expense'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('date', '=', post.get('date')),
                    ('total_amount', '=', float(post.get('total_amount'))),
                    ('product_id', '=', int(post.get('category_id'))),
                    ('sheet_id.state', '!=', 'cancel')  # Exclude withdrawn expenses
                ], limit=1)

                if existing_expense:
                    errors.append(
                        'A similar expense already exists for the same date, amount, and category. Please verify this is not a duplicate.')
                    _logger.warning("Potential duplicate expense detected for employee %s", employee.name)

            except Exception as duplicate_check_error:
                _logger.warning("Error checking for duplicate expenses: %s", str(duplicate_check_error))

        # File validation
        attachment = request.httprequest.files.get('attachment')
        if attachment and attachment.filename:
            # Check file size (max 10MB)
            file_content = attachment.read()
            if len(file_content) > 10 * 1024 * 1024:
                errors.append('File size cannot exceed 10MB.')
            attachment.seek(0)  # Reset file pointer

            # Check file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'application/pdf']
            if attachment.content_type not in allowed_types:
                errors.append('Only JPG, PNG, and PDF files are allowed.')

        return errors

    def _get_or_create_expense_sheet(self, employee, expense):
        """Get existing draft sheet or create new one"""
        import logging
        _logger = logging.getLogger(__name__)

        company_id = employee.company_id.id

        # Find existing draft sheet in the same company
        sheet = request.env['hr.expense.sheet'].sudo().search([
            ('employee_id', '=', employee.id),
            ('company_id', '=', company_id),
            ('state', '=', 'draft')
        ], limit=1)

        if not sheet:
            # Create new sheet with company and currency info
            sheet_vals = {
                'name': f'Expense Report - {employee.name}',
                'employee_id': employee.id,
                'expense_line_ids': [(4, expense.id)],
                'company_id': company_id,
                'currency_id': employee.company_id.currency_id.id,
            }
            sheet = request.env['hr.expense.sheet'].sudo().create(sheet_vals)
            _logger.info("Created new expense sheet with ID: %d", sheet.id)
        else:
            # Add expense to existing sheet
            sheet.write({'expense_line_ids': [(4, expense.id)]})
            _logger.info("Added expense to existing sheet ID: %d", sheet.id)

        # Submit the sheet if it has expenses
        if sheet.state == 'draft' and sheet.expense_line_ids:
            try:
                sheet.action_submit_sheet()
                _logger.info("Successfully submitted expense sheet ID: %d", sheet.id)
            except Exception as submit_error:
                _logger.warning("Failed to auto-submit sheet: %s", str(submit_error))

        return sheet

    # @http.route(MY_EMPLOYEE_URL + '/expenses/withdraw/<int:expense_id>', type='http', auth='user', website=True, methods=['POST'])
    # def portal_expense_withdraw(self, expense_id, **post):
    #     import logging
    #     _logger = logging.getLogger(__name__)
    #
    #     expense = request.env['hr.expense'].sudo().browse(expense_id)
    #     employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.uid)], limit=1)
    #
    #     # Only allow withdraw if expense is in submitted state and belongs to the current employee
    #     if expense and expense.employee_id.id == employee.id and expense.sheet_id and expense.sheet_id.state == 'submit':
    #         try:
    #             # Set the report to cancelled (withdraw)
    #             expense.sheet_id.write({'state': 'cancel'})
    #             _logger.info("Successfully withdrew expense ID: %d", expense_id)
    #         except Exception as withdraw_error:
    #             _logger.error("Failed to withdraw expense: %s", str(withdraw_error))
    #
    #     return request.redirect(MY_EMPLOYEE_URL + '/expenses')
    #
    # @http.route(MY_EMPLOYEE_URL + '/expenses/receipt/<int:expense_id>', type='http', auth='user', website=True)
    # def portal_expense_receipt(self, expense_id, **kwargs):
    #     """View expense receipt/attachment"""
    #     import logging
    #     _logger = logging.getLogger(__name__)
    #
    #     expense = request.env['hr.expense'].sudo().browse(expense_id)
    #     employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.uid)], limit=1)
    #
    #     # Security check: only allow viewing own expense receipts
    #     if not expense or expense.employee_id.id != employee.id:
    #         return request.not_found()
    #
    #     # Get the main attachment
    #     attachment = expense.message_main_attachment_id
    #     if not attachment:
    #         # If no main attachment is set, try to find any attachment related to this expense
    #         attachments = request.env['ir.attachment'].sudo().search([
    #             ('res_model', '=', 'hr.expense'),
    #             ('res_id', '=', expense_id)
    #         ], limit=1)
    #
    #         if attachments:
    #             attachment = attachments[0]
    #         else:
    #             return request.not_found()
    #
    #     # Return the attachment data
    #     return request.env['ir.http'].with_context(attachment_token=attachment.access_token)._get_record_and_check(
    #         'ir.attachment', attachment.id
    #     )

    @http.route('/my/employee/form16', type='http', auth='user', website=True)
    def portal_form16(self, **kwargs):
        """Portal route for viewing Form 16 documents - Only for INR employees"""
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)

        if not employee:
            return request.redirect('/my/employee')

        # Only show if employee currency is INR
        if employee.currency_id.name != 'INR':
            return request.redirect('/my/employee')

        selected_year = kwargs.get('financial_year', '')

        domain = [('employee_id', '=', employee.id)]
        if selected_year:
            domain += [('financial_year', '=', selected_year)]

        form16_records = request.env['hr.employee.form16'].sudo().search(
            domain, order='financial_year desc'
        )

        # Get distinct financial years for filter dropdown
        all_years = request.env['hr.employee.form16'].sudo().search([
            ('employee_id', '=', employee.id)
        ], order='financial_year desc').mapped('financial_year')

        return request.render('employee_self_service_portal.portal_form16', {
            'employee': employee,
            'form16_records': form16_records,
            'all_years': all_years,
            'selected_year': selected_year,
        })

    @http.route('/my/employee/form16/download/<int:record_id>', type='http', auth='user', website=True)
    def portal_form16_download(self, record_id, **kwargs):
        """Download Form 16 PDF"""
        employee = request.env['hr.employee'].sudo().search([
            ('user_id', '=', request.env.uid)
        ], limit=1)

        if not employee:
            return request.redirect('/my/employee')

        record = request.env['hr.employee.form16'].sudo().search([
            ('id', '=', record_id),
            ('employee_id', '=', employee.id),  # security: only own records
        ], limit=1)

        if not record or not record.form16_pdf:
            return request.redirect('/my/employee/form16?error=not_found')

        import base64
        pdf_content = base64.b64decode(record.form16_pdf)
        filename = record.form16_filename or f'Form16_{record.financial_year}.pdf'

        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Length', len(pdf_content)),
            ]
        )


    @http.route(MY_EMPLOYEE_URL + '/payslips', type='http', auth='user', website=True)
    @check_portal_access('payslip')
    def portal_payslip_history(self, **kwargs):
        """Portal route for viewing payslip history - Only confirmed payslips"""
        import logging
        _logger = logging.getLogger(__name__)

        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)
        if not employee:
            return request.redirect(MY_EMPLOYEE_URL)

        # Only show confirmed payslips - no status filter needed
        domain = [
            ('employee_id', '=', employee.id),
            ('state', 'in', ['paid'])
        ]

        # Only month/year filtering allowed
        month = kwargs.get('month')
        year = kwargs.get('year')

        # Log filter parameters for debugging
        _logger.info("Payslip filters - month: %s, year: %s", month, year)

        if month and year:
            try:
                # Filter by date range for selected month/year
                from datetime import datetime
                from calendar import monthrange
                start_date = datetime(int(year), int(month), 1)
                end_date = datetime(int(year), int(month), monthrange(int(year), int(month))[1], 23, 59, 59)
                domain += [('date_from', '>=', start_date.strftime('%Y-%m-%d')),
                           ('date_to', '<=', end_date.strftime('%Y-%m-%d'))]
                _logger.info("Date filter applied: %s to %s", start_date.strftime('%Y-%m-%d'),
                             end_date.strftime('%Y-%m-%d'))
            except (ValueError, TypeError) as e:
                _logger.warning("Invalid date filter values - month: %s, year: %s, error: %s", month, year, e)

        _logger.info("Final domain: %s", domain)
        payslips = request.env['hr.payslip'].sudo().search(domain, order='date_from desc, date_to desc')
        _logger.info("Found %d confirmed payslips", len(payslips))

        # For dropdowns - get available years and months from payslips
        from datetime import datetime
        current_year = datetime.now().year
        years = list(range(2026, current_year + 1))
        months = [
            {'value': i, 'name': datetime(2000, i, 1).strftime('%B')} for i in range(1, 13)
        ]

        return request.render('employee_self_service_portal.portal_payslip', {
            'payslips': payslips,
            'employee': employee,
            'years': years,
            'months': months,
            'selected_month': month or '',
            'selected_year': year or '',
        })

    #     @http.route(MY_EMPLOYEE_URL + '/payslips/download/<int:payslip_id>', type='http', auth='user', website=True)
    #     def portal_payslip_download(self, payslip_id, **kwargs):
    #         """Download payslip as PDF"""
    #         import logging
    #         import base64
    #         _logger = logging.getLogger(__name__)

    #         try:
    #             payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
    #             employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)

    #             # Security check - only allow access to own payslips
    #             if not payslip.exists() or not employee or payslip.employee_id.id != employee.id:
    #                 _logger.warning("Unauthorized payslip access attempt by user %s for payslip %s", request.env.uid,
    #                                 payslip_id)
    #                 return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=access_denied')

    #             # Only allow download of confirmed payslips
    #             if payslip.state not in ['validated', 'done', 'paid']:
    #                 _logger.warning("Download attempt for unconfirmed payslip %s by user %s", payslip_id, request.env.uid)
    #                 return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=not_confirmed')

    #             _logger.info("Attempting to download payslip %s for user %s", payslip_id, request.env.uid)

    #             # Try to find the payslip report - multiple approaches with detailed logging
    #             report_ref = None

    #             # Method 1: Try standard hr_payroll reports with sudo()
    #             report_names = [
    #                 'hr_payroll.action_report_payslip',
    #                 'hr_payroll.payslip_report',
    #                 'hr_payroll.report_payslip',
    #                 'hr_payroll.report_payslip_details'
    #             ]

    #             for report_name in report_names:
    #                 try:
    #                     report_ref = request.env.ref(report_name, raise_if_not_found=False)
    #                     if report_ref:
    #                         _logger.info("Found report reference: %s", report_name)
    #                         # Test if we can access this report
    #                         try:
    #                             report_sudo = report_ref.sudo()
    #                             # Try a quick test to see if this report can be used
    #                             if hasattr(report_sudo, 'report_name') or hasattr(report_sudo, '_render_qweb_pdf'):
    #                                 _logger.info("Report %s is accessible and usable", report_name)
    #                                 break
    #                             else:
    #                                 _logger.warning("Report %s found but may not be usable", report_name)
    #                                 report_ref = None
    #                         except Exception as access_test:
    #                             _logger.warning("Report %s access test failed: %s", report_name, str(access_test))
    #                             report_ref = None
    #                             continue
    #                     else:
    #                         _logger.debug("Report %s not found", report_name)
    #                 except Exception as ref_error:
    #                     _logger.debug("Error checking report %s: %s", report_name, str(ref_error))
    #                     continue

    #             # Method 2: Search for payslip reports if standard ones not found
    #             if not report_ref:
    #                 _logger.info("Standard reports not found, searching for any payslip reports...")
    #                 try:
    #                     reports = request.env['ir.actions.report'].sudo().search([
    #                         ('model', '=', 'hr.payslip'),
    #                         ('report_type', '=', 'qweb-pdf')
    #                     ])
    #                     _logger.info("Found %d payslip reports in system", len(reports))

    #                     for report in reports:
    #                         try:
    #                             # Test each report
    #                             _logger.info("Testing report: %s (ID: %d)", report.sudo().name, report.id)
    #                             report_ref = report
    #                             break
    #                         except Exception as test_error:
    #                             _logger.warning("Report test failed: %s", str(test_error))
    #                             continue

    #                 except Exception as search_error:
    #                     _logger.error("Error searching for reports: %s", str(search_error))

    #             if not report_ref:
    #                 _logger.error("No payslip report found for model hr.payslip")
    #                 return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=report_not_found')

    #             # Generate PDF using the found report - use sudo() for report access
    #             _logger.info("Attempting to generate PDF with found report (ID: %d)", report_ref.id)

    #             # Use the correct method based on Odoo version with sudo()
    #             pdf_content = None
    #             try:
    #                 report_sudo = report_ref.sudo()

    #                 # Use the standard Odoo report rendering approach
    #                 _logger.info("Using standard report rendering with payslip ID: %d", payslip.id)

    #                 # Method 1: Try _render_qweb_pdf with proper context and parameters
    #                 try:
    #                     # Use the correct Odoo 18 API for report rendering
    #                     # _render_qweb_pdf expects (report_ref, res_ids, data=None)
    #                     pdf_content, _ = report_sudo._render_qweb_pdf(report_sudo.report_name, payslip.ids)
    #                     _logger.info("Successfully used _render_qweb_pdf method")
    #                 except Exception as method_error:
    #                     _logger.warning("_render_qweb_pdf failed: %s", str(method_error))

    #                     # Method 2: Try with render_qweb_pdf (if available)
    #                     try:
    #                         # Try render_qweb_pdf method
    #                         pdf_content, _ = report_sudo.render_qweb_pdf(payslip.ids)
    #                         _logger.info("Successfully used render_qweb_pdf method")
    #                     except Exception as method_error2:
    #                         _logger.warning("render_qweb_pdf method failed: %s", str(method_error2))

    #                         # Method 3: Try with _render method (with proper parameters)
    #                         try:
    #                             # Use _render with proper report_name and res_ids parameters
    #                             pdf_content, _ = report_sudo._render(report_sudo.report_name, payslip.ids)
    #                             _logger.info("Successfully used _render method")
    #                         except Exception as method_error3:
    #                             _logger.error("All render methods failed: %s", str(method_error3))
    #                             raise Exception("All report render methods failed")

    #                 if pdf_content and len(pdf_content) > 1000:
    #                     _logger.info("Successfully generated PDF using Odoo report, size: %d bytes", len(pdf_content))
    #                 else:
    #                     _logger.warning("PDF content is empty or too small: %s bytes",
    #                                     len(pdf_content) if pdf_content else 0)
    #                     pdf_content = None

    #             except Exception as render_error:
    #                 _logger.error("PDF rendering failed with Odoo report: %s", str(render_error))
    #                 pdf_content = None

    #             # Only use fallback if we couldn't get a valid PDF from Odoo reports
    #             if not pdf_content or len(pdf_content) < 100:
    #                 _logger.warning("Odoo report failed or returned invalid PDF, using fallback method")

    #                 # Fallback: Create a simple HTML-to-PDF conversion
    #                 _logger.info("Attempting simple PDF generation as fallback")
    #                 _logger.info("Attempting simple PDF generation as fallback")
    #                 try:
    #                     # Create simple HTML content
    #                     html_content = f"""
    #                     <!DOCTYPE html>
    #                     <html>
    #                     <head>
    #                         <meta charset="utf-8">
    #                         <title>Payslip {payslip.number or payslip.id}</title>
    #                         <style>
    #                             body {{ font-family: Arial, sans-serif; margin: 20px; }}
    #                             .header {{ text-align: center; margin-bottom: 30px; }}
    #                             .info {{ margin-bottom: 20px; }}
    #                             .line {{ margin: 5px 0; }}
    #                             table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
    #                             th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    #                             th {{ background-color: #f2f2f2; }}
    #                         </style>
    #                     </head>
    #                     <body>
    #                         <div class="header">
    #                             <h1>PAYSLIP</h1>
    #                             <h2>{payslip.number or payslip.id}</h2>
    #                         </div>

    #                         <div class="info">
    #                             <div class="line"><strong>Employee:</strong> {payslip.employee_id.name}</div>
    #                             <div class="line"><strong>Period:</strong> {payslip.date_from} to {payslip.date_to}</div>
    #                             <div class="line"><strong>Status:</strong> {dict(payslip._fields['state'].selection).get(payslip.state, payslip.state)}</div>
    #                         </div>

    #                         <table>
    #                             <thead>
    #                                 <tr>
    #                                     <th>Description</th>
    #                                     <th>Amount</th>
    #                                 </tr>
    #                             </thead>
    #                             <tbody>
    #                     """

    #                     # Add payslip lines
    #                     if payslip.line_ids:
    #                         for line in payslip.line_ids:
    #                             html_content += f"""
    #                                 <tr>
    #                                     <td>{line.name}</td>
    #                                     <td>{line.total:.2f}</td>
    #                                 </tr>
    #                             """
    #                     else:
    #                         html_content += "<tr><td colspan='2'>No payslip details available</td></tr>"

    #                     html_content += """
    #                             </tbody>
    #                         </table>
    #                     </body>
    #                     </html>
    #                     """

    #                     # Use wkhtmltopdf if available, otherwise create simple text-based PDF
    #                     try:
    #                         import subprocess
    #                         import tempfile
    #                         import os

    #                         # Create temporary HTML file
    #                         with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as html_file:
    #                             html_file.write(html_content)
    #                             html_file_path = html_file.name

    #                         # Create temporary PDF file
    #                         pdf_file_path = html_file_path.replace('.html', '.pdf')

    #                         # Try wkhtmltopdf
    #                         result = subprocess.run([
    #                             'wkhtmltopdf', '--page-size', 'A4', '--orientation', 'Portrait',
    #                             html_file_path, pdf_file_path
    #                         ], capture_output=True, timeout=30)

    #                         if result.returncode == 0 and os.path.exists(pdf_file_path):
    #                             with open(pdf_file_path, 'rb') as pdf_file:
    #                                 pdf_content = pdf_file.read()
    #                             _logger.info("Successfully created PDF using wkhtmltopdf")
    #                         else:
    #                             raise Exception("wkhtmltopdf failed")

    #                         # Cleanup
    #                         os.unlink(html_file_path)
    #                         os.unlink(pdf_file_path)

    #                     except Exception:
    #                         # Final fallback: Create a very simple text-based response
    #                         _logger.warning("wkhtmltopdf not available, creating simple text response")
    #                         simple_content = f"""
    # PAYSLIP: {payslip.number or payslip.id}
    # Employee: {payslip.employee_id.name}
    # Period: {payslip.date_from} to {payslip.date_to}
    # Status: {dict(payslip._fields['state'].selection).get(payslip.state, payslip.state)}

    # Payslip Details:
    # """
    #                         if payslip.line_ids:
    #                             for line in payslip.line_ids:
    #                                 simple_content += f"{line.name}: {line.total:.2f}\n"
    #                         else:
    #                             simple_content += "No payslip details available\n"

    #                         # Return as text file instead of PDF
    #                         safe_number = (payslip.number or str(payslip.id)).replace('/', '_').replace('\\', '_')
    #                         safe_date = payslip.date_from.strftime('%Y-%m') if payslip.date_from else 'unknown'
    #                         filename = f"Payslip_{safe_number}_{safe_date}.txt"

    #                         headers = [
    #                             ('Content-Type', 'text/plain'),
    #                             ('Content-Length', len(simple_content.encode('utf-8'))),
    #                             ('Content-Disposition', f'attachment; filename="{filename}"'),
    #                             ('Cache-Control', 'no-cache'),
    #                             ('Pragma', 'no-cache')
    #                         ]

    #                         _logger.info("Payslip %s downloaded as text file by user %s", payslip_id, request.env.uid)
    #                         return request.make_response(simple_content.encode('utf-8'), headers=headers)

    #                 except Exception as fallback_error:
    #                     _logger.error("Fallback PDF generation also failed: %s", str(fallback_error))
    #                     return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=render_failed')

    #             if not pdf_content:
    #                 _logger.error("All PDF generation methods failed - no content generated")
    #                 return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=empty_pdf')

    #             # Log which method was used
    #             if len(pdf_content) > 1000:
    #                 _logger.info("Successfully generated PDF - likely from Odoo report system (%d bytes)", len(pdf_content))
    #             else:
    #                 _logger.info("Generated small PDF - likely from fallback method (%d bytes)", len(pdf_content))

    #             # Create safe filename
    #             safe_number = (payslip.name or str(payslip.id)).replace('/', '_').replace('\\', '_')
    #             safe_date = payslip.date_from.strftime('%Y-%m') if payslip.date_from else 'unknown'
    #             filename = f"Payslip_{safe_number}_{safe_date}.pdf"

    #             # Create response with PDF
    #             pdfhttpheaders = [
    #                 ('Content-Type', 'application/pdf'),
    #                 ('Content-Length', len(pdf_content)),
    #                 ('Content-Disposition', f'attachment; filename="{filename}"'),
    #                 ('Cache-Control', 'no-cache'),
    #                 ('Pragma', 'no-cache')
    #             ]

    #             _logger.info("Payslip %s downloaded successfully by user %s, file size: %d bytes",
    #                          payslip_id, request.env.uid, len(pdf_content))

    #             return request.make_response(pdf_content, headers=pdfhttpheaders)

    #         except Exception as e:
    #             _logger.error("Unexpected error in payslip download for payslip %s: %s", payslip_id, str(e))
    #             import traceback
    #             _logger.error("Full traceback: %s", traceback.format_exc())
    #             return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=download_failed')

    @http.route(MY_EMPLOYEE_URL + '/payslips/download/<int:payslip_id>', type='http', auth='user', website=True)
    def portal_payslip_download(self, payslip_id, **kwargs):
        """Download payslip as PDF"""
        import logging
        import base64
        _logger = logging.getLogger(__name__)

        try:
            payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
            employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.uid)], limit=1)

            # Security check
            if not payslip.exists() or not employee or payslip.employee_id.id != employee.id:
                _logger.warning("Unauthorized payslip access attempt by user %s for payslip %s", request.uid,
                                payslip_id)
                return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=access_denied')

            if payslip.state not in ['validated', 'done', 'paid']:
                return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=not_confirmed')

            report_ref = None

            report_names = [
                'hr_payroll.action_report_payslip',
                'hr_payroll.payslip_report',
                'hr_payroll.report_payslip',
                'hr_payroll.report_payslip_details'
            ]

            for report_name in report_names:
                report_ref = request.env.ref(report_name, raise_if_not_found=False)
                if report_ref:
                    break

            if not report_ref:
                reports = request.env['ir.actions.report'].sudo().search([
                    ('model', '=', 'hr.payslip'),
                    ('report_type', '=', 'qweb-pdf')
                ])
                report_ref = reports[:1]

            if not report_ref:
                return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=report_not_found')

            pdf_content = None

            try:
                report_sudo = report_ref.sudo()
                pdf_content, _ = report_sudo._render_qweb_pdf(report_sudo.report_name, payslip.ids)
            except Exception:
                try:
                    pdf_content, _ = report_sudo.render_qweb_pdf(payslip.ids)
                except Exception:
                    pdf_content = None

            if not pdf_content:
                return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=render_failed')

            # ================= PASSWORD PROTECTION ADDED HERE =================
            try:

                password = None
                if payslip.employee_id.birthday:
                    password = payslip.employee_id.birthday.strftime("%d%m%Y")

                if password:
                    pdf_stream = io.BytesIO(pdf_content)
                    output_stream = io.BytesIO()

                    with pikepdf.open(pdf_stream) as pdf:
                        pdf.save(
                            output_stream,
                            encryption=pikepdf.Encryption(
                                user=password,
                                owner=password,
                                R=4
                            )
                        )

                    pdf_content = output_stream.getvalue()

            except Exception as enc_error:
                _logger.error("PDF encryption failed: %s", str(enc_error))
            # =================================================================

            safe_number = (payslip.name or str(payslip.id)).replace('/', '_').replace('\\', '_')
            safe_date = payslip.date_from.strftime('%Y-%m') if payslip.date_from else 'unknown'
            filename = f"{payslip.employee_id.name} - {payslip.date_from.strftime('%B %Y')}.pdf"

            pdfhttpheaders = [
                ('Content-Type', 'application/pdf'),
                ('Content-Length', len(pdf_content)),
                ('Content-Disposition', f'attachment; filename="{filename}"'),
            ]

            return request.make_response(pdf_content, headers=pdfhttpheaders)

        except Exception as e:
            import traceback
            _logger.error("Error: %s", traceback.format_exc())
            return request.redirect(MY_EMPLOYEE_URL + '/payslips?error=download_failed')

    @http.route(MY_EMPLOYEE_URL + '/payslips/view/<int:payslip_id>', type='http', auth='user', website=True)
    def portal_payslip_view(self, payslip_id, **kwargs):
        """View payslip details"""
        payslip = request.env['hr.payslip'].sudo().browse(payslip_id)
        employee = request.env[HR_EMPLOYEE_MODEL].sudo().search([('user_id', '=', request.env.uid)], limit=1)

        # Security check - only allow access to own payslips
        if not payslip or not employee or payslip.employee_id.id != employee.id:
            return request.redirect(MY_EMPLOYEE_URL + '/payslips')

        return request.render('employee_self_service_portal.portal_payslip_view', {
            'payslip': payslip,
            'employee': employee,
        })

    # @http.route('/my/employee/crm/update_stage/<int:lead_id>', type='http', auth='user', website=True, methods=['POST'],
    #             csrf=True)
    # def portal_employee_crm_update_stage(self, lead_id, **post):
    #     """Route to handle stage updates via AJAX"""
    #     import json
    #
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #
    #     # Security check - only allow access to own leads
    #     if not lead or lead.user_id.id != user.id:
    #         response = json.dumps({'success': False, 'error': 'Access denied'})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #     stage_id = post.get('stage_id')
    #     if not stage_id:
    #         response = json.dumps({'success': False, 'error': 'Stage ID is required'})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #     try:
    #         stage_id = int(stage_id)
    #         stage = request.env['crm.stage'].sudo().browse(stage_id)
    #         if not stage.exists():
    #             response = json.dumps({'success': False, 'error': 'Invalid stage'})
    #             return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #         lead.write({'stage_id': stage_id})
    #         response = json.dumps({'success': True, 'stage_name': stage.name})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #     except Exception as e:
    #         _logger.error("Error updating lead stage: %s", str(e))
    #         response = json.dumps({'success': False, 'error': 'Update failed'})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})

    # @http.route('/my/employee/crm/api/kpis', type='http', auth='user', website=True, methods=['GET'], csrf=False)
    # def portal_employee_crm_api_kpis(self, **kwargs):
    #     """API endpoint to get dashboard KPIs"""
    #     import json
    #     from datetime import date
    #
    #     user = request.env.user
    #
    #     try:
    #         # Get all user leads
    #         all_user_leads = request.env['crm.lead'].sudo().search([('user_id', '=', user.id)])
    #         today = date.today()
    #
    #         # Calculate KPIs
    #         kpis = self._calculate_dashboard_kpis(all_user_leads, today)
    #
    #         response = json.dumps({'success': True, 'kpis': kpis})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #     except Exception as e:
    #         _logger.error("Error fetching KPIs: %s", str(e))
    #         response = json.dumps({'success': False, 'error': 'Failed to fetch KPIs'})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    # @http.route('/my/employee/crm/api/quick_action', type='http', auth='user', website=True, methods=['POST'],
    #             csrf=True)
    # def portal_employee_crm_quick_action(self, **post):
    #     """API endpoint for quick actions on leads"""
    #     import json
    #
    #     user = request.env.user
    #     action = post.get('action')
    #     lead_id = post.get('lead_id')
    #
    #     try:
    #         lead_id = int(lead_id)
    #         lead = request.env['crm.lead'].sudo().browse(lead_id)
    #
    #         # Security check
    #         if not lead or lead.user_id.id != user.id:
    #             response = json.dumps({'success': False, 'error': 'Access denied'})
    #             return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #         if action == 'mark_won':
    #             # Find "Won" stage
    #             won_stage = request.env['crm.stage'].sudo().search([('name', '=ilike', 'won')], limit=1)
    #             if won_stage:
    #                 lead.write({'stage_id': won_stage.id})
    #                 response = json.dumps({'success': True, 'message': 'Lead marked as won'})
    #             else:
    #                 response = json.dumps({'success': False, 'error': 'Won stage not found'})
    #
    #         elif action == 'mark_lost':
    #             # Find "Lost" stage or set as lost
    #             lost_stage = request.env['crm.stage'].sudo().search([('name', '=ilike', 'lost')], limit=1)
    #             if lost_stage:
    #                 lead.write({'stage_id': lost_stage.id})
    #             else:
    #                 # Use Odoo's built-in lost functionality
    #                 lead.write({'active': False})
    #             response = json.dumps({'success': True, 'message': 'Lead marked as lost'})
    #
    #         elif action == 'schedule_call':
    #             # Create a call activity
    #             activity_type = request.env['mail.activity.type'].sudo().search([('name', '=ilike', 'call')], limit=1)
    #             if not activity_type:
    #                 activity_type = request.env['mail.activity.type'].sudo().search([], limit=1)
    #
    #             if activity_type:
    #                 from datetime import date, timedelta
    #                 request.env['mail.activity'].sudo().create({
    #                     'res_id': lead.id,
    #                     'res_model_id': request.env['ir.model']._get('crm.lead').id,
    #                     'activity_type_id': activity_type.id,
    #                     'summary': 'Scheduled Call',
    #                     'date_deadline': date.today() + timedelta(days=1),
    #                     'user_id': user.id,
    #                 })
    #                 response = json.dumps({'success': True, 'message': 'Call scheduled for tomorrow'})
    #             else:
    #                 response = json.dumps({'success': False, 'error': 'Could not create activity'})
    #
    #         elif action == 'add_note':
    #             note_content = post.get('note_content', '')
    #             if note_content:
    #                 lead.message_post(body=note_content, message_type='comment')
    #                 response = json.dumps({'success': True, 'message': 'Note added'})
    #             else:
    #                 response = json.dumps({'success': False, 'error': 'Note content required'})
    #
    #         else:
    #             response = json.dumps({'success': False, 'error': 'Unknown action'})
    #
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    #     except Exception as e:
    #         _logger.error("Error in quick action: %s", str(e))
    #         response = json.dumps({'success': False, 'error': 'Action failed'})
    #         return request.make_response(response, headers={'Content-Type': 'application/json'})
    #
    # @http.route('/my/employee/crm/notes_modal/<int:lead_id>', type='http', auth='user', website=True)
    # def portal_employee_crm_notes_modal(self, lead_id, **kwargs):
    #     """Route to handle notes modal content loading"""
    #     lead = request.env['crm.lead'].sudo().browse(lead_id)
    #     user = request.env.user
    #
    #     # Security check - only allow access to own leads
    #     if not lead or lead.user_id.id != user.id:
    #         return '<div class="alert alert-danger">Access denied</div>'
    #
    #     # Get all log notes for this lead
    #     notes = request.env['mail.message'].sudo().search([
    #         ('model', '=', 'crm.lead'),
    #         ('res_id', '=', lead_id),
    #         ('message_type', '=', 'comment'),
    #         ('subtype_id', '=', request.env.ref('mail.mt_note').id)
    #     ], order='date desc')
    #
    #     context = {
    #         'lead': lead,
    #         'notes': notes,
    #     }
    #
    #     return request.render('employee_self_service_portal.portal_employee_crm_notes_modal', context)