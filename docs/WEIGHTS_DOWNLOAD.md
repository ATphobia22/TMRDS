# TMRDS Model Weight Download Instructions

## 1. MedicalNet 3D-ResNet (Tencent Med3D)

**Preferred (automatic via MONAI)**
```bash
pip install monai huggingface_hub
# Weights download on first MedicalNetBackbone(pretrained=True) call
```

**Manual Hugging Face CLI**
```bash
# ResNet-50 (recommended default)
huggingface-cli download TencentMedicalNet/MedicalNet-Resnet50 \
    resnet_50_23dataset.pth \
    --local-dir ./weights/medicalnet

# Other depths
huggingface-cli download TencentMedicalNet/MedicalNet-Resnet10  resnet_10_23dataset.pth  --local-dir ./weights/medicalnet
huggingface-cli download TencentMedicalNet/MedicalNet-Resnet18  resnet_18_23dataset.pth  --local-dir ./weights/medicalnet
huggingface-cli download TencentMedicalNet/MedicalNet-Resnet34  resnet_34_23dataset.pth  --local-dir ./weights/medicalnet
huggingface-cli download TencentMedicalNet/MedicalNet-Resnet101 resnet_101_23dataset.pth --local-dir ./weights/medicalnet
```

**Python load**
```python
from engines.medicalnet_backbone import MedicalNetBackbone
backbone = MedicalNetBackbone(depth=50, pretrained=True, device="cuda")
# or offline
backbone.load_weights_manual("./weights/medicalnet/resnet_50_23dataset.pth")
```

Citation: Chen et al., *Med3D: Transfer Learning for 3D Medical Image Analysis*, arXiv:1904.00625

---

## 2. Meditron-7B / 70B

```bash
# Requires Hugging Face account + license acceptance for Llama-2 derivatives
huggingface-cli download epfl-llm/meditron-7b --local-dir ./weights/meditron-7b
# 70B needs multi-GPU / large disk
huggingface-cli download epfl-llm/meditron-70b --local-dir ./weights/meditron-70b
```

vLLM serve example:
```bash
python -m vllm.entrypoints.openai.api_server \
    --model epfl-llm/meditron-7b \
    --tensor-parallel-size 1
```

---

## 3. AlphaFold 3

**Official (academic non-commercial)**
1. Request parameters: https://github.com/google-deepmind/alphafold3
2. Download model parameters: https://storage.googleapis.com/alphafold3/af3.bin.zst
3. Genetic databases (~1 TB recommended SSD)

**Open alternatives**
- OpenFold3 (NVIDIA NIM / Linux Foundation Class 1)
- Ligo-Biosciences/AlphaFold3 (research)

**Cloud (no local weights)**
- AlphaFold Server: https://alphafoldserver.com
- Google Cloud Model Garden AlphaFold 3

---

## 4. Directory Layout Recommendation

```
weights/
├── medicalnet/
│   ├── resnet_50_23dataset.pth
│   └── ...
├── meditron-7b/
└── alphafold3/
    └── af3.bin.zst
```

Set environment variables:
```bash
export MEDICALNET_WEIGHTS=./weights/medicalnet
export MEDITRON_PATH=./weights/meditron-7b
export AF3_MODEL_DIR=./weights/alphafold3
```
