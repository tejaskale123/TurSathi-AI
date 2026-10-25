import json
from pathlib import Path

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# 🌾 TurSathi AI — Google Colab Retraining Pipeline with Google Drive Persistence\n",
                "### Fine-Tuning EfficientNet-B0 with 1280-D Feature Extraction, OOD Rejection Guard, Pruning, & INT8 Quantization\n",
                "\n",
                "**Key Architecture Highlights**:\n",
                "1. **Strict 5-Class Closed Set**: Exclusively recognizes `['Healthy', 'Leaf_Spot', 'Leaf_webber', 'Sterilic_mosaic', 'Wilt']`.\n",
                "2. **Layer 3 Feature Extraction & OOD Guard**: Computes class centroids and Mahalanobis/Cosine distance thresholds. If an external leaf disease, non-tur crop, or unknown condition is detected, it strictly flags:\n",
                "   > **`'This specific condition/class does not exist in the current database'`**\n",
                "3. **Automatic Google Drive Backup**: Periodically checkpoints model weights (every 10 epochs and on best validation accuracy) to `/content/drive/MyDrive/Tur Disease Dataset/checkpoints/` to safeguard against disconnects.\n",
                "4. **L1 Weight Pruning & INT8 Quantization**: Creates an ultra-fast, lightweight production model ready for deployment."
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 📂 Step 1: Mount Google Drive\n",
                "This mounts your Google Drive under `/content/drive`. Ensure you have placed `Tur_Disease_Dataset_Colab_Ready.zip` inside the folder **`Tur Disease Dataset`** on your Google Drive."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "from google.colab import drive\n",
                "import os, sys, shutil\n",
                "from pathlib import Path\n",
                "\n",
                "# Mount Google Drive\n",
                "drive.mount('/content/drive')\n",
                "\n",
                "# Drive directory configuration\n",
                "DRIVE_BASE_DIR = Path('/content/drive/MyDrive/Tur Disease Dataset')\n",
                "DRIVE_CHECKPOINTS_DIR = DRIVE_BASE_DIR / 'checkpoints'\n",
                "DRIVE_OUTPUTS_DIR = DRIVE_BASE_DIR / 'outputs'\n",
                "\n",
                "# Ensure destination folders exist on Google Drive\n",
                "DRIVE_BASE_DIR.mkdir(parents=True, exist_ok=True)\n",
                "DRIVE_CHECKPOINTS_DIR.mkdir(parents=True, exist_ok=True)\n",
                "DRIVE_OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)\n",
                "\n",
                "print('Google Drive connected successfully!')\n",
                "print(f'Drive Base Folder:       {DRIVE_BASE_DIR}')\n",
                "print(f'Drive Checkpoints Folder: {DRIVE_CHECKPOINTS_DIR}')\n",
                "print(f'Drive Final Outputs:     {DRIVE_OUTPUTS_DIR}')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## ⚙️ Step 2: GPU Verification & Dependencies"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "!nvidia-smi\n",
                "import torch\n",
                "print(f'PyTorch Version: {torch.__version__}')\n",
                "print(f'CUDA Available: {torch.cuda.is_available()}')\n",
                "if torch.cuda.is_available():\n",
                "    print(f'GPU Device: {torch.cuda.get_device_name(0)}')\n",
                "    print(f'VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB')\n",
                "\n",
                "# Install required dependencies\n",
                "!pip install -q scikit-learn matplotlib seaborn pillow"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 📦 Step 3: Load & Extract Dataset to Local Fast Storage\n",
                "We copy the dataset zip from `/content/drive/MyDrive/Tur Disease Dataset/Tur_Disease_Dataset_Colab_Ready.zip` to the local Colab ephemeral SSD (`/content/dataset/`) to guarantee maximum GPU throughput and avoid Drive I/O bottlenecks."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import zipfile\n",
                "\n",
                "DRIVE_ZIP = DRIVE_BASE_DIR / 'Tur_Disease_Dataset_Colab_Ready.zip'\n",
                "LOCAL_ZIP = Path('/content/Tur_Disease_Dataset_Colab_Ready.zip')\n",
                "LOCAL_DATASET_DIR = Path('/content/dataset')\n",
                "\n",
                "if DRIVE_ZIP.exists():\n",
                "    print(f'Found dataset on Google Drive: {DRIVE_ZIP}')\n",
                "    print('Copying to local SSD storage for high-speed training...')\n",
                "    shutil.copy2(DRIVE_ZIP, LOCAL_ZIP)\n",
                "elif LOCAL_ZIP.exists():\n",
                "    print(f'Found dataset uploaded locally at: {LOCAL_ZIP}')\n",
                "else:\n",
                "    raise FileNotFoundError(\n",
                "        f'Dataset zip not found! Please place Tur_Disease_Dataset_Colab_Ready.zip inside:\\n'\n",
                "        f'\"{DRIVE_BASE_DIR}\" on your Google Drive, or upload it to /content/'\n",
                "    )\n",
                "\n",
                "# Extract dataset\n",
                "print(f'Extracting {LOCAL_ZIP} to {LOCAL_DATASET_DIR}...')\n",
                "with zipfile.ZipFile(LOCAL_ZIP, 'r') as z:\n",
                "    z.extractall(LOCAL_DATASET_DIR)\n",
                "\n",
                "print('\\nDataset verification:')\n",
                "for split in ['train', 'val', 'test']:\n",
                "    p = LOCAL_DATASET_DIR / split\n",
                "    classes = sorted([d.name for d in p.iterdir() if d.is_dir()])\n",
                "    count = sum(len(list((p / c).glob('*.*'))) for c in classes)\n",
                "    print(f'  [{split.upper()}] {count} images across {len(classes)} classes: {classes}')\n",
                "\n",
                "ood_p = LOCAL_DATASET_DIR / 'ood_evaluation'\n",
                "if ood_p.exists():\n",
                "    ood_count = len(list(ood_p.glob('*.*')))\n",
                "    print(f'  [OOD EVALUATION] {ood_count} external images loaded for rejection testing.')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🧠 Step 4: Run Fine-Tuning Pipeline with Live Google Drive Checkpointing\n",
                "This initiates:\n",
                "- **20 Epochs Fine-Tuning** with Cosine Annealing Learning Rate\n",
                "- **Automatic Checkpoints every 10 epochs and on best validation accuracy** saved directly to `/content/drive/MyDrive/Tur Disease Dataset/checkpoints/`\n",
                "- **1280-D Latent Feature Extraction** and Centroid calculation\n",
                "- **Regularized Mahalanobis and Cosine distance threshold calibration** for OOD rejection\n",
                "- **L1 Weight Pruning** (15% sparsity)\n",
                "- **INT8 Post-Training Dynamic Quantization**\n",
                "- **Direct mirror of final `.pth` models and reports** to `/content/drive/MyDrive/Tur Disease Dataset/outputs/`"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "# Verify train_colab_pipeline.py is available\n",
                "PIPELINE_SCRIPT = Path('/content/train_colab_pipeline.py')\n",
                "DRIVE_SCRIPT = DRIVE_BASE_DIR / 'train_colab_pipeline.py'\n",
                "\n",
                "if not PIPELINE_SCRIPT.exists() and DRIVE_SCRIPT.exists():\n",
                "    shutil.copy2(DRIVE_SCRIPT, PIPELINE_SCRIPT)\n",
                "    print(f'Copied pipeline script from Google Drive: {DRIVE_SCRIPT}')\n",
                "\n",
                "assert PIPELINE_SCRIPT.exists(), (\n",
                "    'train_colab_pipeline.py not found! Please upload it to /content/ '\n",
                "    f'or place it in \"{DRIVE_BASE_DIR}\"'\n",
                ")\n",
                "\n",
                "# Run training with Drive checkpointing\n",
                "!python /content/train_colab_pipeline.py \\\n",
                "    --data_dir /content/dataset \\\n",
                "    --ood_dir /content/dataset/ood_evaluation \\\n",
                "    --output_dir /content/outputs \\\n",
                "    --checkpoint_dir \"/content/drive/MyDrive/Tur Disease Dataset/checkpoints\" \\\n",
                "    --drive_output_dir \"/content/drive/MyDrive/Tur Disease Dataset/outputs\" \\\n",
                "    --checkpoint_interval 10 \\\n",
                "    --epochs 20 \\\n",
                "    --batch_size 16"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 📊 Step 5: Learning Curves & Confusion Matrix"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "import json\n",
                "import matplotlib.pyplot as plt\n",
                "import numpy as np\n",
                "\n",
                "report_file = Path('/content/outputs/training_report.json')\n",
                "if not report_file.exists():\n",
                "    report_file = DRIVE_OUTPUTS_DIR / 'training_report.json'\n",
                "\n",
                "with open(report_file, 'r') as f:\n",
                "    report = json.load(f)\n",
                "\n",
                "history = report['history']\n",
                "epochs = range(1, len(history['train_loss']) + 1)\n",
                "\n",
                "fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))\n",
                "\n",
                "# Accuracy Curve\n",
                "ax1.plot(epochs, [a * 100 for a in history['train_acc']], 'b-o', label='Train Accuracy')\n",
                "ax1.plot(epochs, [a * 100 for a in history['val_acc']], 'g-s', label='Val Accuracy')\n",
                "ax1.set_title('Training & Validation Accuracy (%)', fontsize=13)\n",
                "ax1.set_xlabel('Epoch')\n",
                "ax1.set_ylabel('Accuracy (%)')\n",
                "ax1.legend()\n",
                "ax1.grid(True, linestyle='--', alpha=0.5)\n",
                "\n",
                "# Loss Curve\n",
                "ax2.plot(epochs, history['train_loss'], 'r-o', label='Train Loss')\n",
                "ax2.plot(epochs, history['val_loss'], 'm-s', label='Val Loss')\n",
                "ax2.set_title('Training & Validation Loss', fontsize=13)\n",
                "ax2.set_xlabel('Epoch')\n",
                "ax2.set_ylabel('Cross-Entropy Loss')\n",
                "ax2.legend()\n",
                "ax2.grid(True, linestyle='--', alpha=0.5)\n",
                "\n",
                "plt.tight_layout()\n",
                "plt.savefig('/content/outputs/learning_curves.png', dpi=150)\n",
                "if DRIVE_OUTPUTS_DIR.exists():\n",
                "    plt.savefig(DRIVE_OUTPUTS_DIR / 'learning_curves.png', dpi=150)\n",
                "plt.show()\n",
                "\n",
                "print(f\"Best Validation Accuracy: {report['best_val_accuracy']*100:.2f}%\")\n",
                "print(f\"Final Test Accuracy:       {report['test_accuracy']*100:.2f}%\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🛡️ Step 6: Verify Out-of-Distribution (OOD) Strict Rejection\n",
                "Evaluates the rejection rate on the external/unseen test images:"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "ood_eval = report.get('ood_evaluation')\n",
                "if ood_eval:\n",
                "    print('='*60)\n",
                "    print(f\"OOD External Images Tested:  {ood_eval['total_tested']}\")\n",
                "    print(f\"Strictly Rejected:           {ood_eval['rejected_count']}\")\n",
                "    print(f\"Strict Rejection Rate:       {ood_eval['rejection_rate_percent']:.2f}%\")\n",
                "    print('='*60)\n",
                "    print('Sample Decision Log:')\n",
                "    for s in ood_eval.get('sample_verdicts', []):\n",
                "        print(f\"  • {s['image']} -> {s['status']} (Dist: {s['min_mahalanobis']:.2f}, Conf: {s['confidence']*100:.1f}%)\")"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 🔒 Step 7: Verify Google Drive Backups & Optional Direct Download\n",
                "Verify that all trained weights, checkpoints, and profiles are safely persisted in your Google Drive."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [
                "print('=== GOOGLE DRIVE CHECKPOINTS SAVED ===')\n",
                "for f in sorted(DRIVE_CHECKPOINTS_DIR.iterdir()):\n",
                "    sz_mb = f.stat().st_size / (1024 * 1024)\n",
                "    print(f'  • {f.name} ({sz_mb:.2f} MB)')\n",
                "\n",
                "print('\\n=== GOOGLE DRIVE FINAL OUTPUTS SAVED ===')\n",
                "for f in sorted(DRIVE_OUTPUTS_DIR.iterdir()):\n",
                "    sz_mb = f.stat().st_size / (1024 * 1024)\n",
                "    print(f'  • {f.name} ({sz_mb:.2f} MB)')\n",
                "\n",
                "# Optional direct browser download\n",
                "from google.colab import files\n",
                "shutil.make_archive('/content/tursathi_trained_artifacts', 'zip', '/content/outputs')\n",
                "print('\\nTriggering browser download of tursathi_trained_artifacts.zip as backup...')\n",
                "files.download('/content/tursathi_trained_artifacts.zip')"
            ]
        }
    ],
    "metadata": {
        "accelerator": "GPU",
        "colab": {
            "gpuType": "T4",
            "provenance": []
        },
        "language_info": {
            "name": "python"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = Path("ml/colab/TurSathi_FineTuning_and_OOD_Colab.ipynb")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, indent=2)

print(f"Successfully generated updated {output_path} with Google Drive integration!")
