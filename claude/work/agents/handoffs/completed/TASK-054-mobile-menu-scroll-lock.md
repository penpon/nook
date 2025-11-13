# TASK-054: モバイルメニュー表示時の背景スクロール禁止実装

## タスク概要
モバイルメニューを開いた際に、背景コンテンツがスクロールできてしまう問題を修正する。ユーザビリティ向上のため、メニュー表示中は背景のスクロールを無効化する。

## 変更予定ファイル
- nook/frontend/src/App.tsx

## 前提タスク
なし（独立したタスク）

## worktree名
worktrees/TASK-054-mobile-menu-scroll-lock

## 作業内容

### 1. スクロールロック機能の実装
App.tsxのisMobileMenuOpenステートに連動して、body要素のスクロールを制御するuseEffectを追加：

```tsx
// App.tsx の既存のuseEffectセクション付近に追加
useEffect(() => {
  if (isMobileMenuOpen) {
    // メニューが開いている時はスクロールを無効化
    document.body.style.overflow = 'hidden';
    // iOSのバウンススクロール対策
    document.body.style.position = 'fixed';
    document.body.style.width = '100%';
  } else {
    // メニューが閉じた時は元に戻す
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.width = '';
  }
  
  // クリーンアップ関数でスタイルをリセット
  return () => {
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.width = '';
  };
}, [isMobileMenuOpen]);
```

### 2. スクロール位置の保持
position: fixedによるスクロール位置のジャンプを防ぐため、以下の改善を追加：

```tsx
const [scrollPosition, setScrollPosition] = useState(0);

useEffect(() => {
  if (isMobileMenuOpen) {
    // 現在のスクロール位置を保存
    const currentScrollY = window.scrollY;
    setScrollPosition(currentScrollY);
    
    document.body.style.overflow = 'hidden';
    document.body.style.position = 'fixed';
    document.body.style.top = `-${currentScrollY}px`;
    document.body.style.width = '100%';
  } else {
    // スクロール位置を復元
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.width = '';
    
    window.scrollTo(0, scrollPosition);
  }
  
  return () => {
    document.body.style.overflow = '';
    document.body.style.position = '';
    document.body.style.top = '';
    document.body.style.width = '';
  };
}, [isMobileMenuOpen, scrollPosition]);
```

### 3. テスト項目
1. モバイルメニューを開いた状態で背景がスクロールしないことを確認
2. メニューを閉じた後、元のスクロール位置に戻ることを確認
3. iOSサファリでのバウンススクロールが発生しないことを確認
4. メニューの開閉を繰り返してもスクロール位置がずれないことを確認

### 4. 注意事項
- iOSのモバイルサファリでは特殊な挙動があるため、実機での確認が重要
- position: fixedを使用するため、他のfixed要素との干渉に注意
- パフォーマンスへの影響を最小限にするため、不要なre-renderを避ける

## 完了条件
- [ ] モバイルメニュー表示中は背景がスクロールしない
- [ ] メニューを閉じた後、元のスクロール位置に戻る
- [ ] iOS/Androidの主要ブラウザで動作確認済み
- [ ] コードレビューで承認済み