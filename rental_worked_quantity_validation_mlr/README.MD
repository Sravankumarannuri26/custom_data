
# Rental Worked Quantity Validation

This Odoo module ensures that users cannot manually enter a **Worked Quantity** greater than the **Planned Quantity** in the `rental.invoice.history` model. It is designed to support rental management workflows by enforcing accurate data entry and preventing over-reporting.

## 📦 Module Name
`rental_worked_quantity_validation`

## 🧩 Dependencies
This module depends on:

- `base`
- `sale_rental`
- `techcarrot_rental` (must define the model `rental.invoice.history`)

Ensure the `techcarrot_rental` module is installed and available in the system before installing this module.

## 🧾 Features

- Adds a validation constraint to the `worked_days` field in `rental.invoice.history`.
- Prevents saving a record if `worked_days > planned_days`.
- Displays a clear validation error to the user in case of violation.
- Helps maintain data integrity in rental invoice tracking.

## 🛠️ Technical Details

### Model:
- `rental.invoice.history`

### Validation Logic:
```python
@api.constrains('worked_days')
def _check_worked_days(self):
    for rec in self:
        if rec.planned_days and rec.worked_days and rec.worked_days > rec.planned_days:
            raise ValidationError(_("Worked Qty cannot exceed Planned Qty."))
````


```

## 🧪 Testing

Test scenarios:

1. Set `planned_days = 22.0`
2. Try to enter `worked_days = 25.0` → ✅ Validation error expected
3. Try to enter `worked_days = 22.0` → ✅ Save should succeed

## 📝 Changelog

### v1.0.0 – Initial Release

* Added validation constraint on `worked_days`
* Ensured compatibility with `techcarrot_rental`

## 📌 Notes

If you encounter a `Model 'rental.invoice.history' does not exist in registry.` error:

* Ensure the `techcarrot_rental` module is installed and loaded before this module.
* Rebuild Odoo if working with Odoo.sh, and monitor logs for model resolution issues.

## 👨‍💻 Maintainer

Developed and maintained by Lovaraju Mylapalli - Techcarrot Team.

For support, contact: `lovaraju.mylapalli@techcarrot.ae`

```
