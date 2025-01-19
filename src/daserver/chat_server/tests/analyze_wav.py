import wave
import numpy as np

# WAVファイルを読み込む
with wave.open('/home/ubuntu/attachments/3dc8090a-fff5-4d4b-af7b-2926b57ad67b/test.wav', 'rb') as wav_file:
    # WAVファイルのパラメータを取得
    print(f'チャンネル数: {wav_file.getnchannels()}')
    print(f'サンプル幅: {wav_file.getsampwidth()} bytes')
    print(f'サンプリング周波数: {wav_file.getframerate()} Hz')
    print(f'フレーム数: {wav_file.getnframes()}')
    print(f'パラメータ: {wav_file.getparams()}')
    
    # 音声データを読み込む
    frames = wav_file.readframes(wav_file.getnframes())
    
    # バイト列をnumpy配列に変換
    audio_data = np.frombuffer(frames, dtype=np.int16)
    print(f'\n音声データの情報:')
    print(f'データ型: {audio_data.dtype}')
    print(f'データサイズ: {len(audio_data)} サンプル')
    print(f'最小値: {np.min(audio_data)}')
    print(f'最大値: {np.max(audio_data)}')
    print(f'平均値: {np.mean(audio_data)}')
    print(f'標準偏差: {np.std(audio_data)}')
