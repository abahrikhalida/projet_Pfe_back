from django.db import models

class ExcelUpload(models.Model):
    file_name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending','Pending'),('processed','Processed'),('failed','Failed')],
        default='pending'
    )

    def __str__(self):
        return f"{self.file_name} - {self.uploaded_at}"


class BudgetRecord(models.Model):
    upload = models.ForeignKey(ExcelUpload, on_delete=models.CASCADE, related_name='records')
    activite = models.CharField(max_length=10, blank=True, null=True)
    region = models.CharField(max_length=10, blank=True, null=True)
    perm = models.CharField(max_length=10, blank=True, null=True)
    famille = models.CharField(max_length=50, blank=True, null=True)
    code_division = models.CharField(max_length=50, blank=True, null=True)
    libelle = models.CharField(max_length=255, blank=True, null=True)

    cout_initial_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    cout_initial_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    realisation_cumul_n_mins1_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    realisation_cumul_n_mins1_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    real_s1_n_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    real_s1_n_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_s2_n_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_s2_n_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_cloture_n_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_cloture_n_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus1_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus1_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    reste_a_realiser_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    reste_a_realiser_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus2_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus2_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus3_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus3_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus4_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus4_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus5_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    prev_n_plus5_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    janvier_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    janvier_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fevrier_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    fevrier_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mars_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mars_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    avril_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    avril_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mai_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    mai_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    juin_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    juin_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    juillet_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    juillet_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    aout_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    aout_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    septembre_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    septembre_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    octobre_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    octobre_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    novembre_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    novembre_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    decembre_total = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    decembre_dont_dex = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.libelle} | {self.region}"