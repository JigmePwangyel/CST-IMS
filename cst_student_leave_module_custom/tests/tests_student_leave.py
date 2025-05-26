from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestStudentLeave(TransactionCase):

    def setUp(self):
        super().setUp()
        # Sample users
        self.student_user = self.env["res.users"].create(
            {
                "name": "Test Student",
                "login": "student@example.com",
                "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
            }
        )
        self.staff_user = self.env["res.users"].create(
            {
                "name": "Test Staff",
                "login": "staff@example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref(
                                "your_module_name.student_leave_approver_group"
                            ).id
                        ],
                    )
                ],
            }
        )

        self.leave_type_prog_leader = self.env["student.leave.type"].create(
            {
                "name": "Medical Leave",
                "leave_approver": "programme_leader",
            }
        )
        self.leave_type_staff = self.env["student.leave.type"].create(
            {
                "name": "Sick Leave",
                "leave_approver": "staff",
            }
        )

    def test_01_create_leave_type_with_programme_leader_approver(self):
        self.assertEqual(self.leave_type_prog_leader.leave_approver, "programme_leader")

    def test_02_create_leave_type_with_staff_approver(self):
        self.assertEqual(self.leave_type_staff.leave_approver, "staff")

    def test_03_notify_approver_when_leave_created(self):
        leave = (
            self.env["student.leave"]
            .sudo(self.student_user)
            .create(
                {
                    "student_id": self.student_user.id,
                    "leave_type_id": self.leave_type_staff.id,
                    "start_date": "2025-05-10",
                    "end_date": "2025-05-12",
                    "reason": "Medical reason",
                }
            )
        )
        self.assertTrue(leave)

    def test_04_notify_student_when_leave_approved(self):
        leave = self.env["student.leave"].create(
            {
                "student_id": self.student_user.id,
                "leave_type_id": self.leave_type_staff.id,
                "start_date": "2025-05-10",
                "end_date": "2025-05-12",
                "reason": "Medical reason",
            }
        )
        leave.action_approve()
        self.assertEqual(leave.state, "approved")

    def test_05_notify_selected_staff_when_leave_approved(self):
        leave = self.env["student.leave"].create(
            {
                "student_id": self.student_user.id,
                "leave_type_id": self.leave_type_staff.id,
                "start_date": "2025-05-10",
                "end_date": "2025-05-12",
                "reason": "Medical reason",
            }
        )
        leave.action_approve()
        self.assertEqual(leave.state, "approved")

    def test_06_dont_allow_overlapping_leaves(self):
        self.env["student.leave"].create(
            {
                "student_id": self.student_user.id,
                "leave_type_id": self.leave_type_staff.id,
                "start_date": "2025-05-10",
                "end_date": "2025-05-12",
                "reason": "First leave",
            }
        )
        with self.assertRaises(ValidationError):
            self.env["student.leave"].create(
                {
                    "student_id": self.student_user.id,
                    "leave_type_id": self.leave_type_staff.id,
                    "start_date": "2025-05-11",
                    "end_date": "2025-05-13",
                    "reason": "Overlapping leave",
                }
            )

    def test_07_students_see_only_their_leaves(self):
        leave = self.env["student.leave"].sudo(self.student_user).search([])
        for rec in leave:
            self.assertEqual(rec.student_id.id, self.student_user.id)

    def test_08_staff_can_only_approve_if_approver(self):
        leave = self.env["student.leave"].create(
            {
                "student_id": self.student_user.id,
                "leave_type_id": self.leave_type_staff.id,
                "start_date": "2025-05-10",
                "end_date": "2025-05-12",
                "reason": "Approval test",
            }
        )
        leave.sudo(self.staff_user).action_approve()
        self.assertEqual(leave.state, "approved")

    def test_09_allow_attachment_upload(self):
        leave = self.env["student.leave"].create(
            {
                "student_id": self.student_user.id,
                "leave_type_id": self.leave_type_staff.id,
                "start_date": "2025-05-10",
                "end_date": "2025-05-12",
                "reason": "With attachment",
            }
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": "proof.pdf",
                "res_model": "student.leave",
                "res_id": leave.id,
                "datas": "dummydata",
            }
        )
        self.assertEqual(attachment.res_id, leave.id)

    def test_10_disallow_leave_without_type(self):
        with self.assertRaises(ValidationError):
            self.env["student.leave"].create(
                {
                    "student_id": self.student_user.id,
                    "start_date": "2025-05-10",
                    "end_date": "2025-05-12",
                    "reason": "No type",
                }
            )

    def test_11_disallow_leave_without_start_end_date(self):
        with self.assertRaises(ValidationError):
            self.env["student.leave"].create(
                {
                    "student_id": self.student_user.id,
                    "leave_type_id": self.leave_type_staff.id,
                    "reason": "Missing dates",
                }
            )

    def test_12_disallow_end_date_before_start_date(self):
        with self.assertRaises(ValidationError):
            self.env["student.leave"].create(
                {
                    "student_id": self.student_user.id,
                    "leave_type_id": self.leave_type_staff.id,
                    "start_date": "2025-05-12",
                    "end_date": "2025-05-10",
                    "reason": "Wrong dates",
                }
            )
