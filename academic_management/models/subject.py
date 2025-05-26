import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class OpSubject(models.Model):
    _inherit = "op.subject"

    moduletype = fields.Selection(
        [
            ("with_practical", "Module with Practical Assessment"),
            ("without_practical", "Module without Practical Assessment"),
            ("without_exam", "Module without Exam"),
        ],
        string="Type",
        required=True,
    )
    # Default values allow user input after pre-filling
    ca_weightage = fields.Float("CA Weightage", store=True)
    practical_weightage = fields.Float("Practical Weightage", store=True)
    exam_weightage = fields.Float("Exam Weightage", store=True)

    credit = fields.Float("Credit", readonly=False, store=True)
    course_id = fields.Many2one(
        "op.course", string="Course", ondelete="cascade", required=True
    )

    # For mark uploader
    tutor_id = fields.Many2one("hr.employee", string="Tutor")

    is_offered = fields.Boolean(
        string="Is Offered This Semester",
        help="Keep Track whether the module is currently being offered",
        compute="_check_is_offered",
        store=True,
    )

    is_offered_to_repeat = fields.Boolean(
        string="Is Offered To Repeat Student",
        help="Keep Track whether the module is being offered to repeat Students",
        compute="_check_is_offered",
        store=True,
        readonly=False,
    )

    # ----------
    # Depends
    # -----------

    @api.depends("is_offered")
    def _offer_to_repeat(self):
        for rec in self:
            if rec.is_offered:
                rec.is_offered_to_repeat = True
            else:
                rec.is_offered_to_repeat = False

    @api.onchange("moduletype")
    def _onchange_moduletype(self):
        """Prefill default values for assessment weightages when moduletype is selected"""
        if self.moduletype == "with_practical":
            self.ca_weightage = 35.0
            self.practical_weightage = 25.0
            self.exam_weightage = 40.0
        elif self.moduletype == "without_practical":
            self.ca_weightage = 50.0
            self.practical_weightage = 0.0
            self.exam_weightage = 50.0
        elif self.moduletype == "without_exam":
            self.ca_weightage = 100.0
            self.practical_weightage = 0.0
            self.exam_weightage = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        # This will handle multiple records (vals_list is a list of dictionaries)
        for vals in vals_list:
            # Check if the 'moduletype' is provided in each record
            module_type = vals.get("moduletype")

            if module_type:
                # Handle the case where 'moduletype' is present and set default weightages
                if module_type == "without_practical":
                    vals["practical_weightage"] = 0.0

                if module_type == "without_exam":
                    vals["practical_weightage"] = 0.0
                    vals["exam_weightage"] = 0.0

            # Now check if the user has provided custom weightages
            ca_weightage = vals.get("ca_weightage", 0.0)
            practical_weightage = vals.get("practical_weightage", 0.0)
            exam_weightage = vals.get("exam_weightage", 0.0)

            # Calculate the total weightage
            total_weightage = ca_weightage + practical_weightage + exam_weightage

            # Validate that the total weightage equals 100
            if total_weightage != 100.0:
                raise ValidationError(
                    "The total weightage (CA + Practical + Exam) must equal 100."
                )

        # If validation passes, call the super method to actually write the values to the record(s)
        result = super(OpSubject, self).create(vals_list)

        return result

    ##NOTE no validation here, dont know why the write method is being called when create

    def write(self, vals):

        module_type = vals.get("moduletype")

        if module_type:
            # Handle the case where 'moduletype' is present and set default weightages
            if module_type == "without_practical":
                vals["practical_weightage"] = 0.0

            if module_type == "without_exam":
                vals["practical_weightage"] = 0.0
                vals["exam_weightage"] = 0.0

        # Now check if the user has provided custom weightages
        ca_weightage = vals.get("ca_weightage", 0)
        practical_weightage = vals.get("practical_weightage", 0)
        exam_weightage = vals.get("exam_weightage", 0)

        result = super(OpSubject, self).write(vals)

        # Call _check_is_offered to update 'is_offered' and 'is_offered_to_repeat' fields

        return result
