#!/bin/bash
# Colab ortam kurulumu (A100, tek GPU).
# Kullanım (bir Colab hücresinde): !bash scripts/setup_colab.sh
#
# Kurulum sırası önemli: requirements-generation.txt (artık sadece
# google-genai — Aşama 4 Gemini API kullanıyor, yerel model yok) önce,
# requirements-grounding.txt EN SON kurulur — o dosya transformers'ı
# GitHub'dan (Qwen3-VL desteği için bleeding edge) kurar ve başka bir paket
# onu stable sürüme downgrade etmemeli.
#
# Aşama 4 için GEMINI_API_KEY ortam değişkenini ayrıca ayarlaman gerekiyor:
#   import os; os.environ["GEMINI_API_KEY"] = "..."
set -e

pip install -q -r requirements.txt
pip install -q -r requirements-generation.txt
pip install -q -r requirements-grounding.txt

playwright install --with-deps chromium