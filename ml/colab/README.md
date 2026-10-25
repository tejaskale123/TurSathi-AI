# 🌾 TurSathi AI — Google Colab Pipeline with Google Drive Persistence

This guide details how to run the fine-tuning pipeline on **Google Colab** with **Google Drive mounting**, **automatic checkpointing** (every 10 epochs and on best validation accuracy), and **strict 5-class OOD enforcement**.

---

## 📂 Step 1: Set Up Your Google Drive Folder

1. Open your **Google Drive** ([drive.google.com](https://drive.google.com)).
2. In **My Drive**, create a new folder named exactly:
   ```
   Tur Disease Dataset
   ```
3. Upload the following files from your local project into that folder:
   - [`Tur_Disease_Dataset_Colab_Ready.zip`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/Tur_Disease_Dataset_Colab_Ready.zip) (90.1 MB)
   - [`train_colab_pipeline.py`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/colab/train_colab_pipeline.py)

Your Google Drive folder structure will look like this:
```
Google Drive/MyDrive/
└── Tur Disease Dataset/
    ├── Tur_Disease_Dataset_Colab_Ready.zip
    └── train_colab_pipeline.py
```

---

## 🚀 Step 2: Open Google Colab

1. Navigate to [Google Colab](https://colab.research.google.com).
2. Click **Upload** and select:
   [`TurSathi_FineTuning_and_OOD_Colab.ipynb`](file:///c:/Users/admin/OneDrive/Documents/Desktop/TurSathi%20AI/ml/colab/TurSathi_FineTuning_and_OOD_Colab.ipynb).
3. Ensure GPU hardware acceleration is selected:
   - Click **Runtime** > **Change runtime type**.
   - Hardware accelerator: **GPU** (T4 or higher).

---

## 🏃 Step 3: Run the Cells Sequentially

### Cell 1: Mount Google Drive
- Mounts `/content/drive` and automatically initializes:
  - `/content/drive/MyDrive/Tur Disease Dataset/checkpoints/`
  - `/content/drive/MyDrive/Tur Disease Dataset/outputs/`

### Cell 2: GPU Check & Dependencies
- Verifies CUDA GPU availability and installs required evaluation libraries.

### Cell 3: Fast Local Unpack
- Copies `Tur_Disease_Dataset_Colab_Ready.zip` from your Google Drive into the local Colab ephemeral SSD (`/content/dataset/`) to guarantee fast training throughput without Drive network I/O throttling.

### Cell 4: Train with Live Drive Checkpointing
- Runs 20 epochs of fine-tuning with cosine annealing.
- **Checkpoints saved directly to Google Drive**:
  - `checkpoints/best_model_checkpoint.pth` (saved whenever validation accuracy reaches a new peak).
  - `checkpoints/checkpoint_epoch_10.pth` (periodic 10-epoch backup).
  - `checkpoints/checkpoint_epoch_20.pth`.
- **Final Models & Metrics mirrored to Google Drive**:
  - `outputs/best_pigeonpea_disease_final_efficientnet_b0.pth`
  - `outputs/ood_feature_profile.json` (1280-D centroids, covariance matrix, and distance rejection thresholds)
  - `outputs/quantized_pigeonpea_disease_efficientnet_b0.pth` (INT8 dynamic quantization)
  - `outputs/training_report.json` & `outputs/confusion_matrix.txt`

### Cell 5 & 6: Evaluation & OOD Defense Verification
- Generates accuracy and loss plots.
- Evaluates the 41 unseen/external test images to verify the **100% strict rejection rate** for non-database conditions.

### Cell 7: Verify Drive Backups & Download
- Prints the list of files safely written to your Google Drive.
- Triggers a browser download of `tursathi_trained_artifacts.zip` as an additional local backup.

---

## 🛡️ Strict 5-Class Closed-Set Guarantee

The model is strictly restricted to:
1. `Healthy`
2. `Leaf_Spot` *(Cercospora Leaf Spot)*
3. `Leaf_webber` *(Maruca vitrata / Cydia critica)*
4. `Sterilic_mosaic` *(Sterility Mosaic Disease / SMD)*
5. `Wilt` *(Fusarium Wilt)*

Any external pigeon pea disease (such as Alternaria blight, Phytophthora, Powdery mildew) or foreign plant leaf will exceed the calibrated Mahalanobis & Cosine distance thresholds and be strictly rejected with:
> **`"This specific condition/class does not exist in the current database"`**
