from datetime import date, datetime

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .emails import notify_invite
from .models import Assignment, AssignmentRequest, Company, ContactAttempt, Message, VisitNote


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SECURE_SSL_REDIRECT=False,
)
class BrandingTests(TestCase):
    def test_password_reset_flow_uses_northern_nv_now_branding(self):
        User.objects.create_user(
            username='reset-user',
            email='reset@example.com',
            password='test-pass',
        )

        form_response = self.client.get(reverse('password_reset'))
        self.assertContains(form_response, 'northern-nv-now-primary.svg')
        self.assertContains(form_response, 'Reset Password – Northern NV Now')
        self.assertNotContains(form_response, 'edawn-logo.svg')

        response = self.client.post(reverse('password_reset'), {
            'email': 'reset@example.com',
        })

        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'Reset your Northern NV Now Business Builders Portal password',
        )
        self.assertIn(
            'Northern NV Now Business Builders Portal account',
            mail.outbox[0].body,
        )

    def test_invite_email_uses_northern_nv_now_branding(self):
        notify_invite('volunteer@example.com', 'https://portal.example.test/register/')

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            "You've been invited to Northern NV Now Business Builders",
        )
        self.assertIn('kim@northernnvnow.com', mail.outbox[0].body)
        self.assertNotIn('EDAWN', mail.outbox[0].body)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_PASSWORD='',
    SECURE_SSL_REDIRECT=False,
    SF_CLIENT_ID='',
    SF_CLIENT_SECRET='',
    SF_LOGIN_URL='',
)
class CompanyManagementTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='company-admin',
            password='test-pass',
            is_staff=True,
            first_name='Casey',
        )
        self.volunteer = User.objects.create_user(
            username='company-volunteer',
            password='test-pass',
            first_name='Val',
        )
        self.company = Company.objects.create(
            name='Acme Manufacturing',
            industry='Manufacturing',
            city='Reno',
            notes='Call the operations director before visiting.',
            is_browse_visible=True,
        )

    def _company_payload(self, **overrides):
        payload = {
            'name': self.company.name,
            'status': self.company.status,
            'industry': self.company.industry,
            'address': self.company.address,
            'city': self.company.city,
            'state': self.company.state,
            'zip_code': self.company.zip_code,
            'phone': self.company.phone,
            'email': self.company.email,
            'website': self.company.website,
            'primary_contact_name': self.company.primary_contact_name,
            'primary_contact_title': self.company.primary_contact_title,
            'notes': self.company.notes,
            'imported_last_visit_date': (
                self.company.imported_last_visit_date.isoformat()
                if self.company.imported_last_visit_date else ''
            ),
            'is_browse_visible': 'on',
        }
        payload.update(overrides)
        return payload

    def test_company_management_is_staff_only(self):
        self.client.force_login(self.volunteer)

        response = self.client.get(reverse('staff_companies'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

    def test_staff_can_list_search_and_open_company_history(self):
        assignment = Assignment.objects.create(
            company=self.company,
            volunteer=self.volunteer,
            assigned_by=self.staff,
        )
        self.company.status = Company.STATUS_ASSIGNED
        self.company.save(update_fields=['status'])
        Company.objects.create(name='Different Company', city='Sparks')
        self.client.force_login(self.staff)

        list_response = self.client.get(reverse('staff_companies'), {'q': 'Acme'})
        detail_response = self.client.get(
            reverse('staff_company_detail', args=[self.company.pk]),
        )

        self.assertContains(list_response, 'Acme Manufacturing')
        self.assertNotContains(list_response, 'Different Company')
        self.assertContains(detail_response, 'Call the operations director before visiting.')
        self.assertContains(detail_response, 'Assignment History')
        self.assertContains(detail_response, self.volunteer.get_full_name())
        self.assertContains(detail_response, reverse('company_detail', args=[assignment.pk]))

    def test_staff_can_edit_company_details_and_notes(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('staff_company_detail', args=[self.company.pk]),
            self._company_payload(
                name='Acme Advanced Manufacturing',
                status=Company.STATUS_VISITED,
                notes='Updated internal context.',
            ),
        )

        self.assertRedirects(
            response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        self.company.refresh_from_db()
        self.assertEqual(self.company.name, 'Acme Advanced Manufacturing')
        self.assertEqual(self.company.status, Company.STATUS_VISITED)
        self.assertEqual(self.company.notes, 'Updated internal context.')

    def test_active_assignment_prevents_inconsistent_status_and_archiving(self):
        Assignment.objects.create(
            company=self.company,
            volunteer=self.volunteer,
            assigned_by=self.staff,
        )
        self.company.status = Company.STATUS_ASSIGNED
        self.company.save(update_fields=['status'])
        self.client.force_login(self.staff)

        edit_response = self.client.post(
            reverse('staff_company_detail', args=[self.company.pk]),
            self._company_payload(status=Company.STATUS_UNASSIGNED),
        )
        confirm_response = self.client.get(
            reverse('staff_company_archive', args=[self.company.pk]),
        )
        archive_response = self.client.post(
            reverse('staff_company_archive', args=[self.company.pk]),
        )

        self.assertEqual(edit_response.status_code, 200)
        self.assertContains(edit_response, 'status must remain Assigned')
        self.assertContains(confirm_response, 'This company cannot be removed yet.')
        self.assertRedirects(
            archive_response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, Company.STATUS_ASSIGNED)
        self.assertFalse(self.company.is_archived)

    def test_archiving_preserves_company_and_denies_pending_requests(self):
        request = AssignmentRequest.objects.create(
            company=self.company,
            volunteer=self.volunteer,
        )
        self.client.force_login(self.staff)

        confirm_response = self.client.get(
            reverse('staff_company_archive', args=[self.company.pk]),
        )
        response = self.client.post(
            reverse('staff_company_archive', args=[self.company.pk]),
        )

        self.assertContains(confirm_response, 'Remove and Archive')
        self.assertContains(confirm_response, 'pending request')
        self.assertRedirects(response, reverse('staff_companies'))
        self.company.refresh_from_db()
        request.refresh_from_db()
        self.assertTrue(self.company.is_archived)
        self.assertEqual(self.company.archived_by, self.staff)
        self.assertIsNotNone(self.company.archived_at)
        self.assertEqual(request.status, AssignmentRequest.STATUS_DENIED)
        self.assertTrue(Company.objects.filter(pk=self.company.pk).exists())

        active_list = self.client.get(reverse('staff_companies'))
        archived_list = self.client.get(reverse('staff_companies'), {'archive': 'archived'})
        self.assertNotContains(active_list, self.company.name)
        self.assertContains(archived_list, self.company.name)

        self.client.force_login(self.volunteer)
        browse_response = self.client.get(reverse('company_browse'))
        self.assertNotContains(browse_response, self.company.name)

    def test_staff_can_restore_archived_company(self):
        self.company.is_archived = True
        self.company.archived_by = self.staff
        self.company.save(update_fields=['is_archived', 'archived_by'])
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('staff_company_restore', args=[self.company.pk]),
        )

        self.assertRedirects(
            response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_archived)
        self.assertIsNone(self.company.archived_at)
        self.assertIsNone(self.company.archived_by)

    def test_staff_can_control_individual_browse_visibility(self):
        self.client.force_login(self.staff)

        response = self.client.post(
            reverse('staff_company_detail', args=[self.company.pk]),
            self._company_payload(is_browse_visible=False),
        )

        self.assertRedirects(
            response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_browse_visible)

        self.client.force_login(self.volunteer)
        browse_response = self.client.get(reverse('company_browse'))
        self.assertNotContains(browse_response, self.company.name)
        request_response = self.client.post(
            reverse('toggle_assignment_request', args=[self.company.pk]),
        )
        self.assertEqual(request_response.status_code, 404)

    def test_new_manual_and_csv_companies_start_hidden(self):
        self.client.force_login(self.staff)

        manual_response = self.client.post(reverse('staff_add_company'), {
            'name': 'New Manual Company',
        })
        csv_response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                b'name\nNew CSV Company\n',
                content_type='text/csv',
            ),
        })

        self.assertRedirects(manual_response, reverse('staff_add_company'))
        self.assertRedirects(csv_response, reverse('staff_import_csv'))
        self.assertFalse(
            Company.objects.get(name='New Manual Company').is_browse_visible,
        )
        self.assertFalse(
            Company.objects.get(name='New CSV Company').is_browse_visible,
        )

    def test_csv_import_accepts_last_visit_dates_and_updates_existing_company(self):
        self.client.force_login(self.staff)

        create_response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                b'name,last_visit_date\nISO Company,2023-11-15\nUS Date Company,4/9/2022\n',
                content_type='text/csv',
            ),
        })
        update_response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                f'name,last_visit_date\n{self.company.name},2024-06-30\n'.encode(),
                content_type='text/csv',
            ),
            'overwrite_existing': 'on',
        })

        self.assertRedirects(create_response, reverse('staff_import_csv'))
        self.assertRedirects(update_response, reverse('staff_import_csv'))
        self.assertEqual(
            Company.objects.get(name='ISO Company').imported_last_visit_date,
            date(2023, 11, 15),
        )
        self.assertEqual(
            Company.objects.get(name='US Date Company').imported_last_visit_date,
            date(2022, 4, 9),
        )
        self.company.refresh_from_db()
        self.assertEqual(self.company.imported_last_visit_date, date(2024, 6, 30))

    def test_csv_import_skips_invalid_last_visit_date_without_stopping_import(self):
        self.client.force_login(self.staff)

        response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                (
                    b'name,last_visit\n'
                    b'Invalid Date Company,not-a-date\n'
                    b'Valid Date Company,7/18/2023\n'
                ),
                content_type='text/csv',
            ),
        }, follow=True)

        self.assertContains(response, '1 created')
        self.assertContains(response, '1 skipped')
        self.assertFalse(Company.objects.filter(name='Invalid Date Company').exists())
        self.assertEqual(
            Company.objects.get(name='Valid Date Company').imported_last_visit_date,
            date(2023, 7, 18),
        )

    def test_staff_can_filter_by_effective_last_visit_year(self):
        self.company.imported_last_visit_date = date(2022, 5, 1)
        self.company.save(update_fields=['imported_last_visit_date'])
        imported_company = Company.objects.create(
            name='Imported 2023 Company',
            imported_last_visit_date=date(2023, 7, 4),
        )
        no_visit_company = Company.objects.create(name='No Visit Company')
        assignment = Assignment.objects.create(
            company=self.company,
            volunteer=self.volunteer,
            assigned_by=self.staff,
        )
        visit = VisitNote.objects.create(
            assignment=assignment,
            visited_by=self.volunteer,
            notes='Portal visit after the imported historical date.',
        )
        VisitNote.objects.filter(pk=visit.pk).update(
            visit_date=timezone.make_aware(datetime(2024, 8, 12, 10, 0)),
        )
        self.client.force_login(self.staff)

        response_2024 = self.client.get(
            reverse('staff_companies'),
            {'last_visit_year': '2024'},
        )
        response_2023 = self.client.get(
            reverse('staff_companies'),
            {'last_visit_year': '2023'},
        )
        response_2022 = self.client.get(
            reverse('staff_companies'),
            {'last_visit_year': '2022'},
        )
        response_none = self.client.get(
            reverse('staff_companies'),
            {'last_visit_year': 'none'},
        )

        self.assertContains(response_2024, self.company.name)
        self.assertNotContains(response_2022, self.company.name)
        self.assertContains(response_2023, imported_company.name)
        self.assertContains(response_none, no_visit_company.name)
        self.assertNotContains(response_none, imported_company.name)

    def test_hidden_company_request_remains_cancellable(self):
        self.company.is_browse_visible = False
        self.company.save(update_fields=['is_browse_visible'])
        pending = AssignmentRequest.objects.create(
            company=self.company,
            volunteer=self.volunteer,
        )
        self.client.force_login(self.volunteer)

        browse_response = self.client.get(reverse('company_browse'))
        cancel_response = self.client.post(
            reverse('toggle_assignment_request', args=[self.company.pk]),
        )

        self.assertContains(browse_response, 'Hidden pending request')
        self.assertContains(browse_response, self.company.name)
        self.assertRedirects(cancel_response, reverse('company_browse'))
        self.assertFalse(AssignmentRequest.objects.filter(pk=pending.pk).exists())

    def test_staff_can_filter_and_bulk_update_browse_visibility(self):
        hidden_company = Company.objects.create(
            name='Hidden Company',
            is_browse_visible=False,
        )
        untouched_company = Company.objects.create(
            name='Untouched Company',
            is_browse_visible=True,
        )
        self.client.force_login(self.staff)

        visible_response = self.client.get(
            reverse('staff_companies'),
            {'visibility': 'visible'},
        )
        hidden_response = self.client.get(
            reverse('staff_companies'),
            {'visibility': 'hidden'},
        )
        bulk_response = self.client.post(
            reverse('staff_companies_bulk_visibility'),
            {
                'company_ids': [self.company.pk, hidden_company.pk],
                'visibility': 'hidden',
                'return_query': 'visibility=visible',
            },
        )

        self.assertContains(visible_response, self.company.name)
        self.assertNotContains(visible_response, hidden_company.name)
        self.assertContains(hidden_response, hidden_company.name)
        self.assertNotContains(hidden_response, self.company.name)
        self.assertRedirects(
            bulk_response,
            f"{reverse('staff_companies')}?visibility=visible",
        )
        self.company.refresh_from_db()
        hidden_company.refresh_from_db()
        untouched_company.refresh_from_db()
        self.assertFalse(self.company.is_browse_visible)
        self.assertFalse(hidden_company.is_browse_visible)
        self.assertTrue(untouched_company.is_browse_visible)

        self.client.force_login(self.volunteer)
        denied_response = self.client.post(
            reverse('staff_companies_bulk_visibility'),
            {
                'company_ids': [self.company.pk],
                'visibility': 'visible',
            },
        )
        self.assertEqual(denied_response.status_code, 302)
        self.assertIn('/admin/login/', denied_response.url)
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_browse_visible)

    def test_hide_all_visible_only_hides_companies_currently_in_browse(self):
        hidden_company = Company.objects.create(
            name='Already Hidden',
            is_browse_visible=False,
        )
        assigned_company = Company.objects.create(
            name='Assigned but Visibility On',
            status=Company.STATUS_ASSIGNED,
            is_browse_visible=True,
        )
        archived_company = Company.objects.create(
            name='Archived but Visibility On',
            is_archived=True,
            is_browse_visible=True,
        )
        self.client.force_login(self.staff)

        confirm_response = self.client.get(reverse('staff_companies_hide_all_visible'))
        response = self.client.post(reverse('staff_companies_hide_all_visible'))

        self.assertContains(confirm_response, 'Hide All 1')
        self.assertRedirects(response, reverse('staff_companies'))
        self.company.refresh_from_db()
        hidden_company.refresh_from_db()
        assigned_company.refresh_from_db()
        archived_company.refresh_from_db()
        self.assertFalse(self.company.is_browse_visible)
        self.assertFalse(hidden_company.is_browse_visible)
        self.assertTrue(assigned_company.is_browse_visible)
        self.assertTrue(archived_company.is_browse_visible)

    def test_csv_import_restores_archived_company_without_overwriting_details(self):
        self.company.is_archived = True
        self.company.archived_at = timezone.now()
        self.company.archived_by = self.staff
        self.company.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
        self.client.force_login(self.staff)

        response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                b'name,industry\nAcme Manufacturing,Technology\n',
                content_type='text/csv',
            ),
        })

        self.assertRedirects(response, reverse('staff_import_csv'))
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_archived)
        self.assertIsNone(self.company.archived_at)
        self.assertIsNone(self.company.archived_by)
        self.assertEqual(self.company.industry, 'Manufacturing')

    def test_csv_import_restores_and_updates_archived_company_when_requested(self):
        self.company.is_archived = True
        self.company.archived_at = timezone.now()
        self.company.archived_by = self.staff
        self.company.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
        self.client.force_login(self.staff)

        response = self.client.post(reverse('staff_import_csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                b'name,industry\nAcme Manufacturing,Technology\n',
                content_type='text/csv',
            ),
            'overwrite_existing': 'on',
        })

        self.assertRedirects(response, reverse('staff_import_csv'))
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_archived)
        self.assertEqual(self.company.industry, 'Technology')

    def test_django_admin_csv_import_also_restores_archived_company(self):
        self.staff.is_superuser = True
        self.staff.save(update_fields=['is_superuser'])
        self.company.is_archived = True
        self.company.archived_at = timezone.now()
        self.company.archived_by = self.staff
        self.company.save(update_fields=['is_archived', 'archived_at', 'archived_by'])
        self.client.force_login(self.staff)

        response = self.client.post(reverse('admin:company-import-csv'), {
            'csv_file': SimpleUploadedFile(
                'companies.csv',
                b'name\nAcme Manufacturing\n',
                content_type='text/csv',
            ),
        })

        self.assertRedirects(response, reverse('admin:core_company_changelist'))
        self.company.refresh_from_db()
        self.assertFalse(self.company.is_archived)
        self.assertIsNone(self.company.archived_at)
        self.assertIsNone(self.company.archived_by)

    def test_staff_can_unassign_company_without_deleting_history(self):
        assignment = Assignment.objects.create(
            company=self.company,
            volunteer=self.volunteer,
            assigned_by=self.staff,
        )
        self.company.status = Company.STATUS_ASSIGNED
        self.company.save(update_fields=['status'])
        attempt = ContactAttempt.objects.create(
            assignment=assignment,
            attempted_by=self.volunteer,
            method='phone',
            notes='Left a voicemail.',
        )
        self.client.force_login(self.staff)

        confirm_response = self.client.get(
            reverse('staff_unassign_assignment', args=[assignment.pk]),
        )
        response = self.client.post(
            reverse('staff_unassign_assignment', args=[assignment.pk]),
        )

        self.assertContains(confirm_response, 'Unassign Acme Manufacturing?')
        self.assertContains(confirm_response, 'Nothing will be deleted.')
        self.assertRedirects(
            response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        assignment.refresh_from_db()
        self.company.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.STATUS_UNASSIGNED)
        self.assertEqual(assignment.unassigned_by, self.staff)
        self.assertIsNotNone(assignment.unassigned_at)
        self.assertEqual(self.company.status, Company.STATUS_UNASSIGNED)
        self.assertTrue(ContactAttempt.objects.filter(pk=attempt.pk).exists())

        self.client.force_login(self.volunteer)
        active_list = self.client.get(reverse('company_list'))
        browse_list = self.client.get(reverse('company_browse'))
        history_detail = self.client.get(reverse('company_detail', args=[assignment.pk]))
        self.assertNotContains(active_list, self.company.name)
        self.assertContains(browse_list, self.company.name)
        self.assertContains(history_detail, 'Assignment Ended')

    def test_staff_can_assign_company_to_an_admin_without_volunteer_cap(self):
        assignee = User.objects.create_user(
            username='assigned-admin',
            password='test-pass',
            is_staff=True,
            first_name='Alex',
        )
        assignee.profile.bbv_certified = False
        assignee.profile.save(update_fields=['bbv_certified'])
        other_company = Company.objects.create(name='Already Assigned Company')
        Assignment.objects.create(
            company=other_company,
            volunteer=assignee,
            assigned_by=self.staff,
        )
        other_company.status = Company.STATUS_ASSIGNED
        other_company.save(update_fields=['status'])
        self.client.force_login(self.staff)

        form_response = self.client.get(reverse('staff_assign'))
        response = self.client.post(reverse('staff_assign'), {
            'company': self.company.pk,
            'volunteer': assignee.pk,
        })

        self.assertContains(form_response, 'Alex (Admin)')
        self.assertRedirects(response, reverse('staff_assign'))
        assignment = Assignment.objects.get(company=self.company)
        self.assertEqual(assignment.volunteer, assignee)
        self.assertEqual(assignment.status, Assignment.STATUS_ACTIVE)
        self.company.refresh_from_db()
        self.assertEqual(self.company.status, Company.STATUS_ASSIGNED)
        company_list = self.client.get(reverse('company_list'))
        self.assertContains(company_list, 'Acme Manufacturing')
        self.assertContains(company_list, 'Alex (Admin)')

    def test_only_staff_can_unassign_and_only_when_assignment_is_active(self):
        assignment = Assignment.objects.create(
            company=self.company,
            volunteer=self.volunteer,
            assigned_by=self.staff,
            status=Assignment.STATUS_COMPLETED,
        )
        self.company.status = Company.STATUS_VISITED
        self.company.save(update_fields=['status'])

        self.client.force_login(self.volunteer)
        denied_response = self.client.post(
            reverse('staff_unassign_assignment', args=[assignment.pk]),
        )
        self.assertEqual(denied_response.status_code, 302)
        self.assertIn('/admin/login/', denied_response.url)

        self.client.force_login(self.staff)
        inactive_response = self.client.post(
            reverse('staff_unassign_assignment', args=[assignment.pk]),
        )
        self.assertRedirects(
            inactive_response,
            reverse('staff_company_detail', args=[self.company.pk]),
        )
        assignment.refresh_from_db()
        self.company.refresh_from_db()
        self.assertEqual(assignment.status, Assignment.STATUS_COMPLETED)
        self.assertEqual(self.company.status, Company.STATUS_VISITED)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_PASSWORD='test-resend-key',
    SECURE_SSL_REDIRECT=False,
    SITE_URL='https://portal.example.test',
)
class MessageNotificationTests(TestCase):
    def test_volunteer_private_message_emails_all_active_staff(self):
        volunteer = User.objects.create_user(
            username='volunteer',
            email='volunteer@example.com',
            password='test-pass',
            first_name='Val',
        )
        staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='test-pass',
            is_staff=True,
        )
        second_staff = User.objects.create_user(
            username='second-staff',
            email='second-staff@example.com',
            password='test-pass',
            is_staff=True,
        )
        User.objects.create_user(
            username='inactive-staff',
            email='inactive-staff@example.com',
            password='test-pass',
            is_staff=True,
            is_active=False,
        )

        self.client.force_login(volunteer)
        response = self.client.post(reverse('message_create'), {
            'subject': 'Need help',
            'body': 'Can an admin take a look?',
            'is_private': 'on',
        })

        self.assertRedirects(response, reverse('message_detail', args=[Message.objects.get().pk]))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(set(mail.outbox[0].to), {staff.email, second_staff.email})
        self.assertIn('New portal message from Val', mail.outbox[0].subject)
        self.assertIn('https://portal.example.test/messages/', mail.outbox[0].body)

    def test_staff_direct_message_emails_volunteer_recipient(self):
        staff = User.objects.create_user(
            username='staff',
            email='staff@example.com',
            password='test-pass',
            is_staff=True,
            first_name='Kim',
        )
        volunteer = User.objects.create_user(
            username='volunteer',
            email='volunteer@example.com',
            password='test-pass',
            first_name='Val',
        )

        self.client.force_login(staff)
        response = self.client.post(reverse('message_create'), {
            'subject': 'Schedule check-in',
            'body': 'Please log in when you can.',
            'recipient_group': 'specific_volunteer',
            'recipient_user': str(volunteer.pk),
        })

        self.assertRedirects(response, reverse('message_list'))
        msg = Message.objects.get()
        self.assertEqual(msg.recipient, volunteer)
        self.assertTrue(msg.is_private)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [volunteer.email])
        self.assertEqual(mail.outbox[0].subject, 'New message in the Business Builders portal')
        self.assertIn('Kim sent you a direct message', mail.outbox[0].body)
