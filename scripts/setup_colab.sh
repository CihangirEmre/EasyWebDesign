#!/bin/bash
# Colab ortam kurulumu (A100, tek GPU).
# Kullanım (bir Colab hücresinde): !bash scripts/setup_colab.sh
#
# Kurulum sırası önemli: requirements-generation.txt (torch/accelerate/
# bitsandbytes) önce, requirements-grounding.txt EN SON kurulur — o dosya
# transformers'ı GitHub'dan (Qwen3-VL ve Qwen2.5-VL desteği için bleeding
# edge) kurar ve başka bir paket onu stable sürüme downgrade etmemeli.
set -e

pip install -q -r requirements.txt
pip install -q -r requirements-generation.txt
pip install -q -r requirements-grounding.txt

playwright install --with-deps chromium