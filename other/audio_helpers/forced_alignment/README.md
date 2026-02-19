# Forced Alignment Tools Comparison

This folder contains scripts to compare word/phoneme boundary detection across multiple forced alignment tools. These tools are the scientific standard for determining exactly where words begin and end in spoken audio.

## Overview of Tools

### 1. OpenAI Whisper (Easiest)
- **What it is**: State-of-the-art speech recognition model from OpenAI
- **Pros**: Easy to install, no external dependencies, good accuracy, GPU-accelerated
- **Cons**: Designed for transcription (not alignment), boundaries may be less precise
- **Best for**: Quick analysis, when you don't have a transcript

### 2. WhisperX (Better Whisper)
- **What it is**: Enhanced Whisper with wav2vec2-based word alignment
- **Pros**: More precise timing than vanilla Whisper, pip installable, GPU-accelerated
- **Cons**: Requires additional models download, slightly more complex
- **Best for**: When you want Whisper convenience with better alignment precision
- **Website**: https://github.com/m-bain/whisperX

### 3. Montreal Forced Aligner (MFA) (Gold Standard)
- **What it is**: Purpose-built forced aligner used in phonetics research
- **Pros**: Phoneme-level precision, actively maintained, well-documented
- **Cons**: Requires conda, needs acoustic model download, steeper learning curve
- **Best for**: Research papers, phonetic analysis, when precision matters
- **Website**: https://montreal-forced-aligner.readthedocs.io/

### 4. Gentle
- **What it is**: Robust forced aligner built on Kaldi
- **Pros**: Good accuracy, REST API available, handles disfluencies well
- **Cons**: Requires Docker or complex local installation
- **Best for**: Subtitle generation, when audio quality varies
- **Website**: https://github.com/lowerquality/gentle

### 5. NVIDIA NeMo (Research-Grade)
- **What it is**: NVIDIA's conversational AI toolkit with CTC-based forced alignment
- **Pros**: Production-quality, GPU-accelerated, actively developed by NVIDIA
- **Cons**: Large installation (~2GB+), requires CUDA for best performance
- **Best for**: When you need research-grade alignment with modern neural models
- **Website**: https://docs.nvidia.com/deeplearning/nemo/

### 6. WebMAUS (BAS - Gold Standard for Phonetics)
- **What it is**: Web service from Bavarian Archive for Speech Signals, established in phonetics research
- **Pros**: No installation needed (REST API), gold standard in phonetics literature, produces TextGrids
- **Cons**: Requires internet, audio uploaded to external servers, rate limited
- **Best for**: Phonetics research, when citing established methods, no local setup wanted
- **Website**: https://clarin.phonetik.uni-muenchen.de/BASWebServices/

### 7. Penn Phonetics Lab Forced Aligner (P2FA)
- **What it is**: Classic forced aligner from UPenn, based on HTK
- **Pros**: Well-established in literature, produces Praat TextGrids
- **Cons**: Requires HTK license (free for non-commercial), older, Python 2 originally
- **Best for**: Legacy compatibility, when citing older research methods
- **Website**: https://babel.ling.upenn.edu/phonetics/old_website_2015/p2fa/

---

## Installation Instructions

### Whisper (Required - Easiest)

```powershell
# Install with pip
pip install openai-whisper

# For GPU acceleration (optional but recommended)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### WhisperX (Better Alignment)

```powershell
# Install with pip (requires torch already installed)
pip install whisperx
```

### NVIDIA NeMo (Research-Grade)

```powershell
# Full installation (large, ~2GB+)
pip install nemo_toolkit[asr]

# Or minimal installation
pip install nemo_toolkit[asr] --no-deps
pip install torch torchaudio omegaconf hydra-core pytorch-lightning
```

### WebMAUS (No Installation - Web Service)

```powershell
# No installation needed! Just ensure requests is installed:
pip install requests

# WebMAUS is a REST API - audio is uploaded to BAS servers (Germany)
# For sensitive data, use local tools (MFA, Gentle) instead
```

### Montreal Forced Aligner (Recommended)

**⚠️ NOTE: The standard conda install can take 30-60+ minutes to solve dependencies.**
**Use Option A (mamba) for a much faster installation (~5-10 min).**

#### Option A: FAST Installation (using mamba)

```powershell
# 1. Install mamba (faster conda solver)
conda install -c conda-forge mamba

# 2. Create MFA environment with mamba (MUCH faster)
mamba create -n mfa -c conda-forge montreal-forced-aligner

# 3. Activate environment
conda activate mfa

