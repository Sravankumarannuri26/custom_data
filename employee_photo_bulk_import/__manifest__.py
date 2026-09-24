{
    "name": "Employee Photo Bulk Import",
    "version": "19.0.1.0.0",
    "summary": "Bulk upload employee photos from a zip file, matched by Emp Code",
    "category": "Human Resources",
    "author": "TechCarrot",
    "depends": ["hr"],
    "data": [
        "security/ir.model.access.csv",
        "views/photo_bulk_import_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
