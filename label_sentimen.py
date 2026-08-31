"""
Sentiment labeling for vibecoding dataset.
Uses cardiffnlp/twitter-xlm-roberta-base-sentiment model.
Labels: positive, neutral, negative

Usage:
  python label_sentimen.py                  # rows 1000-2000
  python label_sentimen.py 0 1000           # rows 0-1000
  python label_sentimen.py 2000 1000        # rows 2000-3000
"""

import re
import sys
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from scipy.special import softmax

# --- Config ---
INPUT_CSV = "data/raw/vibecoding_relevant_10000.csv"
BATCH_SIZE = 32
MODEL_NAME = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
MAX_LENGTH = 128

# --- Parse CLI args ---
START_ROW = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
N_ROWS = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
OUTPUT_CSV = f"data/raw/vibecoding_sentimen_{START_ROW}_{START_ROW + N_ROWS}.csv"

# --- Text cleaning ---
def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove @mentions
    text = re.sub(r"@\w+", "", text)
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

# --- Load data ---
print(f"Loading rows {START_ROW}-{START_ROW + N_ROWS} from {INPUT_CSV} ...")
# sep=None + engine="python" membuat pandas mendeteksi delimiter sendiri.
# Diperlukan karena vibecoding_relevant_10000.csv memakai ';' sementara file
# keluaran sentimen memakai ','; tanpa ini file ';' terparsing jadi satu kolom
# dan akses df["text"] gagal.
df = pd.read_csv(
    INPUT_CSV, sep=None, engine="python", encoding="utf-8-sig"
).iloc[START_ROW:START_ROW + N_ROWS]
print(f"Loaded {len(df)} rows. Columns: {df.columns.tolist()}")

# Clean text
df["text_clean"] = df["text"].apply(clean_text)

# --- Load model ---
print(f"Loading model: {MODEL_NAME} ...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
model.eval()

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model = model.to(device)
print(f"Using device: {device}")

# Model label mapping (cardiffnlp/twitter-xlm-roberta-base-sentiment)
# 0 -> negative, 1 -> neutral, 2 -> positive
label_map = {0: "negative", 1: "neutral", 2: "positive"}

# --- Inference ---
sentiments = []
scores = []
prob_neg = []
prob_neu = []
prob_pos = []

texts = df["text_clean"].tolist()
n_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

print(f"Running inference on {len(texts)} texts in {n_batches} batches (batch_size={BATCH_SIZE}) ...")

with torch.no_grad():
    for i in range(0, len(texts), BATCH_SIZE):
        batch_texts = texts[i:i + BATCH_SIZE]
        batch_idx = i // BATCH_SIZE + 1
        print(f"  Batch {batch_idx}/{n_batches} ...", end="\r")

        # Tokenize
        encoded = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        ).to(device)

        # Forward pass
        outputs = model(**encoded)
        logits = outputs.logits.cpu().numpy()

        # Softmax probabilities
        probs = softmax(logits, axis=1)

        for j in range(len(batch_texts)):
            pred_idx = int(probs[j].argmax())
            sentiments.append(label_map[pred_idx])
            scores.append(float(probs[j][pred_idx]))
            prob_neg.append(float(probs[j][0]))
            prob_neu.append(float(probs[j][1]))
            prob_pos.append(float(probs[j][2]))

print(f"\nInference complete.")

# --- Save results ---
df["sentiment"] = sentiments
df["sentiment_score"] = scores
df["prob_negative"] = prob_neg
df["prob_neutral"] = prob_neu
df["prob_positive"] = prob_pos

print(f"\nSentiment distribution:")
print(df["sentiment"].value_counts())

df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
print(f"\nSaved to {OUTPUT_CSV}")
