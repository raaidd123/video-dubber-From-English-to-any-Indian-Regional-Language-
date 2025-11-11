from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import whisper
import os
import gc  # For garbage collection to release file handles
import time  # For small delay if needed
from deep_translator import GoogleTranslator
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
import io
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"})

app = Flask(__name__)
CORS(app)  

# Directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
TEMP_FOLDER = 'temp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(TEMP_FOLDER, exist_ok=True)

# Load Whisper model (tiny for speed; base for better accuracy)
model = whisper.load_model("base") 

# Supported languages
SUPPORTED_LANGS = {'Hindi': 'hi', 'Tamil': 'ta', 'Telugu': 'te', 'Kannada': 'kn', 'Malayalam':'ml'}

def safe_remove(path, retries=5, delay=0.5):
    """Safely remove file with retries to handle temporary locks from ffmpeg/MoviePy."""
    for attempt in range(retries):
        try:
            os.remove(path)
            print(f"Successfully removed {path}")
            return True
        except PermissionError:
            print(f"Attempt {attempt + 1}: File {path} still locked, waiting...")
            time.sleep(delay)
    print(f"Failed to remove {path} after {retries} attempts")
    return False

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file'}), 400
    
    file = request.files['video']
    target_lang = request.form['target_lang']
    
    if file.filename == '' or not file.filename.endswith('.mp4'):
        return jsonify({'error': 'Invalid file, must be MP4'}), 400
    
    # Save uploaded video
    filename = file.filename
    video_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(video_path)
    
    audio_path = None
    dubbed_audio_path = None
    try:
        # Step 1: Extract audio from video
        video = VideoFileClip(video_path)
        audio_path = os.path.join(TEMP_FOLDER, f"extracted_{filename}.wav")
        video.audio.write_audiofile(audio_path)  
        video.audio.close()
        video.close()  # Release first clip

        # Force garbage collection to help release handles
        gc.collect()

        # Step 2: Transcribe audio to text with timestamps
        result = model.transcribe(audio_path, language='en')
        english_text = result['text'].strip()
        segments = result['segments']  
        
        if not english_text:
            return jsonify({'error': 'No speech detected'}), 400
        
        # Step 3: Translate to target language
        translator = GoogleTranslator(source='en', target=target_lang)
        translated_text = translator.translate(english_text)
        
        # Step 4: Generate dubbed audio
        tts = gTTS(text=translated_text, lang=target_lang, slow=False)
        dubbed_audio_path = os.path.join(TEMP_FOLDER, f"dubbed_{filename}.mp3")
        tts.save(dubbed_audio_path)
        
        # Step 5: Merge dubbed audio with video and add captions
        output_filename = f"dubbed_{filename}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)
        video = VideoFileClip(video_path)  # Reload video
        dubbed_audio = AudioFileClip(dubbed_audio_path)
        
        if dubbed_audio.duration > video.duration:
            dubbed_audio = dubbed_audio.subclip(0, video.duration)
        
        captions = []
        for segment in segments:
            start, end = segment['start'], segment['end']
            text = translator.translate(segment['text'].strip())
            if text:  
                caption = TextClip(
                    text, fontsize=24, color='white',  # FIXED: Removed bg_color='black'
                    font='Arial', size=None, method='caption',  # FIXED: size=None for auto-size (no blackout)
                    stroke_color='black', stroke_width=2  # Outline for readability on any bg
                ).set_position(('center', 'bottom')).set_duration(end - start).set_start(start)
                captions.append(caption)
        
        # Composite video with captions
        final_video = video.set_audio(dubbed_audio)
        final_video = CompositeVideoClip([final_video] + captions)
        final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
        
        # Clean up clips
        video.close()
        dubbed_audio.close()
        final_video.close()

        # Force garbage collection again
        gc.collect()

        # Small delay to let ffmpeg subprocesses fully terminate
        time.sleep(1)

        # Safe cleanup with retries
        safe_remove(video_path)
        if audio_path:
            safe_remove(audio_path)
        if dubbed_audio_path:
            safe_remove(dubbed_audio_path)
        
        return jsonify({
            'success': True,
            'english_text': english_text,
            'translated_text': translated_text,
            'target_lang': target_lang,  # FIXED: Pass lang code for frontend display
            'dubbed_url': f'/download/{output_filename}'
        })
    
    except Exception as e:
        import traceback
        print(traceback.format_exc())  # For debugging in console
        
        # Safe cleanup on error
        if audio_path:
            safe_remove(audio_path)
        if dubbed_audio_path:
            safe_remove(dubbed_audio_path)
        safe_remove(video_path)
        
        return jsonify({'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(OUTPUT_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)