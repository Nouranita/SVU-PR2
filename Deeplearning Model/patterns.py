import os
import shutil
import pandas as pd
import random

# ================== READ PATHS ==================
IMAGES_DIR = r"C:\Users\Nouran\Desktop\PR2\Data Set\Lungs\Normal Data Set\NIH Chest X-rays\Images"
CSV_PATH   = r"C:\Users\Nouran\Desktop\PR2\Data Set\Lungs\Normal Data Set\NIH Chest X-rays\Data_Entry_2017.csv"
OUTPUT_DIR = r"C:\Users\Nouran\Desktop\PR2\SDPS\Deeplearning Model\Patterned Data Set"

MAX_IMAGES_PER_CLASS = 5000

# Split ratios (by PATIENT)
TRAIN_RATIO = 0.70
VAL_RATIO   = 0.15
TEST_RATIO  = 0.15

RANDOM_SEED = 42
# ===========================================================

# ---------- Basic checks ----------
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

if not os.path.exists(IMAGES_DIR):
    raise FileNotFoundError(f"Images folder not found: {IMAGES_DIR}")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------- Helpers ----------
def parse_labels(label_str):
    """Split labels like 'Atelectasis|Mass' into a clean list."""
    if pd.isna(label_str):
        return []
    return [x.strip() for x in str(label_str).split("|") if x.strip()]

def get_image_path(image_name):
    """All images are directly inside IMAGES_DIR."""
    p = os.path.join(IMAGES_DIR, image_name)
    return p if os.path.exists(p) else None

# NIH original Data_Entry_2017 does NOT include COVID-19 (I add it manually)
COVID_KEYWORDS = {"COVID-19", "COVID19", "SARS-CoV-2", "Coronavirus", "Corona Virus"}

# Define classes (folder names = class names)
CLASSES = {
    "Normal_NoFinding": lambda labels: ("No Finding" in labels),
    "Pneumonia":        lambda labels: ("Pneumonia" in labels),
    "Covid19":          lambda labels: any(lbl in COVID_KEYWORDS for lbl in labels),
    "Fibrosis_like":    lambda labels: ("Fibrosis" in labels),
    "Mass_Opacity_like":lambda labels: any(x in labels for x in ["Mass", "Nodule", "Consolidation"]),
}

# split folder names
SPLITS = ["Training", "Val", "Testing"]

# Per-class split targets
train_target = int(MAX_IMAGES_PER_CLASS * TRAIN_RATIO)
val_target   = int(MAX_IMAGES_PER_CLASS * VAL_RATIO)
test_target  = MAX_IMAGES_PER_CLASS - train_target - val_target  # exact sum

TARGETS = {"Training": train_target, "Val": val_target, "Testing": test_target}

# ---------- Read CSV ----------
df = pd.read_csv(CSV_PATH)

required_cols = ["Image Index", "Finding Labels", "Patient ID"]
missing = [c for c in required_cols if c not in df.columns]
if missing:
    raise ValueError(f"CSV missing columns: {missing}. Found columns: {list(df.columns)}")

# Parse labels once
df["_labels"] = df["Finding Labels"].apply(parse_labels)

# Keep only rows that match at least one class
def matches_any_class(labels):
    return any(rule(labels) for rule in CLASSES.values())

df_sel = df[df["_labels"].apply(matches_any_class)].copy()

# ---------- PATIENT-BASED SPLIT (GLOBAL) ----------
patients = df_sel["Patient ID"].dropna().astype(str).unique().tolist()
random.seed(RANDOM_SEED)
random.shuffle(patients)

n = len(patients)
n_train = int(n * TRAIN_RATIO)
n_val   = int(n * VAL_RATIO)

train_patients = set(patients[:n_train])
val_patients   = set(patients[n_train:n_train + n_val])
test_patients  = set(patients[n_train + n_val:])

# ---------- DOUBLE CHECK: NO OVERLAP ----------
overlap_tv = train_patients & val_patients
overlap_tt = train_patients & test_patients
overlap_vt = val_patients & test_patients

assert len(overlap_tv) == 0, f"Patient leakage Train-Val! Overlap count: {len(overlap_tv)}"
assert len(overlap_tt) == 0, f"Patient leakage Train-Test! Overlap count: {len(overlap_tt)}"
assert len(overlap_vt) == 0, f"Patient leakage Val-Test! Overlap count: {len(overlap_vt)}"

def patient_to_split(pid: str) -> str:
    if pid in train_patients:
        return "Training"
    if pid in val_patients:
        return "Val"
    return "Testing"

# ---------- Create output directories with requested structure ----------
# OUTPUT_DIR/Training/<class>, OUTPUT_DIR/Val/<class>, OUTPUT_DIR/Testing/<class>
for sp in SPLITS:
    for cname in CLASSES.keys():
        os.makedirs(os.path.join(OUTPUT_DIR, sp, cname), exist_ok=True)

# ---------- Copy with per-class per-split caps ----------
counts = {cname: {sp: 0 for sp in SPLITS} for cname in CLASSES.keys()}

# Shuffle rows so copy selection isn't biased
df_sel = df_sel.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

skipped_missing_file = 0
skipped_full_bucket = 0

for _, row in df_sel.iterrows():
    image_name = row["Image Index"]
    pid = str(row["Patient ID"])
    split_name = patient_to_split(pid)

    image_path = get_image_path(image_name)
    if image_path is None:
        skipped_missing_file += 1
        continue

    labels = row["_labels"]

    # Copy into each matching class (multi-label behavior)
    for cname, rule in CLASSES.items():
        if not rule(labels):
            continue

        if counts[cname][split_name] >= TARGETS[split_name]:
            skipped_full_bucket += 1
            continue

        dst_dir  = os.path.join(OUTPUT_DIR, split_name, cname)
        dst_path = os.path.join(dst_dir, image_name)

        if not os.path.exists(dst_path):
            shutil.copy(image_path, dst_path)
            counts[cname][split_name] += 1

# ---------- Report ----------
print("Done Patient-based split used (global). No patient appears in multiple splits.")
print(f"Patients: train={len(train_patients)}, val={len(val_patients)}, test={len(test_patients)}")
print(f"Targets per class: Training={train_target}, Val={val_target}, Testing={test_target}")
print(f"Skipped (missing image file): {skipped_missing_file}")
print(f"Skipped (bucket full): {skipped_full_bucket}")

print("\nPer-class copied images:")
for cname in CLASSES.keys():
    total = sum(counts[cname].values())
    print(f"  {cname}: total={total} | "
          f"Training={counts[cname]['Training']}, Val={counts[cname]['Val']}, Testing={counts[cname]['Testing']}")