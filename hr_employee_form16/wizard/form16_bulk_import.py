import base64
import zipfile
import io
from odoo import models, fields


class Form16BulkImport(models.TransientModel):
    _name = 'form16.bulk.import.wizard'
    _description = 'Bulk Import Form 16 PDFs'

    zip_file = fields.Binary(string='ZIP File', required=True)
    zip_filename = fields.Char()
    log = fields.Text(readonly=True)

    def action_import(self):
        self.ensure_one()
        zip_data = base64.b64decode(self.zip_file)
        results = []
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            for filename in zf.namelist():
                if not filename.lower().endswith('.pdf'):
                    continue
                base = filename.rsplit('/', 1)[-1].rsplit('.', 1)[0]
                try:
                    emp_code, fy = base.split('_', 1)
                except ValueError:
                    results.append(f"SKIPPED {filename}: bad naming format")
                    continue

                employee = self.env['hr.employee'].search([
                    ('emp_code', '=', emp_code),
                    ('currency_id.name', '=', 'INR'),
                ], limit=1)

                if not employee:
                    results.append(f"NOT FOUND: employee code {emp_code} ({filename})")
                    continue

                pdf_content = zf.read(filename)
                existing = self.env['hr.employee.form16'].search([
                    ('employee_id', '=', employee.id),
                    ('financial_year', '=', fy),
                ], limit=1)

                vals = {
                    'employee_id': employee.id,
                    'financial_year': fy,
                    'form16_pdf': base64.b64encode(pdf_content),
                    'form16_filename': filename.rsplit('/', 1)[-1],
                }
                if existing:
                    existing.write(vals)
                    results.append(f"UPDATED: {employee.name} - {fy}")
                else:
                    self.env['hr.employee.form16'].create(vals)
                    results.append(f"CREATED: {employee.name} - {fy}")

        self.log = "\n".join(results)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'form16.bulk.import.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
