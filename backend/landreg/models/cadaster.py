from django.utils import timezone
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from common.models import CustomModel , Province
from accounts.models import User

class LandUseDomain(CustomModel):
    title = models.CharField(
        verbose_name="عنوان",
        max_length=100,
        blank=False,
        null=False,
    )
    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name = "نوع کاربری"
        verbose_name_plural = "انواع کاربری"

class IrrigationTypDomain(CustomModel):
    title = models.CharField(
        verbose_name="عنوان",
        max_length=100,
        blank=False,
        null=False,
    )
    def __str__(self):
        return f"{self.title}"

    class Meta:
        verbose_name = "نوع آبیاری"
        verbose_name_plural = "انواع آبیاری"


class Cadaster(CustomModel):
    PROJECT_NAME_CHOICES = [
        ('امور اراضی', 'امور اراضی'),
        ('دریاچه', 'دریاچه'),
        ('رودخانه مرزی', 'رودخانه مرزی'),
    ]
    OWNERSHIP_CHOICES = [
        ('ششدانگ', 'ششدانگ'),
        ('مشاع', 'مشاع'),
    ]
    NEZARAT_TYPE_CHOICES = [
        ('سازمان نقشه برداری', 'سازمان نقشه برداری'),
        ('شمیم', 'شمیم'),
        ('ارتوی دارای تایید', 'ارتوی دارای تایید'),
    ]
    cadaster_status = [
        (1 , 'بدون تغییر'),
        (2 , 'دارای تغییر جزئی'),
        (3 , 'تفکیک شده'),
        (4 , 'کاملاً غیرهمخوان'),
        (5 , 'بدون تصمیم'),
    ]
    only_digit_validators=[
        RegexValidator(
            regex=r'^\d+$',
            message='این فیلد فقط می‌تواند شامل اعداد باشد (0-9)',
            code='invalid_jaam_code'
        )
    ]

    border = gis_models.MultiPolygonField(
        srid=4326,
        blank=False,
        null=False,
        verbose_name="مرز"
    )
    uniquecode = models.CharField(
        verbose_name="کد یکتا",
        max_length=100,
        unique=True,
        blank=False,
        null=False,
    )
    jaam_code = models.CharField(
        verbose_name="کد جام",
        max_length=100,
        blank=True,
        null=True,
        validators=only_digit_validators,
    )
    plak_name = models.CharField(
        verbose_name="نام پلاک",
        max_length=100,
        blank=True,
        null=True
    )
    plak_asli = models.CharField(
        verbose_name="پلاک اصلی",
        max_length=100,
        blank=True,
        null=True,
        validators=only_digit_validators,
    )
    plak_farei = models.CharField(
        verbose_name="پلاک فرعی",
        max_length=100,
        blank=True,
        null=True,
        validators=only_digit_validators,
    )
    bakhsh_sabti = models.CharField(
        verbose_name="بخش ثبتی",
        max_length=100,
        blank=True,
        null=True,
        validators=only_digit_validators,
    )
    nahiye_sabti = models.CharField(
        verbose_name="ناحیه ثبتی",
        max_length=100,
        blank=True,
        null=True
    )
    area = models.FloatField(
        verbose_name="مساحت",
        blank=True,
        null=True,
        help_text="مساحت به متر مربع"
    )
    owner_name = models.CharField(
        verbose_name="نام مالک",
        max_length=100,
        blank=True,
        null=True
    )
    owner_lastname = models.CharField(
        verbose_name="نام خانوادگی مالک",
        max_length=100,
        blank=True,
        null=True
    )
    fathername = models.CharField(
        verbose_name="نام پدر",
        max_length=100,
        blank=True,
        null=True
    )
    national_code = models.CharField(
        verbose_name="کد ملی",
        max_length=10,
        blank=True,
        null=True
    )
    mobile = models.CharField(
        verbose_name="شماره موبایل",
        max_length=20,
        blank=True,
        null=True
    )    
    ownership_kinde = models.CharField(
        verbose_name="نوع مالکیت",
        max_length=20,
        choices=OWNERSHIP_CHOICES,
        blank=True,
        null=True,
    )
    consulate_name = models.CharField(
        verbose_name="نام مشاور",
        max_length=100,
        blank=True,
        null=True
    )
    nezarat_type = models.CharField(
        verbose_name="نوع نظارت",
        max_length=50,
        choices=NEZARAT_TYPE_CHOICES,
        blank=False,
        null=False
    )
    
    project_name = models.CharField(
        verbose_name="نام پروژه",
        max_length=50,
        choices=PROJECT_NAME_CHOICES,
        blank=False,
        null=False
    )
    nezart_verify_date = models.DateTimeField(
        verbose_name="تاریخ تایید نظارت",
        blank=True,
        null=True
    )

    status = models.IntegerField(
        verbose_name="وضعیت",
        choices=cadaster_status,
        blank=False,
        null=False,
        default=5
    )

    land_use = models.ForeignKey(
        LandUseDomain,
        on_delete=models.SET_NULL,
        related_name="rlandusecadaster",
        blank=True,
        null=True
    )

    irrigation_type = models.ForeignKey(
        IrrigationTypDomain,
        on_delete=models.SET_NULL,
        related_name="rirridationcadaster",
        blank=True,
        null=True
    )

    pelak = models.ForeignKey(
        'landreg.Pelak',
        on_delete=models.CASCADE,
        related_name="rpelakcadasters",
        verbose_name="پلاک",
        blank=False,
        null=False
    )

    def __str__(self):
        return f"{self.uniquecode}"

    class Meta:
        verbose_name = "کاداستر"
        verbose_name_plural = "کاداسترها"
        indexes = [
            models.Index(fields=['uniquecode']),
            models.Index(fields=['plak_asli', 'plak_farei']),
            models.Index(fields=['national_code']),
            models.Index(fields=['bakhsh_sabti', 'nahiye_sabti']),
            models.Index(fields=['pelak']),
        ]


