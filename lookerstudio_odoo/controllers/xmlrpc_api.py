import json
import logging
import datetime
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

# Standard headers for JSON response with no caching
headers = [('Content-Type', 'application/json'), ('Cache-Control', 'no-store')]

class MyRestController(http.Controller):
    def _parse_auth_header(self):
        """
        Parse the Authorization header, expected format: "login:apikey".
        Returns login and API key strings, or (None, None) if invalid.
        """
        auth = request.httprequest.headers.get('Authorization')
        if not auth:
            return None, None

        # Expect the format "login:apikey"
        if ':' not in auth:
            return None, None
        login, api_key = auth.split(':', 1)

        return login.strip(), api_key.strip()

    def _authenticate_with_api_key(self):
        """
        Authenticate user based on Authorization header credentials.
        Returns user record or None if authentication fails.
        """
        login, api_key = self._parse_auth_header()
        if not login or not api_key:
            return None

        # Find user by login
        user = request.env['res.users'].sudo().search([('login', '=', login)], limit=1)
        if not user:
            _logger.warning(f"Authentication failed: user '{login}' not found")
            return None

        try:
            # Validate API key for 'rpc' scope; returns user ID if valid
            uid = request.env['res.users.apikeys']._check_credentials(scope='rpc', key=api_key)
        except Exception as e:
            _logger.warning(f"API key check error for user '{login}': {e}")
            return None

        if not uid:
            _logger.warning(f"Authentication failed: invalid API key for user '{login}'")
            return None

        return user

    @http.route('/partners', auth='none', type='http', csrf=False, cors="*", methods=['GET', 'POST'])
    def get_partners(self, **kw):
        """
        HTTP endpoint to execute a SELECT query from 'ApiQuery' header.
        Requires valid API key auth. Returns query results as JSON.
        """
        # Authenticate request
        user = self._authenticate_with_api_key()
        if not user:
            return Response(
                json.dumps({"error": "Unauthorized"}),
                status=401,
                content_type='application/json'
            )

        # Retrieve SQL query string from custom header
        query = request.httprequest.headers.get('ApiQuery')
        if not query:
            return Response(
                json.dumps({"error": "No query provided"}),
                status=400,
                content_type='application/json'
            )

        # Only allow SELECT queries to avoid dangerous operations
        stripped_query = query.strip().lower()
        if not stripped_query.startswith("select"):
            return Response(
                json.dumps({"error": "Query blocked: only SELECT allowed"}),
                status=403,
                content_type='application/json'
            )

        try:
            # Execute the SQL query
            request.env.cr.execute(query)
            rows = request.env.cr.fetchall()

            # Extract column names from cursor metadata
            columns = [desc[0] for desc in request.env.cr.description]

            # Convert rows to list of dicts, handling datetime serialization
            result = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    if isinstance(val, (datetime.datetime, datetime.date)):
                        row_dict[col] = val.isoformat()
                    else:
                        row_dict[col] = val
                result.append(row_dict)

        except Exception as e:
            _logger.error(f"Query execution failed: {e}", exc_info=True)
            return Response(
                json.dumps({"error": "Query execution failed", "details": str(e)}),
                status=400,
                content_type='application/json'
            )

        # Return results as formatted JSON response with appropriate headers
        return Response(
            json.dumps(result, indent=2),
            status=200,
            headers=headers
        )
