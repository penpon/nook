# TASK-014: Usage Dashboard UIの調整

## タスク概要
Usage DashboardのUIを前回のシンプルなデザインに戻しつつ、タイトルと最終更新時刻の視認性を改善する。

## 要件
1. **UIを前回のシンプルなデザインに戻す**
2. **タイトル「LLM API 使用状況ダッシュボード」と「最終更新: XX:XX:XX」の視認性を改善**

## 実装内容

### 1. ヘッダー部分の修正
タイトルと最終更新時刻に明示的な色を設定：
```typescript
{/* ヘッダー */}
<Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
  <Typography 
    variant="h4" 
    component="h1"
    sx={{ 
      color: theme.palette.mode === 'dark' ? '#fff' : theme.palette.text.primary,
      fontWeight: 'bold'
    }}
  >
    LLM API 使用状況ダッシュボード
  </Typography>
  <Box display="flex" alignItems="center" gap={2}>
    <Typography 
      variant="body2" 
      sx={{ 
        color: theme.palette.mode === 'dark' ? 'rgba(255, 255, 255, 0.8)' : theme.palette.text.secondary 
      }}
    >
      最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
    </Typography>
    <IconButton onClick={fetchData} disabled={loading}>
      <RefreshIcon />
    </IconButton>
  </Box>
</Box>
```

### 2. SummaryCardを前回のシンプルなバージョンに戻す
```typescript
const SummaryCard: React.FC<{ 
  title: string; 
  value: string; 
  icon: React.ReactNode; 
  color: string;
}> = ({ title, value, icon, color }) => (
  <Card elevation={2}>
    <CardContent>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box>
          <Typography color="textSecondary" gutterBottom variant="body2">
            {title}
          </Typography>
          <Typography variant="h5" component="div" color={color}>
            {value}
          </Typography>
        </Box>
        <Box color={color}>{icon}</Box>
      </Box>
    </CardContent>
  </Card>
);
```

### 3. 削除する機能
以下の機能を削除またはシンプル化：
- formatRelativeTime関数を削除（formatDateのみ使用）
- getColorForMetric関数を削除
- カードのhover効果を削除
- テーブルのhover効果を削除
- アイコンサイズのsx設定を削除
- SummaryCardのtype引数を削除

### 4. サマリーカードの呼び出しを修正
```typescript
<Grid container spacing={3} mb={4}>
  <Grid item xs={12} sm={6} md={3}>
    <SummaryCard
      title="今日のトークン数"
      value={formatNumber(summary?.todayTokens || 0)}
      icon={<ApiIcon />}
      color="primary.main"
    />
  </Grid>
  // 他のカードも同様にtype引数を削除
</Grid>
```

### 5. テーブルの修正
- stickyHeaderを削除
- hover効果のsxを削除
- formatRelativeTimeの代わりにformatDateを使用

## 変更予定ファイル
- `nook/frontend/src/components/UsageDashboard.tsx`

## 前提タスク
なし

## テスト方法
1. ライトモードとダークモードの両方で表示確認
2. タイトルと最終更新時刻が両モードで明確に見えることを確認
3. UIが前回のシンプルなバージョンに戻っていることを確認
4. 機能（データ取得、自動更新）が正常に動作することを確認

## 注意事項
- 機能的な変更は行わない（UIのみの変更）
- 5分ごとの自動更新機能は維持する
- レスポンシブデザインは維持する