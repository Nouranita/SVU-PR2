# api/inference.py
import io
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms
import timm

# 1) Checkpoint path (best checkpoint)
CHECKPOINT_PATH = r"C:\Users\Nouran\Desktop\PR2\SDPS\Deeplearning Model\Effnetv2s Training\checkpoint_best.pt"


_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
_model = None
_class_names = None
_img_size = None

def _to_3ch(t):
    # t: Tensor (C,H,W); if C=1 replicate to C=3
    return t.repeat(3, 1, 1) if (t.ndim == 3 and t.shape[0] == 1) else t

def _load_checkpoint():
    ckpt = torch.load(CHECKPOINT_PATH, map_location=_device)
    # Training.py saves: ckpt["model_name"], ckpt["model_state"], ckpt["class_names"], ckpt["img_size"]
    return ckpt
#lazy loading
def load_model_once():
    global _model, _class_names, _img_size

    if _model is not None:
        return _model, _class_names, _img_size

    ckpt = _load_checkpoint()

    model_name = ckpt["model_name"]          
    state = ckpt["model_state"]              # real weights
    class_names = ckpt["class_names"]        # list of class names from training
    img_size = ckpt.get("img_size", 224)     # should be 224 from my training

    # IMPORTANT: Use pretrained=False here (no internet download). I load my weights anyway.
    model = timm.create_model(model_name, pretrained=False, num_classes=len(class_names))
    model.load_state_dict(state, strict=True)
    model.to(_device)
    model.eval()

    _model = model
    _class_names = class_names
    _img_size = img_size

    return _model, _class_names, _img_size

def _build_preprocess(img_size: int):
    # This matches eval transforms in Training.py: Resize -> ToTensor -> Lambda(to_3ch) -> Normalize(mean/std)
    return transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Lambda(_to_3ch),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])

@torch.no_grad()
def predict_image_bytes(image_bytes: bytes):
    model, class_names, img_size = load_model_once()
    preprocess = _build_preprocess(img_size)

    # Training used grayscale (L) then replicated to 3 channels
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    x = preprocess(img).unsqueeze(0).to(_device)  # shape [1,3,H,W]

    logits = model(x)
    probs = F.softmax(logits, dim=1).squeeze(0).detach().cpu().tolist()

    best_i = int(torch.tensor(probs).argmax().item())
    pred_label = class_names[best_i]

    probs_dict = {class_names[i]: float(probs[i]) for i in range(len(class_names))}
    return pred_label, probs_dict
