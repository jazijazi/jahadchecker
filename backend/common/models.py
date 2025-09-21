from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError

class CustomModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="تاریخ بروزرسانی")

    class Meta:
        abstract = True

class Province(models.Model):
    name_fa = models.CharField(
        verbose_name="نام",
        unique=True,
        blank=False,
        null=False,
    )
    cnter_name_fa = models.CharField(
        verbose_name="نام مرکز",
        unique=True,
        blank=False,
        null=False,
    )
    code = models.PositiveIntegerField(
        verbose_name="کد",
        unique=True,
        blank=False,
        null=False,
    )
    border = gis_models.MultiPolygonField(
        srid=4326,
        blank=False,
        null=False
    )

    def __str__(self):
        return f"province {self.name_fa} ({self.code})"
    class Meta:
        verbose_name = "استان"
        verbose_name_plural = "استان ها"

class County(models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.SET_NULL,
        related_name="rprovince",
        blank=True,
        null=True,
    )
    name_fa = models.CharField(
        verbose_name="نام",
        unique=True,
        blank=False,
        null=False,
    )
    code = models.PositiveIntegerField(
        verbose_name="کد",
        unique=True,
        blank=False,
        null=False,
    )
    border = gis_models.MultiPolygonField(
        srid=4326,
        blank=False,
        null=False
    )

    def __str__(self):
        return f"County {self.name_fa} ({self.code})"
    class Meta:
        verbose_name = "شهرستان"
        verbose_name_plural = "شهرستان ها"



class Company(CustomModel):
    name = models.CharField(
        verbose_name="نام شرکت",
        max_length=100,
        blank=False,
        null=False,
        unique=False
    )
    typ = models.CharField(
        verbose_name="نوع شرکت",
        max_length=100, 
        blank=True,
        null=True, 
        unique=False
    )
    callnumber = models.CharField(
        verbose_name="شماره تماس",
        max_length=100, 
        blank=True,
        null=True, 
        unique=False
    )
    address = models.CharField(
        verbose_name="آدرس",
        max_length=255, 
        blank=True,
        null=True, 
        unique=False
    )
    comment = models.CharField(
        verbose_name="توضیحات",
        max_length=255, 
        blank=True,
        null=True, 
        unique=False
    )
    # Changed to ManyToManyField
    provinces = models.ManyToManyField(
        'Province',
        related_name="companies",
        blank=True,
        verbose_name="استان‌ها"
    )
    is_nazer = models.BooleanField(
        verbose_name="ناظر استانی است؟",
        default=False,
    )
    is_supernazer = models.BooleanField(
        verbose_name="ناظر عالی است؟",
        default=False,
    )
    is_moshaver = models.BooleanField(
        verbose_name="مشاور است؟",
        default=False,
    )

    class Meta:
        verbose_name = "لیست شرکت"
        verbose_name_plural = "لیست شرکت ها"
    
    def __str__(self):
        return f"{self.name}"
    
    def clean(self):
        """
        Custom validation to ensure:
        - Only one of is_nazer, is_supernazer, is_moshaver can be True
        - If is_nazer or is_moshaver is True, only one province is allowed
        - If is_supernazer is True, multiple provinces are allowed
        """
        super().clean()
        
        # Check that only one role is selected
        roles = [self.is_nazer, self.is_supernazer, self.is_moshaver]
        true_count = sum(roles)
        
        if true_count > 1:
            raise ValidationError(
                "فقط یکی از نقش‌های ناظر استانی، ناظر عالی یا مشاور می‌تواند انتخاب شود."
            )
        
        # Check province constraints (only for existing instances)
        if self.pk:
            province_count = self.provinces.count()
            
            if (self.is_nazer or self.is_moshaver) and province_count > 1:
                raise ValidationError(
                    "ناظر استانی و مشاور فقط می‌توانند یک استان داشته باشند."
                )
    
    def save(self, *args, **kwargs):
        """Override save to run validation"""
        self.clean()
        super().save(*args, **kwargs)
    
    def clean_provinces_after_save(self):
        """
        Additional method to validate provinces after ManyToMany relations are saved
        This should be called after saving the instance and setting provinces
        """
        province_count = self.provinces.count()
        
        if (self.is_nazer or self.is_moshaver) and province_count > 1:
            raise ValidationError(
                "ناظر استانی و مشاور فقط می‌توانند یک استان داشته باشند."
            )
        
        return True

    