# 4. Download English acoustic model and dictionary
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
```

#### Option B: Standard Installation (slow, 30-60+ min)

```powershell
# 1. Install conda/miniconda if you don't have it
# Download from: https://docs.conda.io/en/latest/miniconda.html

# 2. Create MFA environment (WARNING: can take 30-60+ minutes)
conda create -n mfa -c conda-forge montreal-forced-aligner

# 3. Activate environment
conda activate mfa

# 4. Download English acoustic model and dictionary
mfa model download acoustic english_us_arpa
mfa model download dictionary english_us_arpa
```

### Gentle (Docker method - easiest)

```powershell
# 1. Install Docker Desktop for Windows
# Download from: https://www.docker.com/products/docker-desktop

# 2. Pull and run Gentle
docker pull lowerquality/gentle
docker run -p 8765:8765 lowerquality/gentle
# Gentle will be available at http://localhost:8765
```

### P2FA (Advanced - Optional)

P2FA requires HTK which has licensing restrictions. For most users, MFA is a better modern alternative that produces similar output.

If you need P2FA specifically:
1. Register for HTK license at http://htk.eng.cam.ac.uk/
2. Follow installation at https://babel.ling.upenn.edu/phonetics/old_website_2015/p2fa/

---

## Quick Start

### Step 1: Test with Whisper (no setup needed beyond pip install)

```powershell
cd other\audio_helpers\forced_alignment
python align_with_whisper.py
```

### Step 2: Test with WhisperX (better alignment than vanilla Whisper)

```powershell
python align_with_whisperx.py
```

### Step 3: Test with NeMo (NVIDIA research-grade)

```powershell
python align_with_nemo.py
```

### Step 4: Test with MFA (after conda setup)

```powershell
conda activate mfa
python align_with_mfa.py
```

### Step 5: Test with Gentle (after Docker setup)

```powershell
# In one terminal, start Gentle:
docker run -p 8765:8765 lowerquality/gentle

# In another terminal:
python align_with_gentle.py
```

### Step 6: Test with WebMAUS (no setup - web service)

```powershell
# Requires internet connection - audio uploaded to BAS servers
python align_with_webmaus.py
```

### Step 7: Compare all results

```powershell
python compare_alignments.py
```

---

## Output Format

All tools produce timing information in a standardized format:

```
Word: "wall"
Start: 1.387 seconds
End: 1.634 seconds
Duration: 247 ms
```

The comparison script will show you:
- How closely the tools agree
- Mean/max difference in word boundaries
- Which tool to trust if they disagree

---

## Understanding the Results

### What is "good" agreement?

| Difference | Interpretation |
|------------|----------------|
| < 10 ms | Excellent - tools agree |
| 10-30 ms | Good - within human perception threshold |
| 30-50 ms | Acceptable - typical variation |
| > 50 ms | Investigate - possible issue with audio or transcript |

### Why might tools disagree?

1. **Different definitions of word boundaries** - Some include aspiration, some don't
2. **Audio quality** - Background noise affects alignment
3. **Speaking rate** - Fast speech is harder to align
4. **Acoustic model training data** - Models trained on different corpora

---

## Files in This Folder

| File | Description |
|------|-------------|
| `align_with_whisper.py` | Align using OpenAI Whisper |
| `align_with_mfa.py` | Align using Montreal Forced Aligner |
| `align_with_gentle.py` | Align using Gentle (requires Docker) |
| `compare_alignments.py` | Compare results from all tools |
| `README.md` | This file |

---

## Recommended Workflow

1. **Start with Whisper** - Quick, easy, gives you a baseline
2. **Run MFA** - The research-grade tool, compare to Whisper
3. **If they agree** - You're done, use either result
4. **If they disagree** - Run Gentle as a tiebreaker, or manually verify in Praat

---

## For Your Specific Audio Files

Your audio files:
- `fullsentence.wav` - Full sentence containing the word "wall"
- `targetwall.wav` - Isolated word "wall"

The scripts are pre-configured to analyze these files and find:
1. Where "wall" starts and ends in `fullsentence.wav`
2. Whether `targetwall.wav` was cut at the correct boundaries
3. If there's extra silence/audio that should be trimmed

---

## References

- Whisper: Radford et al. (2022). "Robust Speech Recognition via Large-Scale Weak Supervision"
- MFA: McAuliffe et al. (2017). "Montreal Forced Aligner: Trainable Text-Speech Alignment Using Kaldi"
- Gentle: Based on Kaldi ASR toolkit
- P2FA: Yuan & Liberman (2008). "Speaker identification on the SCOTUS corpus"
