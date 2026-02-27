import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="CXRImage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("xray_file", models.FileField(upload_to="uploads/cxr/")),
                ("xray_name", models.CharField(max_length=255)),
                ("xray_size", models.BigIntegerField()),
                ("top1_prediction", models.CharField(max_length=100)),
                ("analyzed_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="AnalysisResult",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("probs", models.JSONField(blank=True, default=dict)),
                ("payload_created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cxr",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="analysis_result",
                        to="api.cxrimage",
                    ),
                ),
            ],
        ),
    ]
