import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { 
  LogOut, Upload, Download, RefreshCw, Search, 
  ChevronLeft, ChevronRight, Tag, Inbox, Mail, Settings2, Activity 
} from 'lucide-react';
import api from '../lib/api';
import { showSuccess, showError } from '../lib/toast';
import { CONFIG, MESSAGES } from '../lib/constants';
import ImportModal from '../components/ImportModal';
import EmailViewModal from '../components/EmailViewModal';
import {
  useAccountsQuery,
  useAccountTagsQuery,
  useSystemConfigQuery,
  useSystemMetricsQuery,
  useApiAction,
} from '../lib/hooks';
import { logError } from '../lib/utils';

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [showImport, setShowImport] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [emailLimit, setEmailLimit] = useState(5);
  const [savingConfig, setSavingConfig] = useState(false);

  const { data, isLoading, isError } = useAccountsQuery({ page, search });
  const { data: tagsData } = useAccountTagsQuery();
  const { data: configData } = useSystemConfigQuery();
  const { data: metricsData } = useSystemMetricsQuery();
  const apiAction = useApiAction();
  const emailCacheStats = metricsData?.data?.email_manager?.email_cache || {};
  const cacheHitRate = metricsData?.data?.email_manager?.cache_hit_rate;

  useEffect(() => {
    if (configData?.data?.email_limit) {
      setEmailLimit(configData.data.email_limit);
    }
  }, [configData]);
  
  const accountTagsMap = tagsData?.data?.accounts || {};

  const handleLogout = () => {
    sessionStorage.removeItem('admin_token');
    navigate('/admin/login');
  };

  const handleConfigSave = async () => {
    setSavingConfig(true);
    try {
      await apiAction(
        () => api.post('/api/system/config', { email_limit: Number(emailLimit) }),
        {
          successMessage: MESSAGES.SUCCESS_CONFIG_UPDATED,
          errorMessage: MESSAGES.ERROR_CONFIG_UPDATE_FAILED,
          onSuccess: () => queryClient.invalidateQueries(['system-config']),
        },
      );
    } finally {
      setSavingConfig(false);
    }
  };

  const handleTagManage = async (emailAddress) => {
    const current = accountTagsMap[emailAddress] || [];
    const next = window.prompt('请输入标签（用逗号分隔）', current.join(','));
    if (next === null) return;

    const tags = next
      .split(',')
      .map(t => t.trim())
      .filter(Boolean);

    await apiAction(
      () =>
        api.post(`/api/account/${encodeURIComponent(emailAddress)}/tags`, {
          email: emailAddress,
          tags,
        }),
      {
        successMessage: MESSAGES.SUCCESS_TAG_SAVED,
        errorMessage: MESSAGES.ERROR_TAG_SAVE_FAILED,
        onSuccess: () => queryClient.invalidateQueries(['tags']),
      },
    );
  };

  const handleCacheRefresh = async () => {
    await apiAction(
      () => api.post('/api/system/cache/refresh'),
      {
        successMessage: MESSAGES.SUCCESS_CACHE_REFRESHED,
        errorMessage: MESSAGES.ERROR_CACHE_REFRESH_FAILED,
        onSuccess: () => {
          queryClient.invalidateQueries(['system-metrics']);
          queryClient.invalidateQueries(['accounts']);
        },
      },
    );
  };

  const handleExport = async () => {
    try {
      const res = await api.get('/api/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'outlook_accounts.txt');
      document.body.appendChild(link);
      link.click();
      link.remove();
      showSuccess(MESSAGES.SUCCESS_EXPORT);
    } catch (e) {
      logError('导出失败', e);
      showError(e?.response?.data?.message || MESSAGES.ERROR_EXPORT_FAILED);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* Navbar */}
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center sticky top-0 z-10">
        <div className="flex items-center gap-3">
           <div className="bg-blue-600 p-2 rounded-lg text-white">
               <Inbox className="w-5 h-5" />
           </div>
           <h1 className="text-xl font-bold text-gray-800">Outlook Manager</h1>
        </div>
        <div className="flex items-center gap-4">
           <button 
             onClick={handleLogout}
             className="text-gray-500 hover:text-red-600 flex items-center gap-2 text-sm font-medium transition-colors"
           >
             <LogOut className="w-4 h-4" /> 退出
           </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        
        {/* Toolbar */}
        <div className="flex flex-col md:flex-row gap-4 justify-between items-center bg-white p-4 rounded-xl shadow-sm">
            <div className="flex items-center gap-2 w-full md:w-auto">
                <div className="relative w-full md:w-80">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                    <input 
                      type="text" 
                      placeholder="搜索邮箱..." 
                      className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
                      value={search}
                      onChange={e => {
                          setSearch(e.target.value);
                          setPage(1);
                      }}
                    />
                </div>
            </div>
            
            <div className="flex gap-2 w-full md:w-auto">
                <button 
                  onClick={() => setShowImport(true)}
                  className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
                >
                    <Upload className="w-4 h-4" /> 导入
                </button>
                <button 
                  onClick={handleExport}
                  className="flex-1 md:flex-none flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors"
                >
                    <Download className="w-4 h-4" /> 导出
                </button>
                <button 
                  onClick={() => queryClient.invalidateQueries(['accounts'])}
                  className="p-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors"
                  title="刷新"
                >
                    <RefreshCw className="w-4 h-4" />
                </button>
            </div>
        </div>

        {/* System overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-500">邮件获取限制</p>
                <h3 className="text-xl font-semibold text-gray-800">每次最多 {emailLimit} 封</h3>
              </div>
              <Settings2 className="w-6 h-6 text-blue-500" />
            </div>
            <div className="flex gap-3">
              <input
                type="number"
                min={1}
                max={50}
                value={emailLimit}
                onChange={(e) => setEmailLimit(e.target.value)}
                className="flex-1 border rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 outline-none"
              />
              <button
                onClick={handleConfigSave}
                disabled={savingConfig}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {savingConfig ? '保存中...' : '保存'}
              </button>
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm p-5 space-y-3">
            <div className="flex justify-between items-center gap-3">
              <div>
                <p className="text-sm text-gray-500">系统指标</p>
                <h3 className="text-xl font-semibold text-gray-800">
                  {metricsData?.data?.email_manager?.accounts_count || 0} 个账户
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <Activity className="w-6 h-6 text-green-500" />
                <button
                  onClick={handleCacheRefresh}
                  className="px-3 py-1.5 text-xs font-medium border border-gray-200 rounded-lg hover:bg-gray-50"
                >
                  刷新缓存
                </button>
              </div>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm text-gray-600">
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>缓存命中</dt>
                <dd className="font-semibold text-gray-900">
                  {metricsData?.data?.email_manager?.cache_hits ?? 0}
                </dd>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>缓存未命中</dt>
                <dd className="font-semibold text-gray-900">
                  {metricsData?.data?.email_manager?.cache_misses ?? 0}
                </dd>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>IMAP 复用</dt>
                <dd className="font-semibold text-gray-900">
                  {metricsData?.data?.email_manager?.client_reuses ?? 0}
                </dd>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>IMAP 创建</dt>
                <dd className="font-semibold text-gray-900">
                  {metricsData?.data?.email_manager?.client_creates ?? 0}
                </dd>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>缓存命中率</dt>
                <dd className="font-semibold text-gray-900">
                  {typeof cacheHitRate === 'number'
                    ? `${(cacheHitRate * 100).toFixed(1)}%`
                    : '--'}
                </dd>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <dt>缓存邮件数</dt>
                <dd className="font-semibold text-gray-900">
                  {emailCacheStats.total_messages ?? 0}
                </dd>
              </div>
            </dl>
            {metricsData?.data?.warning && (
              <p className="text-sm text-amber-600 bg-amber-50 border border-amber-100 rounded-lg p-3">
                {metricsData.data.warning}
              </p>
            )}
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl shadow-sm overflow-hidden border border-gray-200">
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-gray-50 text-gray-500 font-medium border-b">
                        <tr>
                            <th className="px-6 py-4">邮箱账户</th>
                            <th className="px-6 py-4">标签</th>
                            <th className="px-6 py-4 text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {isLoading ? (
                            [...Array(5)].map((_, i) => (
                                <tr key={i} className="animate-pulse">
                                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-48"></div></td>
                                    <td className="px-6 py-4"><div className="h-4 bg-gray-200 rounded w-24"></div></td>
                                    <td className="px-6 py-4"></td>
                                </tr>
                            ))
                        ) : isError ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-8 text-center text-red-500">加载失败，请重试</td>
                            </tr>
                        ) : data?.data?.items?.length === 0 ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-12 text-center text-gray-400">
                                    暂无数据
                                </td>
                            </tr>
                        ) : (
                            data?.data?.items?.map((account) => (
                                <tr key={account.email} className="hover:bg-gray-50 group transition-colors">
                                    <td className="px-6 py-4 font-medium text-gray-900">
                                        {account.email}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-1 flex-wrap">
                                            {accountTagsMap[account.email]?.map(tag => (
                                                <span key={tag} className="px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full text-xs font-medium">
                                                    {tag}
                                                </span>
                                            ))}
                                            {(!accountTagsMap[account.email] || accountTagsMap[account.email].length === 0) && (
                                                <span className="text-gray-300 italic text-xs">无标签</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex gap-2 justify-end">
                                            <button 
                                              onClick={() => setSelectedEmail(account.email)}
                                              className="text-gray-400 hover:text-blue-600 p-1 rounded transition-colors"
                                              title="查看邮件"
                                            >
                                                <Mail className="w-4 h-4" />
                                            </button>
                                            <button 
                                              className="text-gray-400 hover:text-green-600 p-1 rounded transition-colors"
                                              title="管理标签"
                                              onClick={() => handleTagManage(account.email)}
                                            >
                                                <Tag className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
            
            {/* Pagination */}
            <div className="border-t px-6 py-4 flex items-center justify-between">
                <p className="text-sm text-gray-500">
                    共 {data?.data?.total || 0} 条记录
                </p>
                <div className="flex gap-2">
                    <button 
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ChevronLeft className="w-4 h-4" />
                    </button>
                    <span className="flex items-center px-4 text-sm font-medium text-gray-700">
                        第 {page} 页
                    </span>
                    <button 
                      onClick={() => setPage(p => p + 1)}
                      disabled={!data?.data || page * CONFIG.DEFAULT_PAGE_SIZE >= data.data.total}
                      className="p-2 border rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ChevronRight className="w-4 h-4" />
                    </button>
                </div>
            </div>
        </div>
      </main>

      <ImportModal 
        isOpen={showImport} 
        onClose={() => setShowImport(false)} 
        onSuccess={() => {
            queryClient.invalidateQueries(['accounts']);
        }}
      />

      <EmailViewModal
        email={selectedEmail}
        isOpen={!!selectedEmail}
        onClose={() => setSelectedEmail(null)}
      />
    </div>
  );
}
