from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .emails import notify_invite
from .models import Assignment, AssignmentRequest, Company, Message


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
