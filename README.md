🎥 Dubber: Modular and Reproducible Video Dubbing Pipeline

This repository hosts the source code and implementation scripts for our research paper on building a modular, end-to-end pipeline for automatic video dubbing, primarily focusing on translating English videos into Indian regional languages.

The pipeline integrates state-of-the-art open-source components for a complete solution covering transcription, translation, speech synthesis, and optional lip synchronization.

✨ Features

Modular Pipeline: A clearly defined sequence of stages allowing for easy swapping of individual components (ASR, MT, TTS).

Cross-Lingual Dubbing: Optimized for dubbing English content to target languages, including Hindi and other Indian regional languages.

Open-Source Integration: Utilizes robust, publicly available models for core tasks.

Optional Lip Synchronization: Includes a module to generate visually plausible lip movements coherent with the dubbed audio.

Reproducibility: Released with experiment scripts and configuration files to facilitate research replication and benchmarking.

⚙️ Dubbing Pipeline Overview

The system operates in a sequential manner, taking an input video and producing a dubbed video file.

Audio Extraction: The audio track is separated from the input video file (using MoviePy and ffmpeg).

ASR (Automatic Speech Recognition): The English audio is transcribed into text using the powerful Whisper model. Segment-level timestamps are preserved.

Translation (NMT): The English transcript is translated into the target language. We support MarianMT (for offline experiments) and Google Translate (for quick prototyping).

TTS (Text-to-Speech): The translated text is synthesized back into speech using a configurable engine (gTTS baseline or neural TTS like Coqui). The resulting audio segments are concatenated.

Video Composition: The newly synthesized audio track replaces the original audio track in the video.

Optional Lip-Sync (Wav2Lip): For visual coherence, the Wav2Lip inference script is run to re-generate the video frames, synchronizing the actor's lips with the new dubbed audio.

🚀 Setup and Installation

Prerequisites

Python 3.10+

ffmpeg (must be installed and accessible in your system path)

A suitable GPU is highly recommended for practical runtimes, especially if using the Wav2Lip module.

Installation

Clone the repository and install the dependencies:

git clone [https://github.com/raaidd123/video-dubber.git](https://github.com/raaidd123/video-dubber.git)
cd video-dubber
pip install -r requirements.txt


Model Checkpoints

Wav2Lip: Download the pre-trained checkpoint and place it in the designated folder (e.g., checkpoints/).

ASR (Whisper): The required Whisper model size (e.g., small, medium) can be configured in the main script.

Translation (MarianMT): Specify the appropriate Hugging Face model checkpoints for the source-to-target language pair (e.g., Helsinki-NLP/opus-mt-en-hi for English to Hindi).

💡 Usage

Run the Dubbing Script

Execute the main script, specifying the input video and target language:

python run_dubber.py \
    --input_video "path/to/your/video.mp4" \
    --target_language "hindi" \
    --output_video "dubbed_video_hi.mp4"


Enable Lip Synchronization

To include the computationally intensive Wav2Lip step, add the --enable_lipsync flag:

python run_dubber.py \
    --input_video "path/to/your/video.mp4" \
    --target_language "spanish" \
    --output_video "dubbed_video_es_sync.mp4" \
    --enable_lipsync


📊 Performance and Evaluation

Our system was evaluated on a dataset of 50 short English interview clips (15-60 s) with human references.

Stage

Time (s) per 1 min video

Notes

ASR (Whisper small)

54

GPU accelerated

Translation

18

Per-segment processing

TTS Synthesis (gTTS)

30

Baseline

Audio Replacement

24

MoviePy/ffmpeg

Total (No Lip-Sync)

126

~2.1x original duration

Wav2Lip (optional)

198

High GPU requirement

Total (With Wav2Lip)

324

~5.4x original duration

🤝 Contribution

We welcome contributions! Please refer to the open issues or submit a pull request with your suggested improvements. Specifically, we are looking for contributions in:

Integration of higher-quality neural TTS engines.

Duration-aware synthesis for better segment timing alignment.

Improved handling of prosody and emotion transfer.

⚖️ Limitations and Ethical Considerations

TTS Quality: The current baseline TTS (gTTS) lacks the prosody and emotional range of professional human dubbing. Higher-fidelity neural TTS should be used for production quality.

Deceptive Content: Automated dubbing enables the creation of synthetic content. Users must obtain explicit consent for voice usage and disclose when content is synthetically generated.

Reproducibility: For strict research reproducibility, use offline models (MarianMT) with fixed checkpoints, as cloud services (Google Translate, gTTS) may change over time.

📝 Citation

If you use this work, please cite the original paper:

@article{Abdullah_Dubber_2024,
  title={Dubbing Any English Video To Any Indian Regional Language},
  author={Raaid Abudllaah and Zakariya Razak and Maroof Ansari},
  journal={Department of Computer Science (Data Science) Presidency University, Bengaluru, India},
  year={2024},
  note={Preprint. Available at this repository.}
}


Authors: Raaid Abudllaah, Zakariya Razak, Maroof Ansari
Department of Computer Science (Data Science), Presidency University, Bengaluru, India
