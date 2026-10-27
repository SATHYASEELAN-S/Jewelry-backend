from django.contrib import admin

# Register your models here.
from .models import Payment, PaymentStatusHistory

admin.site.register(Payment)
admin.site.register(PaymentStatusHistory)