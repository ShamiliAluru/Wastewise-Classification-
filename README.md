# Wastewise

Wastewise is a polished image-and-description waste sorting assistant. It suggests one of four broad next-step groups—biodegradable/compostable, recyclable material, hazardous/special handling, or general waste/check first—and gives practical, cautious guidance. It does not claim to know local collection acceptance rules.

## Architecture

```text
Streamlit interface (app.py)
   ├── photo ──> image validation ──> optional trained Keras model ──> confidence check ──┐
   ├── description ──> transparent keyword helper (no external AI/API) ───────────────────┤
   └── user correction ──────────────────────────────────────────────────────────────────┘
                                      ↓
                        sorting guide + reference links

Training: labeled folders -> MobileNetV2 transfer learning -> models/wastewise.keras
                                                         └-> models/metadata.json
```

The interface is usable before the custom image model is trained: descriptions can produce a **basic keyword suggestion**. If it cannot identify an item, it asks for an item or material description instead of asking the user to choose a broad category. The text helper is not a language model and may not understand unlisted terms. The original cats-vs-dogs starter ZIP had no waste images; the supplied 12-class archive is prepared in `data_wastewise`.

## Run the interface

**Windows one-click launch:** extract the project ZIP and double-click `Run_Wastewise.bat`. It checks for Python 3.12, sets up the app environment, installs the required packages, trains the model if it is not present, and opens the app. The first setup needs internet access and can take several minutes. Keep the console open while using the app; press Ctrl+C to stop it.

To run manually, use Python 3.12 for the TensorFlow training environment. From this folder:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Streamlit opens the local app in your browser. Try a photo and/or a description. If no model has been trained, the app says so and uses the limited description helper.

## Supplied dataset

The included archive matches the [Garbage Classification 12-class dataset](https://www.kaggle.com/datasets/mostafaabla/garbage-classification). It has 15,515 readable images in 12 folders: battery (945), biological (985), brown-glass (607), cardboard (891), clothes (5,325), green-glass (629), metal (769), paper (1,050), plastic (865), shoes (1,977), trash (697), and white-glass (775). The project removes exact duplicates, drops files with conflicting duplicate labels, and makes seeded, stratified 70/15/15 train/validation/test splits. The split manifest records source paths and hashes.

The image scan found no unreadable files and 19 repeated image copies; copies with conflicting labels are excluded. The classes are uneven: clothes is about a third of the archive, and clothing/shoe images do not always show discarded items. The archive has no source-family IDs, so near-duplicate leakage across random splits cannot be ruled out. Glass colors are separate visual labels but map to the same recyclable guidance. Paint, medicines, e-waste, and food scraps are not separate model classes. The ZIP itself did not include a license file; the source dataset page should be checked before redistribution or public release. This project is for educational use.

The prepared data is included in `data_wastewise/`. To recreate it from the ZIP:

```powershell
python prepare_garbage_dataset.py --archive "C:\Users\23311\Downloads\archive.zip" --output data_wastewise
```

The script refuses to overwrite an existing output folder and writes `preparation_manifest.csv` for traceability.

For TensorFlow training, use a 64-bit Python 3.12 environment (the current app environment is Python 3.13). Install dependencies and train from the Wastewise project folder:

```powershell
py -3.12 -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r requirements.txt -r requirements-ml.txt
.\.venv-ml\Scripts\python.exe train.py --data data_wastewise --epochs 12 --fine-tune-epochs 4
.\.venv-ml\Scripts\python.exe -m streamlit run app.py
```

If the Python launcher cannot find 3.12, install 64-bit Python 3.12 first, then run these commands in the Wastewise folder. Training uses ImageNet-pretrained MobileNetV2 and saves the model to `models/wastewise.keras`; the app loads it automatically. Installing TensorFlow and downloading pretrained weights need internet access. A GPU is optional. Images are streamed and prefetched rather than cached in memory, so large datasets are less likely to exhaust RAM.

## User experience

1. Upload one JPG, PNG, or WebP photo, type a description, or do both.
2. If the file is unreadable, the app asks for a clearer image or a description.
3. A trained model predicts a fine-grained item label. Confident results go straight to the item name, sorting group, and practical handling steps.
4. When the model is unsure, it asks about its leading item guesses with yes/no buttons. If none fit, the person can type the item or material; the app does not ask them to choose a broad waste category.
5. Without a trained model, a transparent keyword helper can make a limited description-based suggestion. If a photo cannot be read but a description is present, the app explains that the guide is based on the description.

## Categories and limits

- **Biodegradable / compostable:** food scraps and yard waste. Soil/dirt is not automatically compostable. Home compost systems have limits; the guide distinguishes a basic backyard pile from other processes.
- **Recyclable material:** common paper/cardboard, plastic, metal, and glass. Aluminum and glass are recyclable examples, not hazardous classes. Acceptance varies; Wastewise does not promise local acceptance.
- **Hazardous / special handling:** batteries, paint/chemicals, medicines, and electronics. The app gives conservative general prompts, not item-specific legal disposal instructions. Follow the label and appropriate collection program.
- **General waste / check first:** clothes and shoes are usually best reused or donated when usable; otherwise check for a textile recovery route. Unclear or mixed items use the cautious fallback guidance. This is a fallback, not a claim that an item must go to landfill.

Handling instructions now include item-specific steps for common dataset labels and typed examples. When uncertain, the app asks a short yes/no item question and then requests a material description if needed. Do not use this prototype to decide how to handle leaking, unlabeled, reactive, or otherwise dangerous material. It cannot assess contamination or identify hidden contents from a photo.

**Model quality limitation:** this is an educational classifier, not a reliable waste authority. It learns the dataset’s photo styles, and labels such as clothing and shoes can depict reusable products rather than waste. Validate on new real-world photos and use per-class precision/recall, not just overall accuracy.

## Technology stack

| Layer | Technology | Role |
|---|---|---|
| Interface | Streamlit | Browser UI, upload controls, confirmation and correction flow |
| Language | Python | App logic, training, and inference |
| Image processing | Pillow | Validate, orient, resize, and convert photos |
| Deep learning | TensorFlow / Keras | Train and load the classifier |
| Transfer learning | MobileNetV2 with ImageNet weights | Reuse learned visual features and fine-tune for waste classes |
| Numeric arrays | NumPy | Format photos for model inference |
| Styling | Custom CSS + Google Fonts | Green visual identity, spacing, hierarchy, responsive layout |
| Guidance | Local Python catalog + EPA reference links | Practical next steps without a paid API or external text model |

## Project structure

```text
Wastewise/
├── app.py                 # Screen layout and user flow
├── train.py               # Model training and held-out test evaluation
├── prepare_garbage_dataset.py # Deduplicate and split the supplied 12-class archive
├── src/
│   ├── catalog.py         # Categories, guidance, class map, text helper
│   ├── inference.py       # Image validation and optional model prediction
│   └── ui.py              # Reusable visual components and CSS
├── requirements.txt       # Lightweight interface dependencies
├── requirements-ml.txt    # Optional TensorFlow/NumPy dependencies
├── README.md              # Setup, architecture, and usage guide
├── data_wastewise/        # Prepared 12-class images, manifest, and attribution (ignored by Git)
└── models/                # Generated model and metadata (ignored by Git)
```

## Next improvement

Review confusing examples and user corrections before adding them to a future dataset. Compare per-class precision/recall and a confusion matrix, not only overall accuracy. Keep hazardous labels conservative. Local disposal lookup can be added later if you choose to support a specific region.
