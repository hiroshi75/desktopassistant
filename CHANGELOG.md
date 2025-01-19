# Changelog

## [Unreleased]

### Changed
- macOSメニューバー実装を`rumps`ベースに変更
  - [MacOS-Menu-Bar-Picker](https://github.com/marwonn/MacOS-Menu-Bar-Picker)を参考に実装
  - `pystray`からの移行により、よりネイティブな体験を提供
  - システムトレイアイコンとメニュー項目の実装を簡素化

### Added
- `MacOSMenuBarApp`クラスの実装
  - ネイティブなmacOSメニューバーの提供
  - チャットウィンドウの表示/非表示制御
  - スレッドセーフなウィンドウ操作の実装

### Improved
- スレッドセーフティの強化
  - メインスレッドでのウィンドウ操作を確実に実行
  - `PyObjCTools.AppHelper`を使用した適切なスレッド管理
  - テスト環境での`AppHelper`のモック化対応

### Testing
- テストカバレッジの拡充
  - `test_macos_window_operations`: メニュー操作とウィンドウ制御のテスト
  - `test_window_thread_safety`: スレッドセーフティのテスト
  - モジュールレベルのモック化による安定したテスト環境

### Known Issues
- テストの一部が失敗中
  - ウィンドウ作成の検証が不完全
  - スレッドセーフティテストの改善が必要
  - HTMLテンプレートのモック化に課題あり

### Next Steps
- テストの修正と安定化
  - スレッドセーフティテストの完了
  - ウィンドウ作成テストの改善
  - モック戦略の見直し
- 実装の改善
  - エラーハンドリングの強化
  - ウィンドウ状態管理の改善
  - クロスプラットフォーム対応の維持
