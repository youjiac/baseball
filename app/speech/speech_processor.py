import speech_recognition as sr
from gtts import gTTS
import io
import tempfile
import os
import streamlit as st

class SpeechProcessor:
    def __init__(self):
        """初始化語音處理器"""
        self.recognizer = sr.Recognizer()
        self.language = "zh-TW"  # 設置為繁體中文
        
    def listen(self) -> sr.AudioData:
        """監聽麥克風輸入"""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source)
                audio = self.recognizer.listen(source, timeout=5)
                return audio
        except Exception as e:
            st.error(f"無法取得麥克風輸入: {str(e)}")
            return None
            
    def transcribe(self, audio: sr.AudioData) -> str:
        """將語音轉換為文字"""
        try:
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text
        except sr.UnknownValueError:
            st.warning("無法識別語音內容")
            return None
        except sr.RequestError as e:
            st.error(f"語音識別服務錯誤: {str(e)}")
            return None
            
    def synthesize(self, text: str) -> bytes:
        """將文字轉換為語音"""
        try:
            # 創建 gTTS 對象
            tts = gTTS(text=text, lang=self.language)
            
            # 將語音保存到內存中
            fp = io.BytesIO()
            tts.write_to_fp(fp)
            fp.seek(0)
            
            return fp.read()
            
        except Exception as e:
            st.error(f"語音合成失敗: {str(e)}")
            return None