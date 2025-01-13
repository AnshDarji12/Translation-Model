# translation_pipeline.py
import torch
import whisper
import traceback
import os
import edge_tts
import asyncio
import nest_asyncio
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
import logging
from pydub import AudioSegment
import io
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Apply nest_asyncio for async operations
nest_asyncio.apply()

# Translation prompt template
TRANSLATION_PROMPT = """Below is an English text that needs to be translated to {target_lang}.
Provide only the translation, without any additional text or explanations.

English: {source_text}

{target_lang}: {target_text}"""

# Language voice mapping for edge-tts
VOICE_MAPPING = {
    'es': 'es-ES-AlvaroNeural',
    'fr': 'fr-FR-HenriNeural',
    'ru': 'ru-RU-PavelNeural',
    'en': 'en-US-EricNeural'
}

class VideoTranslationPipeline:
    def __init__(self, model=None, tokenizer=None, temp_dir: str = "temp"):
        """Initialize the translation pipeline."""
        self.model = model
        self.tokenizer = tokenizer
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Initialize Whisper Model
        logger.info("Loading Whisper Model...")
        try:
            self.whisper_model = whisper.load_model("base")
            logger.info("✓ Whisper model loaded successfully!")
        except Exception as e:
            logger.error(f"✗ Error loading Whisper model: {e}")
            raise

        logger.info("✓ Translation pipeline initialized successfully!")

    def speech_to_text(self, audio_input) -> Optional[str]:
        """Convert speech to text using Whisper."""
        try:
            logger.info("\n🎤 Converting Speech to Text...")
            
            if isinstance(audio_input, bytes):
                temp_audio_path = self.temp_dir / "temp_input.wav"
                
                # Convert webm to wav using pydub
                audio = AudioSegment.from_file(io.BytesIO(audio_input), format="webm")
                audio.export(str(temp_audio_path), format="wav")
                
                # Transcribe audio
                result = self.whisper_model.transcribe(str(temp_audio_path))
                
                # Clean up temporary file
                temp_audio_path.unlink(missing_ok=True)
            else:
                result = self.whisper_model.transcribe(audio_input)
            
            if result and 'text' in result:
                original_text = result['text'].strip()
                logger.info("\n📝 Original English Text:")
                logger.info("=" * 80)
                logger.info(original_text)
                logger.info("=" * 80)
                return original_text
            else:
                logger.warning("✗ No text found in transcription")
                return None
                
        except Exception as e:
            logger.error(f"✗ Speech-to-text error: {e}")
            traceback.print_exc()
            return None

    def translate_text(self, text: str, target_lang: str = 'es') -> Optional[str]:
        """Translate text to target language."""
        try:
            logger.info(f"\n🔄 Translating to {target_lang}...")
            
            # Map language codes to full names
            language_names = {
                'es': 'Spanish',
                'fr': 'French',
                'ru': 'Russian',
                'en': 'English'
            }
            
            # Get full language name
            target_lang_name = language_names.get(target_lang, target_lang)
            
            # Create input using the exact format
            prompt = TRANSLATION_PROMPT.format(
                target_lang=target_lang_name,
                source_text=text,
                target_text=" "
            )
            
            inputs = self.tokenizer([prompt], return_tensors="pt").to("cuda")
            
            # Generate translation with optimized parameters
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=128,
                num_beams=5,
                temperature=0.1,
                top_p=0.95,
                repetition_penalty=4.2,
                no_repeat_ngram_size=4,
                length_penalty=8.5,
                early_stopping=True,
                use_cache=True
            )
            
            # Get translation
            translated = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
            cleaned_translation = self._clean_translation(translated, target_lang_name)
            
            # Verify translation is not empty or invalid
            if not self._is_valid_translation(cleaned_translation):
                logger.warning("Invalid translation, retrying with different parameters...")
                # Retry with different parameters
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=128,
                    do_sample=False,
                    temperature=0.3,
                    top_p=0.95,
                    repetition_penalty=2.5,
                    use_cache=True
                )
                translated = self.tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
                cleaned_translation = self._clean_translation(translated, target_lang_name)
            
            logger.info(f"\n📝 Translation: {cleaned_translation}")
            return cleaned_translation
            
        except Exception as e:
            logger.error(f"✗ Translation error: {e}")
            traceback.print_exc()
            return None

    def _clean_translation(self, text: str, target_lang: str) -> str:
        """Clean up translation output."""
        try:
            # Extract translation from the response
            translation = text
            
            # Try to find the translation after the language marker
            markers = [
                f"{target_lang}:",
                "translation:",
                f"in {target_lang}:",
                ":"
            ]
            
            for marker in markers:
                if marker.lower() in translation.lower():
                    translation = translation.lower().split(marker.lower())[-1]
                    break
            
            # Remove English source if present
            if "english:" in translation.lower():
                translation = translation.lower().split("english:")[0]
            
            # Clean up
            translation = translation.strip()
            translation = translation.strip(':".,')
            
            # Remove common artifacts
            artifacts = [
                "translate",
                "translation",
                "following",
                "text",
                target_lang.lower(),
                "english",
                "provide",
                "only",
                "without",
                "additional",
                "explanations"
            ]
            
            cleaned = translation.lower()
            for artifact in artifacts:
                cleaned = cleaned.replace(artifact, "")
            
            # Final cleanup
            cleaned = cleaned.strip()
            cleaned = ' '.join(cleaned.split())
            
            # Capitalize first letter
            if cleaned:
                cleaned = cleaned[0].upper() + cleaned[1:] if len(cleaned) > 1 else cleaned.upper()
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning translation: {e}")
            return text

    def _is_valid_translation(self, translation: str) -> bool:
        """Check if translation is valid."""
        if not translation:
            return False
            
        # Check if it's too short
        if len(translation) < 2:
            return False
            
        # Check if it contains common prompt artifacts
        artifacts = ["translate", "translation:", "english:", "spanish:", "french:"]
        if any(artifact in translation.lower() for artifact in artifacts):
            return False
            
        return True

    async def text_to_speech(self, text: str, target_lang: str = 'es') -> Tuple[bool, Optional[str], Optional[str]]:
        """Convert text to speech using edge-tts."""
        try:
            logger.info(f"\n🔊 Converting to {target_lang} speech...")
            
            voice = VOICE_MAPPING.get(target_lang, VOICE_MAPPING['en'])
            output_path = self.temp_dir / f"translation_{target_lang}.wav"
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(output_path))
            
            # Read the audio file and convert to base64
            with open(output_path, 'rb') as audio_file:
                audio_data = base64.b64encode(audio_file.read()).decode('utf-8')
            
            logger.info(f"✓ Audio generated successfully")
            return True, str(output_path), audio_data
            
        except Exception as e:
            logger.error(f"✗ Text-to-speech error: {e}")
            traceback.print_exc()
            return False, None, None

    def cleanup_temp_files(self):
        """Clean up temporary files."""
        try:
            for file in self.temp_dir.glob("*"):
                file.unlink()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")