import speech_recognition as sr

# print(sr.__version__)

r = sr.Recognizer()

audio_source = sr.AudioData('harvard.wav', 16000, 2)

r.recognize_google(audio_source)