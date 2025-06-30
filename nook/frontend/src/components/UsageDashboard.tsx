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

interface UsageDashboardProps {
  darkMode?: boolean;
}

const UsageDashboard: React.FC<UsageDashboardProps> = ({ darkMode = false }) => {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [serviceUsage, setServiceUsage] = useState<ServiceUsage[]>([]);
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const theme = useTheme();
  // const isSmallScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const isMediumScreen = useMediaQuery(theme.breakpoints.down('md'));

  const fetchData = async () => {
    try {
      setLoading(true);
      
      const [summaryResponse, serviceResponse, dailyResponse] = await Promise.all([
        axios.get('http://localhost:8000/api/usage/summary'),
        axios.get('http://localhost:8000/api/usage/by-service'),
        axios.get('http://localhost:8000/api/usage/daily?days=30')
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
        <Typography 
          variant="h4" 
          component="h1" 
          className={darkMode ? 'text-white' : 'text-gray-900'}
        >
          LLM API 使用状況ダッシュボード
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Typography 
            variant="body2" 
            className={darkMode ? 'text-gray-300' : 'text-gray-600'}
          >
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
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="今日のコスト"
            value={formatCurrency(summary?.todayCost || 0)}
            icon={<AttachMoneyIcon />}
            color="success.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="今月のコスト"
            value={formatCurrency(summary?.monthCost || 0)}
            icon={<CalendarTodayIcon />}
            color="warning.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="API呼び出し回数"
            value={formatNumber(summary?.totalCalls || 0)}
            icon={<TrendingUpIcon />}
            color="info.main"
          />
        </Grid>
      </Grid>

      {/* サービス別使用量テーブル */}
      <Card elevation={2} sx={{ mb: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            サービス別使用量
          </Typography>
          <TableContainer sx={{ overflowX: 'auto' }}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>サービス名</TableCell>
                  <TableCell align="right">呼び出し回数</TableCell>
                  <TableCell align="right">入力トークン</TableCell>
                  <TableCell align="right">出力トークン</TableCell>
                  <TableCell align="right">コスト</TableCell>
                  <TableCell align="right">最終呼び出し</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {serviceUsage.map((service) => (
                  <TableRow key={service.service}>
                    <TableCell>
                      <Chip 
                        label={service.service} 
                        variant="outlined" 
                        size="small"
                      />
                    </TableCell>
                    <TableCell align="right">{formatNumber(service.calls)}</TableCell>
                    <TableCell align="right">{formatNumber(service.inputTokens)}</TableCell>
                    <TableCell align="right">{formatNumber(service.outputTokens)}</TableCell>
                    <TableCell align="right">{formatCurrency(service.cost)}</TableCell>
                    <TableCell align="right">{formatDate(service.lastCalled)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>

      {/* 時系列グラフ */}
      <Card elevation={2}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            日別コスト推移（過去30日）
          </Typography>
          <Box sx={{ width: '100%', height: isMediumScreen ? 300 : 400 }}>
            <ResponsiveContainer>
              <BarChart data={dailyUsage}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tick={{ fontSize: 12 }}
                  interval={isMediumScreen ? 'preserveStartEnd' : 0}
                />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  formatter={(value: number) => [formatCurrency(value), 'コスト']}
                  labelFormatter={(label) => `日付: ${label}`}
                />
                <Legend />
                <Bar 
                  dataKey="totalCost" 
                  fill={theme.palette.primary.main}
                  name="総コスト"
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