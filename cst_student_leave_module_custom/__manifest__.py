{
    "name": "CST Student Leave Management",
    "version": "18.0.0.0",
    "license": "LGPL-3",
    "category": "Education",
    "sequence": 1,
    "summary": "Customizing Time off Module to allow students to take leave too",
    "author": "Jigme Phuntsho Wangyel",
    "website": "https://www.1.1.1.1.core",
    "depends": ["hr_holidays", "openeducat_core", "base", "website"],
    "data": [
        # SECURITY
        "security/groups.xml",
        "security/record_rule.xml",
        "security/ir.model.access.csv",
        # Data Files
        "data/mail_template_data.xml",
        # VIEWS
        "views/view_student_leave.xml",
        "views/student_leave_inherit.xml",
        "views/student_leave_type.xml",
        "views/templates/student_leave_template.xml",
        "views/templates/access_denied_template.xml",
        "views/templates/portal.xml",
        "views/menu.xml",
    ],
    "demo": [],
    "installable": True,
    "auto_install": False,
    "application": True,
}
