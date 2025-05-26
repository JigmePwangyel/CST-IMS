import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)  # Create a logger


class ReEvalRegistar(models.Model):
    _name = "cst.exam.re.eval.registar"
    _description = "RE Check Re Eval Register Model"

    name = fields.Char(string="Register Name", store=True, required=True)
    type = fields.Selection(
        [
            ("recheck", "Re-Check"),
            ("reevaluation", "Re-Evaluation"),
        ],
        string="Type of Registar",
        store=True,
    )
    start_date = fields.Datetime(
        "Start Date",
        required=True,
        tracking=True,
        default=lambda self: date.today(),
    )
    end_date = fields.Datetime(
        "End Date",
        required=True,
        tracking=True,
        default=lambda self: date.today(),
    )
    term_id = fields.Many2one(
        "op.academic.term",
        string="Academic Term",
        required=True,
        tracking=True,
    )
    is_published = fields.Boolean(default=False, store=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("application", "Application Gathering"),
            ("done", "Done"),
        ],
        string="State",
        store=True,
        default="draft",
        tracking=True,
        compute="_auto_update_state_done",
    )
    application_count = fields.Integer(compute="compute_application_count", default=0)
    duration_days = fields.Integer(
        compute="compute_duration", string="Duration in Days"
    )

    # Actions
    def action_confirm(self):
        for rec in self:
            rec.state = "confirmed"

    def action_gather_application(self):
        for rec in self:
            rec.state = "application"
            rec.is_published = True

    def action_done(self):
        for rec in self:
            rec.state = "done"
            rec.is_published = False

    def action_reset(self):
        for rec in self:
            rec.state = "draft"
            rec.is_published = False

    def website_publish_button(self):
        for record in self:
            if record.state != "application":
                raise ValidationError(
                    "To publish to website, the state should be in application gathering"
                )
            else:
                record.is_published = not record.is_published

    # NOTE Need to change
    def get_request(self):
        self.ensure_one()
        action = self.env.ref(
            "cst_result_processing_module_custom.action_open_re_eval_application"
        )
        action = action.read()[0]
        action["domain"] = [("re_eval_registar_id", "=", self.id)]
        return action

    @api.depends("end_date", "state")
    def _auto_update_state_done(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.end_date and rec.state != "done" and rec.end_date < now:
                rec.action_done()

    # Computed Methods
    @api.depends("start_date", "end_date")
    def compute_duration(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_days = delta.days
            else:
                record.duration_days = 0

    def compute_application_count(self):
        for rec in self:
            rec.application_count = 0  # default to 0
            if rec.id:
                rec.application_count = self.env["cst.exam.ra.request"].search_count(
                    [("ra_register_id", "=", rec.id)]
                )

    # Constrains
    @api.constrains("is_published", "type")
    def _check_only_one_published_per_type(self):
        for rec in self:
            if rec.is_published and rec.type in ("recheck", "reevaluation"):
                other_published = self.search(
                    [
                        ("is_published", "=", True),
                        ("type", "=", rec.type),
                        ("id", "!=", rec.id),
                    ],
                    limit=1,
                )
                if other_published:
                    raise ValidationError(
                        f"Only one published record is allowed for type '{rec.type.replace('_', ' ').title()}'."
                    )


class REEvalApplication(models.Model):
    _name = "cst.exam.re.eval.application"
    _description = "Recheck Reval Application"

    name = fields.Char(string="Application Name")
    re_eval_registar_id = fields.Many2one(
        "cst.exam.re.eval.registar", store=True, required=True
    )
    student_id = fields.Many2one("op.student", string="Student Name", required=True)
    student_number = fields.Char(
        compute="compute_student_number", string="Student Number", store=True
    )
    programme_id = fields.Many2one("op.course", compute="compute_programme", store=True)
    subject_ids = fields.Many2many(
        "op.subject",
        relation="re_eval_register_subject_rel",
        string="Applied subjects",
    )
    attachment = fields.Binary(string="Application")
    attachment_filename = fields.Char(string="Filename")
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice",
        domain="[('move_type', '=', 'out_invoice')]",
        readonly=True,
        help="The invoice generated for this application",
    )

    # Computed Methods
    @api.depends("student_id")
    def compute_student_number(self):
        for rec in self:
            if rec.student_id:
                rec.student_number = rec.student_id.student_number
            else:
                rec.student_number = ""

    @api.depends("student_id")
    def compute_programme(self):
        for rec in self:
            if rec.student_id:
                rec.programme_id = rec.student_id.course_id
            else:
                rec.programme_id = False

    # Helper Method
    invoice_count = fields.Integer(compute="get_invoice_count")

    def get_invoice_count(self):
        for rec in self:
            if rec.invoice_id:
                rec.invoice_count = 1
            else:
                rec.invoice_count = 0

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
