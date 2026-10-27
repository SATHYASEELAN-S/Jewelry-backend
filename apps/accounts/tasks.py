# tasks.py
from celery import shared_task
from django.conf import settings

from django.core.mail import send_mail

@shared_task
def send_welcome_email(user_email, user_name):

    subject = f"Welcome to Sparkle Jewelry, {user_name}!"
    message = "Thank you for joining."

    send_mail(
        subject, message, settings.DEFAULT_FROM_EMAIL, [user_email], fail_silently=False
    )
