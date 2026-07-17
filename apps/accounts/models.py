from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import RegexValidator 

phone_validator=RegexValidator(
    regex    = r'^\d{10}$',
    message="Phone number must be exactly 10 digits."
)

class CustomerUserManager(BaseUserManager):
    
    def create_user(self,email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        
        email = self.normalize_email(email)
        user  = self.model(email=email,**extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user
    
    def create_superuser(self,email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_active',True)

        return self.create_user(email, password, **extra_fields)
        


class CustomUser(AbstractUser):
    username=None
    email=models.EmailField(unique=True)
    phone_number=models.CharField(max_length=10,blank=True,validators=[phone_validator])
    
    USERNAME_FIELD='email'
    REQUIRED_FIELDS=[]
    
    objects=CustomerUserManager()
    
    def __str__(self):
        return self.email
    

class Address(models.Model):
    user=models.ForeignKey(CustomUser,on_delete=models.CASCADE,related_name='addresses')
    street=models.CharField(max_length=255)
    city=models.CharField(max_length=100)
    state=models.CharField(max_length=100)
    landmark=models.CharField(max_length=255,blank=True,null=True)
    pincode=models.CharField(max_length=6)
    is_default=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.city}"
    


    
    
    