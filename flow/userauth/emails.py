from html import escape
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


class ActivationEmailError(Exception):
    """Raised when an activation email cannot be prepared or delivered."""


def build_activation_url(activation_token):
    if not settings.FRONTEND_URL:
        raise ActivationEmailError('FRONTEND_URL is not configured.')
    if not activation_token:
        raise ActivationEmailError('The user does not have an activation token.')

    query = urlencode({'token': activation_token})
    return f"{settings.FRONTEND_URL.rstrip('/')}/activate?{query}"


def send_activation_email(user):
    activation_url = build_activation_url(user.activation_token)
    subject = 'Activate your Flow account'
    text_body = (
        'Welcome to Flow!\n\n'
        f'Activate your account by opening this link:\n{activation_url}\n\n'
        'If you did not create this account, you can ignore this email.'
    )
    html_body = (
        '<p>Welcome to Flow!</p>'
        '<p>Activate your account using the link below:</p>'
        f'<p><a href="{escape(activation_url, quote=True)}">Activate my account</a></p>'
        '<p>If you did not create this account, you can ignore this email.</p>'
    )
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    message.attach_alternative(html_body, 'text/html')

    try:
        sent_count = message.send(fail_silently=False)
    except Exception as exc:
        raise ActivationEmailError('Activation email delivery failed.') from exc

    if sent_count != 1:
        raise ActivationEmailError('The email backend did not accept the activation email.')

    return activation_url