class OldCadasterData(CustomModel):
    # Use TextChoices for better type safety and IDE support
    class Status(models.TextChoices):
        NOT_MATCHED = '1', 'مچ نشده'
        MATCHED = '2', 'مچ شده'
    
    table_name = models.CharField(
        verbose_name="نام جدول در دیتابیس",
        max_length=100,
        blank=False,
        null=False,
        db_index=True,
        help_text="نام جدول مربوطه در دیتابیس"
    )
    
    created_by = models.ForeignKey(
        User,
        verbose_name="ایجاد شده توسط",
        on_delete=models.SET_NULL,
        related_name="created_old_cadaster_data", 
        blank=True,
        null=True
    )
    
    status = models.CharField(
        verbose_name="وضعیت",
        max_length=1,
        choices=Status.choices,
        default=Status.NOT_MATCHED,
        blank=False,
        null=False,
        db_index=True
    )
    
    matched_by = models.ForeignKey( 
        User,
        verbose_name="مچ شده توسط",
        on_delete=models.SET_NULL,
        related_name="matched_old_cadaster_data",
        blank=True,
        null=True
    )
    
    matched_at = models.DateTimeField(
        verbose_name="تاریخ مچ شدن",
        blank=True,
        null=True,
        db_index=True
    )
    
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name="old_cadaster_data",
        verbose_name="استان مربوطه",
        blank=False,
        null=False,
        db_index=True
    )

    @property
    def is_matched(self):
        return self.status == self.Status.MATCHED
    
    class Meta:
        verbose_name = "داده کادستر قدیمی"
        verbose_name_plural = "داده‌های کادستر قدیمی"
        # Add composite indexes for common query patterns
        indexes = [
            models.Index(fields=['status', 'province']),
            models.Index(fields=['matched_at', 'status']),
        ]
        # Add constraints
        constraints = [
            # Ensure matched_by and matched_at are both set or both null
            models.CheckConstraint(
                check=(
                    models.Q(matched_by__isnull=True, matched_at__isnull=True) |
                    models.Q(matched_by__isnull=False, matched_at__isnull=False)
                ),
                name='matched_fields_consistency'
            ),
        ]
    
    def __str__(self):
        return f"{self.table_name}"
    
    def clean(self):
        """Custom validation"""
        from django.core.exceptions import ValidationError
        
        if self.status == self.Status.MATCHED:
            if not self.matched_by or not self.matched_at:
                raise ValidationError(
                    'برای وضعیت "مچ شده"، فیلدهای "مچ شده توسط" و "تاریخ مچ شدن" باید پر باشند.'
                )
        elif self.status == self.Status.NOT_MATCHED:
            if self.matched_by or self.matched_at:
                raise ValidationError(
                    'برای وضعیت "مچ نشده"، فیلدهای "مچ شده توسط" و "تاریخ مچ شدن" باید خالی باشند.'
                )
    
    def save(self, *args, **kwargs):
        # Auto-set matched_at when status changes to MATCHED
        if self.status == self.Status.MATCHED and not self.matched_at:
            from django.utils import timezone
            self.matched_at = timezone.now()
        
        # Clear matched fields when status is NOT_MATCHED
        elif self.status == self.Status.NOT_MATCHED:
            self.matched_by = None
            self.matched_at = None
        
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)
    




