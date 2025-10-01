from django.utils import timezone
from django.db import models
from django.contrib.gis.db import models as gis_models

from django.core.exceptions import ValidationError

from common.models import CustomModel , Province
from accounts.models import User


class Pelak(CustomModel):
    number = models.CharField(
        verbose_name="شماره پلاک",
        max_length=100,
        unique=True,
        blank=False,
        null=False,
        primary_key=True,
    )
    title = models.CharField(
        verbose_name="عنوان پلاک",
        max_length=100,
        unique=False,
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        User,
        verbose_name="ایجاد شده توسط",
        on_delete=models.SET_NULL,
        related_name="rusercreatedpelaks",
        blank=True,
        null=True
    )
    verify = models.BooleanField(
        verbose_name="تایید نهایی شده؟",
        default=False,
    )
    verifydata = models.DateTimeField(
        verbose_name="تاریخ تایید نهایی شدن",
        blank=True,
        null=True,
    )
    verifyby = models.ForeignKey(
        User,
        verbose_name="تایید نهایی توسط",
        on_delete=models.SET_NULL,
        related_name="ruserverifydplaks",
        blank=True,
        null=True
    )
    provinces = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name="rprovincecpelak",
        verbose_name="استان مربوطه",
        blank=False,
        null=False
    )
    border = gis_models.MultiPolygonField(
        srid=4326,
        blank=False,
        null=False,
        spatial_index=True,
    )
    @property
    def is_verified(self):
        """Check if the pelak is verified"""
        return self.verify and self.verifydata is not None

    def verify_pelak(self, user:User):
        
        if not user.is_superuser:
            if not user.company:
                raise ValueError("کاربر باید به شرکتی متصل باشد")
            
            if not user.company.is_nazer:
                raise ValueError("فقط شرکت‌های ناظر می‌توانند پلاک تایید کنند")
        
        self.verify = True
        self.verifydata = timezone.now()
        self.verifyby = user
        self.save()

    def unverify_pelak(self , user:User):
        if not user.is_superuser:
            raise ValueError("فقط کاربر ادمین اجازه لغو تایید نهایی را دارد")
            
        self.verify = False
        self.verifydata = None
        self.verifyby = None
        self.save()

    def clean(self):
        """Model validation"""
        super().clean()

        if self.verify and not self.verifydata:
            raise ValidationError({
                'verifydata': 'تاریخ تایید باید مشخص شود وقتی پلاک تایید شده است'
            })
        
        if self.verify and not self.verifyby:
            raise ValidationError({
                'verifyby': 'کاربر تایید کننده باید مشخص شود وقتی پلاک تایید شده است'
            })
        
        # Ensure verifydata is not in the future
        if self.verifydata and self.verifydata > timezone.now():
            raise ValidationError({
                'verifydata': 'تاریخ تایید نمی‌تواند در آینده باشد'
            })

    def __str__(self):
        return f"{self.title} ({self.number or 'بدون شماره'})"

    class Meta:
        verbose_name = "پلاک"
        verbose_name_plural = "پلاک ها"
        indexes = [
            models.Index(fields=['number']),
            models.Index(fields=['verify', 'verifydata']),  # for filtering verified pelaks
            models.Index(fields=['created_at']),
        ]

