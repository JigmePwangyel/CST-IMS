from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class Scholarship(models.Model):
    _name = "cst.scholarship"
    _description = "Scholarship Types"

    name = fields.Char(string="Name", required=True)
    category = fields.Selection(
        [("gov", "Governement Funding"), ("self", "Self Funding"), ("other", "Other")],
        string="Category",
        default="other",
    )
