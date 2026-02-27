from django.db import models

class CXRImage(models.Model):
    xray_file = models.FileField(upload_to="uploads/cxr/")

    xray_name = models.CharField(max_length=255)
    xray_size = models.BigIntegerField()
    top1_prediction = models.CharField(max_length=100)
    analyzed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.xray_name} -> {self.top1_prediction}"


class AnalysisResult(models.Model):
    cxr = models.OneToOneField(
        CXRImage,
        on_delete=models.CASCADE,
        related_name="analysis_result",
    )
    
    probs = models.JSONField(default=dict, blank=True)

    payload_created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AnalysisResult for {self.cxr.xray_name}"
