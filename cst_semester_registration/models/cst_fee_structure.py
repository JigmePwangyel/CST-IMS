from odoo import api, fields, models


class FeeStructure(models.Model):
    _name = "cst.fee.structure"
    _description = "Fee Structure"

    name = fields.Char("Name of fee", required=True)
    fee_type = fields.Selection(
        [
            ("gov", "Government Scholarship"),
            ("self", "Self-Finance"),
            ("other", "Other-Scholarship"),
            ("repeat_module_fee", "Repeat-Module-Fee"),
            ("back_paper", "Backpaper Fee"),
            ("re_eval", "Re Evaluation Fee"),
            ("re_check", "Re Check Fee"),
        ],
        string="Fee Type",
        required=True,
    )

    fee_component_ids = fields.Many2many(
        "product.product",
        "cst_fee_structure_product_rel",
        "fee_structure_id",
        "product_id",
        string="Fee Components",
    )

    is_active = fields.Boolean(
        default=False, help="Mark whether this fee structure is active or not"
    )
