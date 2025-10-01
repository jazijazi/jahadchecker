from django.utils import timezone
from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.core.exceptions import NON_FIELD_ERRORS
from common.models import CustomModel
from accounts.models import User


class Flag(CustomModel):
    FLAG_STATUS_CHOICES = [
        (1, 'بدون تغییر'),
        (2, 'دارای تغییر جزئی'),
        (3, 'تفکیک شده'),
        (4, 'کاملاً غیرهمخوان'),
    ]
    
    border = gis_models.PointField(
        srid=4326,
        blank=False,
        null=False,
        verbose_name="موقعیت نقطه",
        help_text="موقعیت جغرافیایی نقطه فلگ",
        spatial_index=True,
    )
    
    createdby = models.ForeignKey(
        User,
        verbose_name="ایجاد شده توسط",
        on_delete=models.SET_NULL,
        related_name="created_flags",
        blank=True,
        null=True
    )
    
    description = models.TextField(
        verbose_name="توضیحات",
        max_length=512,
        blank=True,
        null=True,
        help_text="توضیحات اضافی در مورد فلگ"
    )
    
    cadaster = models.ForeignKey(
        'landreg.Cadaster',
        verbose_name="کاداستر",
        on_delete=models.CASCADE,
        related_name="flags",
        blank=False,
        null=False
    )
    
    status = models.IntegerField(
        verbose_name="وضعیت",
        choices=FLAG_STATUS_CHOICES,
        blank=False,
        null=False,
        default=1,
        help_text="وضعیت فعلی فلگ"
    )

    def __str__(self):
        status_label = dict(self.FLAG_STATUS_CHOICES).get(self.status, 'نامشخص')
        return f"فلگ {self.id} - {status_label}"

    def get_status_display_persian(self):
        """Get Persian display name for status"""
        return dict(self.FLAG_STATUS_CHOICES).get(self.status, 'نامشخص')
    
    def clean(self):
        """Validate that the flag point intersects with the cadaster border"""
        super().clean()
        
        # ----------- validate flag cadaster -----------
        # Check if the point intersects with the cadaster's border
        if self.border and self.cadaster:
            if not self.cadaster.border.intersects(self.border):
                raise ValidationError({
                    'border': 'موقعیت فلگ باید در محدوده کاداستر مربوطه قرار داشته باشد'
                })
            
        # ----------- validate flag user creator -----------
        # Skip company and role checks for superusers
        if self.createdby and self.createdby.is_superuser:
            return
    
        # Validate user has a company (only for non-superusers)
        if not self.createdby or not self.createdby.company:
            raise ValidationError({
                NON_FIELD_ERRORS: "کاربر نویسنده فلگ باید به یک شرکت متصل باشد"
            })
    
        user_company = self.createdby.company
    
        # Build base queryset (exclude self if updating)
        base_query = Flag.objects.filter(cadaster=self.cadaster)
        if self.pk:
            base_query = base_query.exclude(pk=self.pk)
    
        # Check nazer constraint
        if user_company.is_nazer:
            if base_query.filter(createdby__company__is_nazer=True).exists():
                raise ValidationError({
                    NON_FIELD_ERRORS: "فلگ روی این کاداستر قبلا توسط ناظر ثبت شده است"
                })
    
        # Check supernazer constraint
        if user_company.is_supernazer:
            if base_query.filter(createdby__company__is_supernazer=True).exists():
                raise ValidationError({
                    NON_FIELD_ERRORS: "فلگ روی این کاداستر قبلا توسط ناظرعالی ثبت شده است"
                })

            
    def save(self, *args, **kwargs):
        """Override save to ensure validation runs"""
        # Run full_clean to trigger clean() method
        self.full_clean()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "فلگ"
        verbose_name_plural = "فلگ‌ها"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['cadaster']),
            models.Index(fields=['createdby']),
            models.Index(fields=['created_at', 'status']),
        ]
        ordering = ['-created_at']  # Most recent first
