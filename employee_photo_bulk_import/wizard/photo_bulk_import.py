import base64
import io
import logging
import zipfile

from odoo import fields, models

_logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".gif")


class EmployeePhotoBulkImport(models.TransientModel):
    _name = "employee.photo.bulk.import"
    _description = "Bulk Import Employee Photos"

    # Multiple zip files can be uploaded at once (e.g. batch_1.zip, batch_2.zip, ...)
    zip_files = fields.Many2many(
        "ir.attachment",
        string="Photos ZIP File(s)",
        help="You can select multiple zip files at once. Each zip must be "
             "small enough for your server's upload limit - if uploads keep "
             "failing with a 'Request Entity Too Large' error, split your "
             "photos into smaller zip batches first.",
    )

    match_field = fields.Char(
        string="Employee Matching Field (technical name)",
        default="emp_code",
        required=True,
        help=(
            "The technical field name on hr.employee that holds the Emp "
            "Code (e.g. emp_code, identification_id, or barcode). Each "
            "photo file inside the zip must be named exactly as this "
            "value, e.g. T1034.jpg"
        ),
    )

    result_log = fields.Text(string="Result", readonly=True)

    def action_import_photos(self):
        self.ensure_one()
        Employee = self.env["hr.employee"]

        if not self.zip_files:
            self.result_log = "ERROR: Please upload at least one zip file."
            return self._reopen_wizard()

        if self.match_field not in Employee._fields:
            self.result_log = (
                "ERROR: '%s' is not a valid field on hr.employee. "
                "Check Settings > Technical > Database Structure > Models "
                "to find the correct technical field name." % self.match_field
            )
            return self._reopen_wizard()

        updated, skipped, not_found, bad_zips = [], [], [], []

        for attachment in self.zip_files:
            zip_bytes = base64.b64decode(attachment.datas)

            try:
                zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
            except zipfile.BadZipFile:
                bad_zips.append(attachment.name)
                continue

            for name in zf.namelist():
                if name.endswith("/") or "/__MACOSX" in name:
                    continue
                base_name = name.split("/")[-1]
                lower_name = base_name.lower()
                if not lower_name.endswith(IMAGE_EXTENSIONS):
                    continue

                emp_code = base_name.rsplit(".", 1)[0].strip()
                if not emp_code:
                    continue

                try:
                    file_bytes = zf.read(name)
                    b64_data = base64.b64encode(file_bytes).decode("utf-8")
                except Exception as e:
                    skipped.append("%s (read error: %s)" % (base_name, e))
                    continue

                employees = Employee.search([(self.match_field, "=", emp_code)])

                if not employees:
                    not_found.append(emp_code)
                    continue

                employees.write({"image_1920": b64_data})
                updated.append("%s -> %s" % (emp_code, ", ".join(employees.mapped("name"))))

        log_lines = []
        log_lines.append("Zip files processed: %d" % len(self.zip_files))
        log_lines.append("Updated: %d" % len(updated))
        log_lines.append("Not matched in Odoo: %d" % len(not_found))
        if skipped:
            log_lines.append("Skipped (errors): %d" % len(skipped))
        if bad_zips:
            log_lines.append("Invalid zip files: %d" % len(bad_zips))
        log_lines.append("")
        if updated:
            log_lines.append("--- Updated ---")
            log_lines.extend(updated)
        if not_found:
            log_lines.append("")
            log_lines.append("--- No employee found for these Emp Codes ---")
            log_lines.extend(not_found)
        if skipped:
            log_lines.append("")
            log_lines.append("--- Skipped ---")
            log_lines.extend(skipped)
        if bad_zips:
            log_lines.append("")
            log_lines.append("--- Invalid zip files (could not open) ---")
            log_lines.extend(bad_zips)

        self.result_log = "\n".join(log_lines)
        return self._reopen_wizard()

    def _reopen_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "employee.photo.bulk.import",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }
