from odoo import api, fields, models
from odoo.exceptions import ValidationError


class StudentLeaveTypes(models.Model):
    _name = "cst.student.leave.type"
    _description = "Student Time Off Type"

    name = fields.Char("Time Off Type", required=True, translate=True)
    faculty_validator = fields.Many2one("hr.employee", string="Leave Approved By")

    student_leave_validation_type = fields.Selection(
        [
            ("pl", "By Programme Leader"),  # Option for Programme Leader
            ("faculty", "By Faculty"),  # Option for Faculty
        ],
        string="Leave Approver",  # Label for the field in the UI
        help="Choose who will approve the student leave request.",  # Optional help text displayed on hover
    )

    support_document = fields.Boolean(string="Supporting Document")
    notify_ids = fields.Many2many(
        "res.users",
        "student_leave_type_res_users_rel",
        "student_leave_type_id",
        "res_users_id",
        string="Notified Employee",
        domain="[('employee_ids', '!=', False)]",
        auto_join=True,
        help="Choose the people who will be notified of the leave",
    )

    active = fields.Boolean(default=True)

    @api.onchange("student_leave_validation_type")
    def _check_leave_validator(self):
        """Resets faculty_validator to False if leave_validation_type is changed from 'faculty' to something else."""
        for rec in self:
            if rec.student_leave_validation_type != "faculty":
                rec.faculty_validator = False


class StudentLeaveType(models.Model):
    _inherit = "hr.leave.type"
    _description = "Student Specific Leave"

    is_student_leave = fields.Boolean(string="Check if Student Leave", default=False)

    faculty_validator = fields.Many2one("hr.employee", string="Leave Approved By")

    student_leave_validation_type = fields.Selection(
        [
            ("pl", "By Programme Leader"),  # Option for Programme Leader
            ("faculty", "By Faculty"),  # Option for Faculty
        ],
        string="Leave Approver",  # Label for the field in the UI
        help="Choose who will approve the student leave request.",  # Optional help text displayed on hover
    )

    # --------------------------------
    # NOTE Couple of things i need to handle here.
    # 1. Add leave approver of Programme Leader.
    #   Programme Leader id is available in the course model
    #   Each student will have unique programme leader
    # --------------------------------

    # Add logic if the leave type is a student leave
    @api.onchange("is_student_leave")
    def _onchange_student_leave(self):
        if self.is_student_leave:
            # Allocations are not needed for Student Leave
            self.requires_allocation = "no"
        else:
            self.is_student_leave = False
            self.requires_allocation = "yes"

    # No allocations are allowed for student leaves
    @api.onchange("requires_allocation")
    def _check_stduent_leave_allocation(self):
        if self.is_student_leave and self.requires_allocation == "yes":
            raise ValidationError("Student Leave cannot have allocations")

    @api.onchange("leave_validation_type")
    def _check_leave_validator(self):
        """Resets faculty_validator to False if leave_validation_type is changed from 'faculty' to something else."""
        for rec in self:
            if rec.leave_validation_type != "faculty":
                rec.faculty_validator = False
