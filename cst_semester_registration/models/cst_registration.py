from odoo import api, fields, models
from odoo.exceptions import ValidationError


class Registration(models.Model):
    _name = "cst.registration"
    _description = "Student Registration"

    register_id = fields.Many2one(
        "cst.registration.register", string="Registration Register", required=True
    )
    student_id = fields.Many2one("op.student", string="Student", required=True)
    course_id = fields.Many2one(
        "op.course",
        string="Course",
        compute="compute_programme",
        store=True,
        readonly=True,
    )
    term_id = fields.Many2one(
        "op.academic.term",
        string="Semester",
        related="register_id.term_id",
        store=True,
        readonly=True,
    )
    batch_id = fields.Many2one(
        "op.batch",
        string="Batch",
        related="register_id.batch_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [
            ("registered", "Registered"),
            ("pending", "Pending"),
            ("invoiced", "Invoiced"),  # Added invoiced state
        ],
        string="Status",
        default="registered",
        tracking=True,
    )

    subject_registration_ids = fields.One2many(
        "student.subject.registration",
        "registration_id",
        string="Subjects",
        ondelete="cascade",
    )

    attachment_filename = fields.Char(string="Filename")
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain="[('move_type', '=', 'out_invoice')]",
        readonly=True,
        help="The invoice generated for this registration",
    )
    invoice_count = fields.Integer(compute="_compute_invoice_count")

    # COmpute Methods
    @api.depends("student_id")
    def compute_programme(self):
        for rec in self:
            if rec.student_id:
                rec.course_id = rec.student_id.course_id
            else:
                rec.course_id = False

    # Invoice methods (same as REEvalApplication)
    @api.depends("invoice_id")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0

    def get_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            return  # No invoice to show

        return {
            "type": "ir.actions.act_window",
            "name": "Invoice",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "=", self.invoice_id.id)],
            "target": "current",
        }

    # Existing constraints (unchanged)
    def _check_repeat_subjects(self):
        for record in self:
            repeat_count = len(
                record.subject_registration_ids.filtered(
                    lambda r: r.registration_type == "repeat"
                )
            )
            if repeat_count > 2:
                raise ValidationError(
                    "Maximum 2 repeat modules allowed per registration"
                )

    _constraints = [
        (
            _check_repeat_subjects,
            "Maximum 2 repeat modules allowed",
            ["subject_registration_ids"],
        )
    ]

    _sql_constraints = [
        (
            "unique_student_registration",
            "unique(student_id, register_id)",
            "Student is already registered!",
        )
    ]
