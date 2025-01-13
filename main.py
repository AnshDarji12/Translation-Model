from flask import Flask, render_template
from flask_socketio import SocketIO
from model_loader import initialize_model
from translation_pipeline import VideoTranslationPipeline
import base64
import logging
import asyncio
from engineio.async_drivers import threading
import os

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize model and pipeline
try:
    model, tokenizer = initialize_model()
    translator = VideoTranslationPipeline(model, tokenizer)
    logger.info("✓ Model and translator initialized successfully!")
except Exception as e:
    logger.error(f"✗ Error initializing model: {e}")
    raise

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('translate_audio')
def handle_audio(data):
    try:
        logger.info("Received audio for translation")
        audio_data = base64.b64decode(data['audio'])
        target_lang = data.get('target_lang', 'es')
        
        # Process translation
        text = translator.speech_to_text(audio_data)
        logger.info(f"Transcribed text: {text}")
        
        if text:
            translated = translator.translate_text(text, target_lang)
            logger.info(f"Translated text: {translated}")
            
            if translated:
                # Run text-to-speech in a separate thread
                def process_tts():
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # Generate speech and get audio data
                        success, audio_path, audio_data = loop.run_until_complete(
                            translator.text_to_speech(translated, target_lang)
                        )
                        
                        if success and audio_data:
                            socketio.emit('translation_result', {
                                'original': text,
                                'translated': translated,
                                'audio_data': audio_data
                            })
                            
                            # Clean up audio file
                            if audio_path and os.path.exists(audio_path):
                                os.remove(audio_path)
                    except Exception as e:
                        logger.error(f"TTS processing error: {e}")
                        socketio.emit('translation_error', {'error': str(e)})
                    finally:
                        loop.close()
                
                socketio.start_background_task(process_tts)
                
    except Exception as e:
        logger.error(f"Translation error: {e}")
        socketio.emit('translation_error', {'error': str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=False, allow_unsafe_werkzeug=True)