import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  TrendingUp as TrendingUpIcon,
  AttachMoney as AttachMoneyIcon,
  Api as ApiIcon,
  CalendarToday as CalendarTodayIcon
} from '@mui/icons-material';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts';
import axios from 'axios';

interface UsageSummary {
  todayTokens: number;
  todayCost: number;
  monthCost: number;
  totalCalls: number;
}

interface ServiceUsage {
  service: string;
  calls: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  lastCalled: string;
}

interface DailyUsage {
  date: string;
  services: { [key: string]: number };
  totalCost: number;
}

const UsageDashboard: React.FC = () => {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [serviceUsage, setServiceUsage] = useState<ServiceUsage[]>([]);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const isMediumScreen = useMediaQuery(theme.breakpoints.down('md'));

  const fetchData = async () => {
    try {
      setLoading(true);
      
      const [summaryResponse, serviceResponse, dailyResponse] = await Promise.all([
        axios.get('/api/usage/summary'),
        axios.get('/api/usage/by-service'),
        axios.get('/api/usage/daily?days=30')
      ]);

      setSummary(summaryResponse.data);
      setServiceUsage(serviceResponse.data);
      setDailyUsage(dailyResponse.data);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('データの取得に失敗しました:', error);
      // モックデータを設定（開発用）
      setSummary({
        todayTokens: 15420,
        todayCost: 0.23,
        monthCost: 12.45,
        totalCalls: 78
      });
      setServiceUsage([
        {
          service: 'OpenAI GPT-4',
          calls: 25,
          inputTokens: 8500,
          outputTokens: 3200,
          cost: 0.15,
          lastCalled: '2024-01-20T15:30:00Z'
        },
        {
          service: 'Claude-3',
          calls: 18,
          inputTokens: 6200,
          outputTokens: 2800,
          cost: 0.08,
          lastCalled: '2024-01-20T14:45:00Z'
        }
      ]);
      setDailyUsage([
        { date: '2024-01-15', services: { 'OpenAI GPT-4': 0.12, 'Claude-3': 0.08 }, totalCost: 0.20 },
        { date: '2024-01-16', services: { 'OpenAI GPT-4': 0.18, 'Claude-3': 0.06 }, totalCost: 0.24 },
        { date: '2024-01-17', services: { 'OpenAI GPT-4': 0.15, 'Claude-3': 0.09 }, totalCost: 0.24 },
        { date: '2024-01-18', services: { 'OpenAI GPT-4': 0.22, 'Claude-3': 0.07 }, totalCost: 0.29 },
        { date: '2024-01-19', services: { 'OpenAI GPT-4': 0.19, 'Claude-3': 0.11 }, totalCost: 0.30 },
        { date: '2024-01-20', services: { 'OpenAI GPT-4': 0.15, 'Claude-3': 0.08 }, totalCost: 0.23 }
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    
    // 5分ごとの自動更新
    const interval = setInterval(fetchData, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatCurrency = (amount: number) => `$${amount.toFixed(2)}`;
  const formatNumber = (num: number) => num.toLocaleString();
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ja-JP');
  };

  const formatRelativeTime = (dateString: string) => {
    const now = new Date();
    const date = new Date(dateString);
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    
    if (diffHours < 1) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins}分前`;
    } else if (diffHours < 24) {
      return `${diffHours}時間前`;
    } else {
      const diffDays = Math.floor(diffHours / 24);
      return `${diffDays}日前`;
    }
  };

  const getColorForMetric = (type: string) => {
    switch(type) {
      case 'cost': return theme.palette.warning.main;
      case 'tokens': return theme.palette.info.main;
      case 'calls': return theme.palette.success.main;
      default: return theme.palette.primary.main;
    }
  };

  const SummaryCard: React.FC<{ 
    title: string; 
    value: string; 
    icon: React.ReactNode; 
    color: string;
    type: string;
  }> = ({ title, value, icon, color, type }) => (
    <Card 
      elevation={3}
      sx={{
        transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: theme.shadows[6]
        }
      }}
    >
      <CardContent>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h3" component="div" color={getColorForMetric(type)} fontWeight="bold">
              {value}
            </Typography>
          </Box>
          <Box color={getColorForMetric(type)} sx={{ fontSize: '40px' }}>
            {icon}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  if (loading && !summary) {
    return (
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Typography>データを読み込み中...</Typography>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
      {/* ヘッダー */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          LLM API 使用状況ダッシュボード
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography variant="body2" color="textSecondary">
            最終更新: {lastUpdated.toLocaleTimeString('ja-JP')}
          </Typography>
          <IconButton onClick={fetchData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {/* サマリーカード */}
      <Grid container spacing={3} mb={4}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="今日のトークン数"
            value={formatNumber(summary?.todayTokens || 0)}
            icon={<ApiIcon />}
            color="primary.main"
            type="tokens"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="今日のコスト"
            value={formatCurrency(summary?.todayCost || 0)}
            icon={<AttachMoneyIcon />}
            color="success.main"
            type="cost"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="今月のコスト"
            value={formatCurrency(summary?.monthCost || 0)}
            icon={<CalendarTodayIcon />}
            color="warning.main"
            type="cost"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="API呼び出し回数"
            value={formatNumber(summary?.totalCalls || 0)}
            icon={<TrendingUpIcon />}
            color="info.main"
            type="calls"
          />
        </Grid>
      </Grid>

      {/* サービス別使用量テーブル */}
      <Card elevation={3} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            サービス別使用量
          </Typography>
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table stickyHeader>
              <TableHead>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold' }}>サービス名</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>呼び出し回数</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>入力トークン</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>出力トークン</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>コスト</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>最終呼び出し</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {serviceUsage.map((service) => (
                  <TableRow 
                    key={service.service}
                    sx={{
                      '&:hover': {
                        backgroundColor: theme.palette.action.hover
                      },
                      transition: 'background-color 0.2s ease'
                    }}
                  >
                    <TableCell sx={{ py: 2 }}>
                      <Chip 
                        label={service.service} 
                        variant="outlined" 
                        size="small"
                        color="primary"
                      />
                    </TableCell>
                    <TableCell align="right" sx={{ py: 2 }}>{formatNumber(service.calls)}</TableCell>
                    <TableCell align="right" sx={{ py: 2 }}>{formatNumber(service.inputTokens)}</TableCell>
                    <TableCell align="right" sx={{ py: 2 }}>{formatNumber(service.outputTokens)}</TableCell>
                    <TableCell align="right" sx={{ py: 2 }}>
                      <Typography color={getColorForMetric('cost')} fontWeight="medium">
                        {formatCurrency(service.cost)}
                      </Typography>
                    </TableCell>
                    <TableCell align="right" sx={{ py: 2 }}>
                      <Typography variant="body2" color="textSecondary">
                        {formatRelativeTime(service.lastCalled)}
                      </Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* 時系列グラフ */}
      <Card elevation={3}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            日別コスト推移（過去30日）
          </Typography>
          <Box sx={{ width: '100%', height: 400 }}>
            <ResponsiveContainer>
              <BarChart data={dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  interval={'preserveStartEnd'}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                />
                <YAxis 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => formatCurrency(value)}
                />
                <Tooltip 
                  formatter={(value: number) => [formatCurrency(value), 'コスト']}
                  labelFormatter={(label) => {
                    const date = new Date(label);
                    return `日付: ${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 8
                  }}
                />
                <Legend />
                <Bar 
                  dataKey="totalCost" 
                  fill={getColorForMetric('cost')}
                  name="総コスト"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </CardContent>
      </Card>
    </Container>
  );
};

export default UsageDashboard;