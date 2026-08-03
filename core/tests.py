from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .emails import notify_invite
from .models import Message


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
