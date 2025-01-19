import numpy as np
import os

def analyze_pcm_file(file_path, sample_rate=8000):
    """PCMファイルを解析する"""
    # ファイルサイズを取得
    file_size = os.path.getsize(file_path)
    print(f'ファイルサイズ: {file_size} bytes')
    
    # PCMデータを読み込む（16ビット、リトルエンディアン）
    with open(file_path, 'rb') as f:
        audio_data = np.frombuffer(f.read(), dtype=np.int16)
    
    # 音声の長さを計算
    duration = len(audio_data) / sample_rate
    
    print(f'\n音声データの情報:')
    print(f'サンプリング周波数: {sample_rate} Hz（想定）')
    print(f'データ型: {audio_data.dtype}')
    print(f'データサイズ: {len(audio_data)} サンプル')
    print(f'音声の長さ: {duration:.2f} 秒')
    print(f'最小値: {np.min(audio_data)}')
    print(f'最大値: {np.max(audio_data)}')
    print(f'平均値: {np.mean(audio_data):.2f}')
    print(f'標準偏差: {np.std(audio_data):.2f}')
    
    # 最初の10サンプルを16進数で表示
    print(f'\n最初の10サンプル（16進数）:')
    for i in range(min(10, len(audio_data))):
        print(f'Sample {i}: {audio_data[i]:04x}')

if __name__ == '__main__':
    file_path = '/home/ubuntu/attachments/3dc8090a-fff5-4d4b-af7b-2926b57ad67b/test.wav'
    analyze_pcm_file(file_path)
