from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import whisper
import os
import gc
import time
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip,
    concatenate_audioclips, AudioClip
)
from moviepy.config import change_settings

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

app = Flask(__name__)
CORS(app)

# Folders
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
TEMP_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

model = whisper.load_model("base") 

SUPPORTED_LANGS = {
    "Assamese": "as",
    "Bengali": "bn",
    "Bodo": "brx",
    "Dogri": "doi",
    "Gujarati": "gu",
    "Hindi": "hi",
    "Kannada": "kn",
    "Kashmiri": "ks",
    "Konkani": "kok",
    "Maithili": "mai",
    "Malayalam": "ml",
    "Manipuri": "mni",
    "Marathi": "mr",
    "Nepali": "ne",
    "Odia": "or",       
    "Punjabi": "pa",
    "Sanskrit": "sa",
    "Santali": "sat",
    "Sindhi": "sd",
    "Tamil": "ta",
    "Telugu": "te",
    "Urdu": "ur"
}

def safe_remove(path):
    if path and os.path.exists(path):
        try: os.remove(path)
        except: pass

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400

    file = request.files['video']
    target_lang = request.form.get('target_lang', 'hi')

    if not file.filename.endswith('.mp4'):
        return jsonify({'error': 'Only .mp4 allowed'}), 400

    if target_lang in SUPPORTED_LANGS.values():
        target_code = target_lang
    else:
        matched = None
        for name, code in SUPPORTED_LANGS.items():
            if name.lower() == target_lang.lower():
                matched = code
                break
        if matched:
            target_code = matched
        else:
            if target_lang.lower() in {c.lower() for c in SUPPORTED_LANGS.values()}:
                lc = target_lang.lower()
                canonical = next(c for c in SUPPORTED_LANGS.values() if c.lower() == lc)
                target_code = canonical
            else:
                return jsonify({'error': 'Unsupported language requested', 'supported': list(SUPPORTED_LANGS.keys())}), 400

    filename_base = os.path.splitext(file.filename)[0]
    video_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(video_path)

    extracted_audio_path = None
    try:
        start_time = time.time()
        print(f"Processing: {file.filename}")

        # 1. Extract audio
        video = VideoFileClip(video_path)
        video_duration = video.duration
        print(f"Video duration: {video_duration:.2f}s")

        extracted_audio_path = os.path.join(TEMP_FOLDER, f"extracted_{filename_base}.wav")
        video.audio.write_audiofile(extracted_audio_path, verbose=False, logger=None)
        video.close()
        gc.collect()

        # 2. Transcribe
        result = model.transcribe(extracted_audio_path, language='en')
        segments = result['segments']
        if not segments:
            return jsonify({'error': 'No speech detected'}), 400

        english_text = result['text'].strip()
        translated_segments = []
        full_translated_text = ""

        dubbed_clips = []
        captions = []
        translator = GoogleTranslator(source='en', target=target_code)
        current_time = 0.0

        for i, seg in enumerate(segments):
            start = seg['start']
            end = seg['end']
            text = seg['text'].strip()

        
            if start > current_time:
                silence = AudioClip(lambda t: [0, 0], duration=start - current_time)
                dubbed_clips.append(silence)

    
            translated = translator.translate(text)
            translated_segments.append(translated)
            full_translated_text += translated + " "

            tts_path = os.path.join(TEMP_FOLDER, f"tts_{i}.mp3")
            gTTS(text=translated, lang=target_code, slow=False).save(tts_path)
            tts_clip = AudioFileClip(tts_path)

            speech_duration = end - start
            if tts_clip.duration > speech_duration:
                tts_clip = tts_clip.subclip(0, speech_duration)
            else:
                pad = AudioClip(lambda t: [0, 0], duration=speech_duration - tts_clip.duration)
                tts_clip = concatenate_audioclips([tts_clip, pad])

            dubbed_clips.append(tts_clip)
            current_time = end

          
            caption = TextClip(
                translated,
                fontsize=24, color='white', font='Arial',
                stroke_color='black', stroke_width=2, method='caption'
            ).set_start(start).set_duration(speech_duration).set_position(('center', 'bottom'))
            captions.append(caption)

            safe_remove(tts_path)

      
        if current_time < video_duration:
            final_silence = AudioClip(lambda t: [0, 0], duration=video_duration - current_time)
            dubbed_clips.append(final_silence)

        final_audio = concatenate_audioclips(dubbed_clips).set_duration(video_duration)

        original_video = VideoFileClip(video_path)
        final_video = original_video.set_audio(final_audio)
        final_video = CompositeVideoClip([final_video] + captions)

        output_filename = f"dubbed_{filename_base}.mp4"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        final_video.write_videofile(
            output_path,
            codec='libx264',
            audio_codec='aac',
            verbose=False,
            logger=None,
            threads=4
        )

        original_video.close()
        final_audio.close()
        final_video.close()
        gc.collect()

        safe_remove(video_path)
        safe_remove(extracted_audio_path)

        total_time = time.time() - start_time
        print(f"DONE in {total_time:.1f} seconds!")

        return jsonify({
            'success': True,
            'dubbed_url': f'/download/{output_filename}',
            'time_taken': f"{total_time:.1f}s",
            'english_text': english_text,
            'translated_text': full_translated_text.strip()
        })

    except Exception as e:
        import traceback
        print("ERROR:", traceback.format_exc())
        safe_remove(video_path)
        safe_remove(extracted_audio_path)
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    print("DUBBING SERVER RUNNING")
    print("   → http://127.0.0.1:5000")
    print("   → Returns english_text & translated_text")
    app.run(debug=True, port=5000)
