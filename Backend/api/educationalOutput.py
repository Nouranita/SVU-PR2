# Educational Summary

NO_FINDING_ALIASES = {
    "No-finding Pattern",
    "No finding Pattern",
    "No Finding Pattern",
    "No abnormality detected",
    "Normal",
    "Normal_NoFinding",     
    "Normal NoFinding",     
    "NoFinding",            
}


EDU_TEXT = {
    "Pneumonia": {
        "factors": (
            "Factors that may influence this prediction (educational):\n"
            "• Increased opacity / consolidation patterns that can appear in inflammatory processes.\n"
            "• Distribution and density differences across lung regions.\n"
            "• Image quality, rotation, and exposure can affect what the model focuses on."
        ),
        "reversibility": (
            "Possibility of improvement & general recommendations (educational):\n"
            "• Many causes of pneumonia improve with appropriate clinical treatment and follow-up.\n"
            "• A clinician may request symptoms review, vitals, labs, and possibly follow-up imaging.\n"
            "• Seek urgent care if severe shortness of breath, low oxygen, or rapid deterioration occurs."
        ),
        "complications": (
            "Potential complications if neglected (if diagnosis is confirmed by a doctor):\n"
            "• Worsening infection, reduced oxygenation, or respiratory distress.\n"
            "• Pleural effusion or lung abscess in some cases.\n"
            "• Higher risk in older adults or immunocompromised patients."
        ),
    },

    "Fibrosis_like": {
        "factors": (
            "Factors that may influence this prediction (educational):\n"
            "• Reticular / fibrotic-like texture patterns that suggest chronic structural change.\n"
            "• Reduced clarity in lower zones or diffuse interstitial markings.\n"
            "• Overlap with other conditions is possible; confirmation often needs specialist review."
        ),
        "reversibility": (
            "Possibility of improvement & general recommendations (educational):\n"
            "• Some fibrotic conditions can be managed to slow progression with specialist care.\n"
            "• Avoid smoking and minimize exposure to lung irritants.\n"
            "• A clinician may request CT imaging and pulmonary function testing."
        ),
        "complications": (
            "Potential complications if neglected (if confirmed by a doctor):\n"
            "• Gradual decline in lung function and chronic low oxygen.\n"
            "• Increased strain on the heart/lung circulation.\n"
            "• Acute worsening episodes can occur in certain fibrotic diseases."
        ),
    },

    "Covid19": {
        "factors": (
            "Factors that may influence this prediction (educational):\n"
            "• Certain bilateral opacity patterns that can appear in viral infections.\n"
            "• Peripheral or diffuse changes sometimes seen in COVID-like presentations.\n"
            "• X-ray alone is not sufficient for confirmation without clinical context."
        ),
        "reversibility": (
            "Possibility of improvement & general recommendations (educational):\n"
            "• Many cases improve with appropriate medical guidance depending on severity.\n"
            "• Clinical confirmation may involve symptom assessment and lab testing.\n"
            "• Seek urgent care if breathing becomes difficult or oxygen levels drop."
        ),
        "complications": (
            "Potential complications if neglected (if confirmed by a doctor):\n"
            "• Worsening pneumonia and oxygenation problems.\n"
            "• Need for advanced respiratory support in severe cases.\n"
            "• Broader systemic complications depending on patient risk factors."
        ),
    },

    "Mass_Opacity_like": {
        "factors": (
            "Factors that may influence this prediction (educational):\n"
            "• Localized mass/opacity patterns and density differences.\n"
            "• Asymmetry or well-defined abnormal regions may increase model confidence.\n"
            "• X-ray cannot confirm cancer; additional imaging is usually needed."
        ),
        "reversibility": (
            "Possibility of improvement & general recommendations (educational):\n"
            "• This result suggests a mass/opacity-like pattern, not a confirmed diagnosis.\n"
            "• A clinician may recommend CT imaging and specialist review.\n"
            "• Earlier evaluation typically improves management options."
        ),
        "complications": (
            "Potential complications if neglected (if confirmed by a doctor):\n"
            "• Progression of the underlying condition and delayed treatment.\n"
            "• Worsening respiratory symptoms depending on location/size.\n"
            "• More complex treatment decisions if evaluation is delayed."
        ),
    },
}


def is_no_finding(label: str) -> bool:
    if not label:
        return True
    return label in NO_FINDING_ALIASES


def get_education_blocks(top1_label: str):
    """
    Returns a dict with 3 text blocks OR None if label is No-finding / Normal.
    """
    if is_no_finding(top1_label):
        return None

    blocks = EDU_TEXT.get(top1_label)
    if not blocks:
        # fallback generic educational Summary
        return {
            "factors": (
                "Factors that may influence this prediction (educational):\n"
                "• The model relies on learned visual patterns (density, texture, distribution).\n"
                "• Image quality and positioning can affect predictions."
            ),
            "reversibility": (
                "Possibility of improvement & general recommendations (educational):\n"
                "• Please consult a clinician for confirmation and management.\n"
                "• Additional tests or imaging may be required."
            ),
            "complications": (
                "Potential complications if neglected (if confirmed by a doctor):\n"
                "• Complications depend on the confirmed condition and severity.\n"
                "• Seek medical attention if symptoms worsen."
            ),
        }

    return blocks
