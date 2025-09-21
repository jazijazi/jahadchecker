from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet

from common.models import CustomModel , Company

class Apis(models.Model):
    # Define choices for HTTP methods
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH' , 'PATCH'),
        ('DELETE', 'DELETE'),
    ]
    url_validator = RegexValidator(
        regex=r'^\/[a-zA-Z0-9_\-\/]*\/?$',
        message='فرمت URL نادرست است. باید با / شروع شود و فقط شامل حروف، اعداد، /، - و _ باشد.'
    )
    method = models.CharField(
        max_length=50, 
        choices=METHOD_CHOICES,
        blank=False, 
        null=False
    )
    url = models.CharField(
        max_length=250,
        validators=[url_validator],
        blank=False,
        null= False
    )
    desc = models.CharField(
        max_length=250,
        blank=True,
        null= True
    )

    def __str__(self):
        return f"{self.method} _ {self.url}"
    class Meta:
        unique_together = ['method', 'url']
        indexes = [
            models.Index(fields=['method', 'url']),  # Composite index
            models.Index(fields=['url']),            # Individual indexes
            models.Index(fields=['method']),
        ]
        verbose_name = "نام دسترسی"
        verbose_name_plural = "لیست  دسترسی ها"

class Tools(models.Model):
    title = models.CharField(
        unique=True,
        max_length=100,
        blank=False,
        null=False
    )
    desc = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title
    class Meta:
        verbose_name = "ابزار دسترسی"
        verbose_name_plural = "ابزارهای دسترسی"

class Roles(models.Model):
    apis = models.ManyToManyField(
        Apis,
        blank=False,
        related_name='rrolesapis',
        related_query_name='rolesapis'
    )
    tools = models.ManyToManyField(
        Tools,
        blank=True,
        related_name='rroletools',
        related_query_name='roletools'
    )
    title = models.CharField(
        unique=True,
        max_length=100,
        blank=False,
        null=False
    )
    desc = models.CharField(
        max_length=250,
        blank=True,
        null=True
    )

    def __str__(self):
        return self.title
    class Meta:
        verbose_name = "نام نقش"
        verbose_name_plural = "لیست نقش ها"

class User(AbstractUser):
    """
    Custom User model.
    """

    #Overwrite username field
    username_validator = RegexValidator(r'^[0-9a-zA-Z]*$', 'فقط حروف و اعداد استفاده کنید')
    username = models.CharField(
      _("username"),
      max_length=25,
      unique=True,
      help_text=_(
          "اجباری.کمتر از 25 کاراکتر. فقط حروف و اعداد استفاده کنید"
      ),
      validators=[username_validator],
      error_messages={
          "unique": _("کاربر با این نام کاربری موجود است"),
      },
    )

    first_name_fa = models.CharField(verbose_name="نام فارسی", max_length=255, blank=True, null=True)
    last_name_fa = models.CharField(verbose_name="نام خانوادگی فارسی", max_length=255, blank=True, null=True)
    address = models.CharField(verbose_name="آدرس", max_length=255, blank=True, null=True)

    roles = models.ForeignKey(
        Roles,
        on_delete=models.SET_NULL,
        related_name="rrole",
        blank=True,
        null=True,
        db_index=True  # Add index for faster lookups
    )

    # Foreign key to Company
    company = models.ForeignKey(
        Company,  # Use string reference
        on_delete=models.SET_NULL,
        related_name="users",
        blank=True,
        null=True,
        db_index=True,
        verbose_name="شرکت",
        help_text="شرکت مرتبط با این کاربر"
    )


    def get_full_name_fa(self):
        full_name_fa = "%s %s" % (self.first_name_fa, self.last_name_fa)
        return full_name_fa.strip()

    REQUIRED_FIELDS = [] #dont requierd email 
    
    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name = "نام کاربران"
        verbose_name_plural = "لیست کاربران"

class Notification(CustomModel):
    sender = models.ForeignKey(
        User,
        verbose_name="فرستنده",
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        blank=True, # Allow null for system notifications
        null=True, # Allow null for system notifications
        db_index=True,
    )
    receiver = models.ForeignKey(
        User,
        verbose_name="گیرنده",
        on_delete=models.CASCADE,
        related_name='received_notifications',
        blank=False,
        null=False,
        db_index=True
    )
    subject = models.CharField(
        verbose_name="موضوع" ,
        max_length=500,
        blank=False,
        null=False,
        unique=False,
    )
    text = models.CharField(
        verbose_name="متن" ,
        max_length=2000,
        blank=False,
        null=False,
        unique=False
    )
    is_read = models.BooleanField(
        verbose_name="وضعیت خوانده شده",
        default=False,
        blank=False,
        null=False
    )

    def __str__(self):
        sender_name = self.sender.username if self.sender else "سیستم"
        return f"اعلان: از {sender_name} به {self.receiver.username} - {self.subject[:30]}..."
    
    class Meta:
        verbose_name = "اعلان"
        verbose_name_plural = "اعلان ها"
        ordering = ["-created_at"]

        indexes = [
            models.Index(fields=['receiver', '-created_at']),
            models.Index(fields=['sender', '-created_at']),
        ]
