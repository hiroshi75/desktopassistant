import asyncio
import websockets
import numpy as np
import struct
import os
import logging

# ログレベルの設定
logging.basicConfig(level=logging.DEBUG,
                   format='%(asctime)s - %(levelname)s - %(message)s')

# AWSの認証情報を設定
os.environ['AWS_ACCESS_KEY_ID'] = os.getenv('AWS_ACCESS_KEY_ID', '')
os.environ['AWS_SECRET_ACCESS_KEY'] = os.getenv('AWS_SECRET_ACCESS_KEY', '')
os.environ['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')

if not all(os.environ.get(key) for key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_REGION']):
    logging.error("AWS認証情報が環境変数に設定されていません。テストを中止します。")
    raise ValueError("AWS認証情報が必要です")

def generate_test_audio():
    """テスト用の音声データを生成（1秒間の440Hz正弦波）"""
    sample_rate = 8000  # サンプリング周波数を8000Hzに変更
    duration = 3.0  # 3秒
    t = np.linspace(0, duration, int(sample_rate * duration))
    
    # 440Hzの正弦波を生成（「あ」の基本周波数に近い）
    audio = np.sin(2 * np.pi * 440 * t)
    
    # 16ビットPCMに変換（リトルエンディアン）
    audio = np.clip(audio * 32767, -32768, 32767)
    audio = audio.astype('<i2')  # np.int16 with explicit little-endian
    
    # ヘッダーなしのrawPCMデータとして送信
    audio_bytes = audio.tobytes()
    
    logging.debug(f"生成された音声データの詳細:")
    logging.debug(f"- サイズ: {len(audio_bytes)} bytes")
    logging.debug(f"- サンプリングレート: {sample_rate} Hz")
    logging.debug(f"- ビット深度: 16-bit")
    logging.debug(f"- エンディアン: リトルエンディアン")
    logging.debug(f"- チャンネル数: 1 (モノラル)")
    logging.debug(f"- 周波数: 440 Hz")
    logging.debug(f"- 長さ: {duration} 秒")
    
    return audio_bytes

async def test_websocket():
    uri = "ws://localhost:8000/TranscribeStreaming"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket接続が確立されました")
            
            # テスト用の音声データを生成して送信
            audio_data = generate_test_audio()
            chunk_size = 1024  # より小さいチャンクサイズで処理を高速化
            
            # データをチャンクに分割して送信
            for i in range(0, len(audio_data), chunk_size):
                chunk = audio_data[i:i + chunk_size]
                if not chunk:
                    break
                    
                logging.info(f"チャンク {i//chunk_size + 1} を送信中... (サイズ: {len(chunk)} バイト)")
                # バイナリデータをそのまま送信
                await websocket.send(chunk)
                logging.debug(f"チャンク {i//chunk_size + 1} を送信完了")
                
                # 非同期でレスポンスを受信（ブロッキングを避ける）
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    logging.info(f"受信: {response}")
                except asyncio.TimeoutError:
                    # タイムアウトは正常な動作として扱う（応答を待たずに次のチャンクを送信）
                    logging.debug(f"チャンク {i//chunk_size + 1} の送信を継続します")
                    pass
                except Exception as e:
                    logging.error(f"エラーが発生しました: {e}")
                    if "connection is closed" in str(e):
                        break

                # さらに短い間隔で次のチャンクを送信（タイムアウトを防ぐため）
                await asyncio.sleep(0.005)
            
            logging.info("すべてのデータを送信しました")
            
            # 終了シグナルを送信（遅延を短縮）
            await asyncio.sleep(0.1)  # 最後のチャンクが処理されるのを待つ
            await websocket.send("submit_response")
            print("終了シグナルを送信しました")
            
            # 最終応答を待機
            try:
                while True:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    logging.info(f"最終応答: {response}")
            except asyncio.TimeoutError:
                logging.warning("最終応答のタイムアウト")
            except websockets.exceptions.ConnectionClosed:
                logging.info("WebSocket接続が正常に終了しました")
            
    except Exception as e:
        logging.error(f"エラーが発生しました: {e}")
    finally:
        logging.info("テスト完了")

if __name__ == "__main__":
    asyncio.run(test_websocket())
