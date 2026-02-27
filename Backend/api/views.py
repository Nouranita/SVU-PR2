from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import CXRImage, AnalysisResult
from .inference import predict_image_bytes
from .educationalOutput import get_education_blocks


@api_view(["GET"])
@permission_classes([AllowAny])  # <-- public health
def health(request):
    return Response({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])  # <-- protected predict
def predict(request):
    if "image" not in request.FILES:
        return Response(
            {"error": "No image uploaded. Use form-data key: image"},
            status=status.HTTP_400_BAD_REQUEST
        )
    # InMemoryUploadedFile / TemporaryUploadedFile
    f = request.FILES["image"]

    # 1) Read bytes for inference
    image_bytes = f.read()

    # 2) Run real inference
    pred_label, probs = predict_image_bytes(image_bytes)

    # 3) Make sure probs is JSON-safe
    probs = {k: float(v) for k, v in probs.items()}

    # reset file pointer so Django can save it
    try:
        f.seek(0)
    except Exception:
        pass

    # 4) Save file + important metadata into DB
    cxr = CXRImage.objects.create(
        xray_file=f,                 # Django will store it in MEDIA_ROOT/uploads/cxr/
        xray_name=f.name,
        xray_size=getattr(f, "size", len(image_bytes)),
        top1_prediction=pred_label,
    )

    # One-to-one row (store analysis row (with probs)
    analysis = AnalysisResult.objects.create(
    cxr=cxr,
    probs=probs,  # already JSON-safe floats
    )

    # 5) Build base payload
    payload = {
        "filename": f.name,
        "size_bytes": len(image_bytes),
        "prediction": pred_label,
        "probs": analysis.probs,  
        "stored_file": cxr.xray_file.url if cxr.xray_file else None,
        "cxr_id": cxr.id,
        "analysis_id": analysis.id,
    }

    # 6) Add education blocks only when NOT "no finding"
    edu = get_education_blocks(pred_label)

    if edu:
        payload["education"] = edu

    return Response(payload)
