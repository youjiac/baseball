import speech_recognition as sr
from gtts import gTTS
import os
import logging

logger = logging.getLogger(__name__)

class SpeechProcessor:
    def __init__(self):
        """初始化語音處理器"""
        self.recognizer = sr.Recognizer()
        self.language = 'zh-tw'  # 使用繁體中文
        
    def speech_to_text(self) -> str:
        """語音轉文字"""
        try:
            with sr.Microphone() as source:
                logger.info("正在調整環境噪音...")
                self.recognizer.adjust_for_ambient_noise(source)
                logger.info("請說話...")
                audio = self.recognizer.listen(source)
                logger.info("正在識別...")
                text = self.recognizer.recognize_google(audio, language=self.language)
                logger.info(f"識別結果: {text}")
                return text
        except Exception as e:
            logger.error(f"語音識別錯誤: {str(e)}")
            return None

    def text_to_speech(self, text: str) -> str:
        """文字轉語音"""
        try:
            tts = gTTS(text=text, lang=self.language)
            filename = "temp_speech.mp3"
            tts.save(filename)
            logger.info("語音生成成功")
            return filename
        except Exception as e:
            logger.error(f"語音生成錯誤: {str(e)}")
            return None

    def cleanup(self):
        """清理暫存檔案"""
        try:
            if os.path.exists("temp_speech.mp3"):
                os.remove("temp_speech.mp3")
        except Exception as e:
            logger.error(f"清理檔案時發生錯誤: {str(e)}")