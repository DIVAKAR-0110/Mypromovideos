from django.db import models
import json


class AnalysisReport(models.Model):
    """Stores a completed video intelligence analysis session."""

    company = models.ForeignKey('CompanySignup', on_delete=models.CASCADE, null=True, blank=True)
    report_name = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # User inputs
    own_company = models.CharField(max_length=200)
    competitors_raw = models.TextField(help_text="JSON list of competitor names")

    # Status
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("error", "Error"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)

    # Results stored as JSON blobs
    channel_data_json = models.TextField(default="{}")
    video_data_json = models.TextField(default="{}")
    analysis_json = models.TextField(default="{}")

    # Report file
    pptx_file = models.FileField(upload_to="reports/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report #{self.pk} — {self.report_name or self.own_company} ({self.status})"

    # ── Helpers ────────────────────────────────────────────────────────────
    def get_competitors(self):
        try:
            return json.loads(self.competitors_raw)
        except Exception:
            return []

    def get_channel_data(self):
        try:
            return json.loads(self.channel_data_json)
        except Exception:
            return {}

    def get_video_data(self):
        try:
            return json.loads(self.video_data_json)
        except Exception:
            return {}

    def get_analysis(self):
        try:
            return json.loads(self.analysis_json)
        except Exception:
            return {}

    def set_channel_data(self, data):
        self.channel_data_json = json.dumps(data)

    def set_video_data(self, data):
        self.video_data_json = json.dumps(data)

    def set_analysis(self, data):
        self.analysis_json = json.dumps(data)


class CompanySignup(models.Model):
    company_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=255)
    company_image = models.ImageField(upload_to="company_images/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class Competitor(models.Model):
    company = models.ForeignKey(CompanySignup, on_delete=models.CASCADE, related_name="saved_competitors")
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
