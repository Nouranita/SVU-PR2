import os
import shutil
import pandas as pd

# ============
IMAGES_DIR = r"C:\Users\Nouran\Desktop\PR2\Data Set\Normal Data Set\NIH Chest X-rays\Images"
CSV_PATH   = r"C:\Users\Nouran\Desktop\PR2\Data Set\Normal Data Set\NIH Chest X-rays\Data_Entry_2017"
OUTPUT_DIR = r"C:\Users\Nouran\Desktop\PR2\Data Set\Normal Data Set\NIH Chest X-rays\NIH_selected"

MAX_IMAGES_PER_CLASS = 2000
# ============

# If the CSV file was saved as Data_Entry_2017.csv, handle it automatically
if not os.path.exists(CSV_PATH) and os.path.exists(CSV_PATH + ".csv"):
    CSV_PATH = CSV_PATH + ".csv"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# Output folders (5 classes)
fibrosis_dir  = os.path.join(OUTPUT_DIR, "Fibrosis_like")
mass_dir      = os.path.join(OUTPUT_DIR, "Mass_Opacity_like")
normal_dir    = os.path.join(OUTPUT_DIR, "Normal_NoFinding")
pneumonia_dir = os.path.join(OUTPUT_DIR, "Pneumonia")
covid_dir     = os.path.join(OUTPUT_DIR, "Covid19")

for d in [fibrosis_dir, mass_dir, normal_dir, pneumonia_dir, covid_dir]:
    os.makedirs(d, exist_ok=True)

# Read CSV
df = pd.read_csv(CSV_PATH)

# Counters
fibrosis_count = 0
mass_count = 0
normal_count = 0
pneumonia_count = 0
covid_count = 0

def parse_labels(label_str):
    """Split labels like 'Atelectasis|Mass' into a clean list."""
    if pd.isna(label_str):
        return []
    return [x.strip() for x in str(label_str).split("|") if x.strip()]

def get_image_path(image_name):
    """All images are directly inside IMAGES_DIR."""
    p = os.path.join(IMAGES_DIR, image_name)
    return p if os.path.exists(p) else None

# COVID label variants (different spellings)
COVID_KEYWORDS = {"COVID-19", "COVID19", "SARS-CoV-2", "Coronavirus", "Corona Virus"}

for _, row in df.iterrows():
    image_name = row.get("Image Index", None)      
    labels_raw = row.get("Finding Labels", "")     

    if not image_name:
        continue

    labels = parse_labels(labels_raw)

    image_path = get_image_path(image_name)
    if image_path is None:
        continue

    # 1) Normal (No Finding)
    if ("No Finding" in labels) and (normal_count < MAX_IMAGES_PER_CLASS):
        shutil.copy(image_path, normal_dir)
        normal_count += 1

    # 2) Pneumonia
    if ("Pneumonia" in labels) and (pneumonia_count < MAX_IMAGES_PER_CLASS):
        shutil.copy(image_path, pneumonia_dir)
        pneumonia_count += 1

    # 3) Covid-19 
    if any(lbl in COVID_KEYWORDS for lbl in labels) and (covid_count < MAX_IMAGES_PER_CLASS):
        shutil.copy(image_path, covid_dir)
        covid_count += 1

    # 4) Fibrosis-like
    if ("Fibrosis" in labels) and (fibrosis_count < MAX_IMAGES_PER_CLASS):
        shutil.copy(image_path, fibrosis_dir)
        fibrosis_count += 1

    # 5) Mass / Opacity-like
    if any(x in labels for x in ["Mass", "Nodule", "Consolidation"]) and (mass_count < MAX_IMAGES_PER_CLASS):
        shutil.copy(image_path, mass_dir)
        mass_count += 1

    # Stop if all classes reached max
    if (fibrosis_count >= MAX_IMAGES_PER_CLASS and
        mass_count >= MAX_IMAGES_PER_CLASS and
        normal_count >= MAX_IMAGES_PER_CLASS and
        pneumonia_count >= MAX_IMAGES_PER_CLASS and
        covid_count >= MAX_IMAGES_PER_CLASS):
        break

print("Done.")
print("Normal (No Finding):", normal_count)
print("Pneumonia:", pneumonia_count)
print("Covid-19:", covid_count)
print("Fibrosis:", fibrosis_count)
print("Mass/Opacity:", mass_count)
