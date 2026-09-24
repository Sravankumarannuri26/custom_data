import requests
import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class HRDepartment(models.Model):
    _inherit = 'hr.department'

    azure_dl_email = fields.Char("DL Email", readonly=True)
    azure_dl_id = fields.Char("DL ID", readonly=True)

    def action_sync_dl_from_azure(self):
        """Find and link existing DL from Azure based on department name"""
        self.ensure_one()

        params = self.env['ir.config_parameter'].sudo()
        tenant = params.get_param("azure_tenant_id")
        client = params.get_param("azure_client_id")
        secret = params.get_param("azure_client_secret")
        domain = params.get_param("azure_domain")

        if not all([tenant, client, secret, domain]):
            _logger.error(" Azure credentials missing")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': 'Azure credentials missing in System Parameters',
                    'type': 'danger',
                }
            }

        try:
            # Get token
            token_resp = requests.post(
                f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": client,
                    "client_secret": secret,
                    "scope": "https://graph.microsoft.com/.default"
                },
                timeout=30
            ).json()

            token = token_resp.get("access_token")
            if not token:
                _logger.error("Failed to get token")
                return

            headers = {"Authorization": f"Bearer {token}"}

            # MODIFIED: Try both uppercase and lowercase versions
            dept_name_upper = self.name.replace(' ', '_').replace('&', 'and')
            dept_name_lower = self.name.lower().replace(' ', '_').replace('&', 'and')

            # Try uppercase first (DL_Test)
            expected_dl_email = f"DL_{dept_name_upper}@{domain}"

            _logger.info(f" Searching for: {expected_dl_email}")

            # Search for group by email
            search_url = f"https://graph.microsoft.com/v1.0/groups?$filter=mail eq '{expected_dl_email}'"
            response = requests.get(search_url, headers=headers, timeout=30)

            groups = []
            if response.status_code == 200:
                groups = response.json().get('value', [])

            # MODIFIED: If not found with uppercase, try lowercase (DL_test)
            if not groups and dept_name_upper != dept_name_lower:
                expected_dl_email = f"DL_{dept_name_lower}@{domain}"
                _logger.info(f" Trying lowercase: {expected_dl_email}")

                search_url = f"https://graph.microsoft.com/v1.0/groups?$filter=mail eq '{expected_dl_email}'"
                response = requests.get(search_url, headers=headers, timeout=30)

                if response.status_code == 200:
                    groups = response.json().get('value', [])

            # MODIFIED: Updated error messages
            if groups:
                group = groups[0]
                self.write({
                    'azure_dl_email': group.get('mail'),
                    'azure_dl_id': group.get('id')
                })
                _logger.info(f" Linked: {self.name} → {group.get('mail')}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f" Linked to {group.get('mail')}",
                        'type': 'success',
                    }
                }
            else:
                _logger.warning(f" DL not found: DL_{dept_name_upper} or DL_{dept_name_lower}")
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'message': f" DL not found. Tried: DL_{dept_name_upper}@{domain} and DL_{dept_name_lower}@{domain}",
                        'type': 'warning',
                    }
                }

        except Exception as e:
            _logger.error(f" Error: {e}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': f'Error: {str(e)}',
                    'type': 'danger',
                }

            }
