import React, { useEffect, useState, Suspense } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  LogOut, Upload, Download, RefreshCw, Search,
  ChevronLeft, ChevronRight, Tag, Inbox, Mail, Settings2, Activity, XCircle, AlertCircle
} from 'lucide-react';
import api from '../lib/api';
import { showSuccess, showError } from '../lib/toast';
import { CONFIG, MESSAGES } from '../lib/constants';
import {
  useAccountsQuery,
  useAccountTagsQuery,
  useSystemConfigQuery,
  useSystemMetricsQuery,
  useApiAction,
  useDebounce
} from '../lib/hooks';
import { logError } from '../lib/utils';

import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card';
import { Skeleton } from '../components/ui/Skeleton';

// Lazy load modals
const ImportModal = React.lazy(() => import('../components/ImportModal'));
const EmailViewModal = React.lazy(() => import('../components/EmailViewModal'));
const TagManageModal = React.lazy(() => import('../components/TagManageModal'));

export default function AdminDashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState('');
  const [jumpToPage, setJumpToPage] = useState('');
  const debouncedSearch = useDebounce(search, 500);
  const [showImport, setShowImport] = useState(false);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [tagModal, setTagModal] = useState({ isOpen: false, email: null });
  const [emailLimit, setEmailLimit] = useState(5);
  const [savingConfig, setSavingConfig] = useState(false);
  const [refreshingCache, setRefreshingCache] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Use debounced search for query
  const { data, isLoading, isError } = useAccountsQuery({ page, search: debouncedSearch, pageSize });
  const { data: tagsData } = useAccountTagsQuery();
  const { data: configData } = useSystemConfigQuery();
  const { data: metricsData } = useSystemMetricsQuery();

  // Calculate pagination info
  const totalPages = data?.data?.total ? Math.ceil(data.data.total / pageSize) : 1;
  const totalRecords = data?.data?.total || 0;

  // Handle page size change
  const handlePageSizeChange = (newSize) => {
    setPageSize(Number(newSize));
    setPage(1); // Reset to first page
  };

  // Handle jump to page
  const handleJumpToPage = () => {
    // Remove non-numeric characters
    const cleanedInput = jumpToPage.replace(/\D/g, '');
    const pageNum = parseInt(cleanedInput, 10);

    if (isNaN(pageNum) || cleanedInput === '') {
      showError('请输入有效的页码');
      return;
    }

    if (pageNum >= 1 && pageNum <= totalPages) {
      setPage(pageNum);
      setJumpToPage('');
    } else {
      showError(`请输入 1 到 ${totalPages} 之间的页码`);
    }
  };

  // Generate page numbers with ellipsis
  const getPageNumbers = () => {
    const pages = [];
    const showEllipsisStart = page > 3;
    const showEllipsisEnd = page < totalPages - 2;

    // Always show first page
    pages.push(1);

    // Show ellipsis or pages before current
    if (showEllipsisStart) {
      pages.push('...');
      // Show 2 pages before current
      for (let i = Math.max(2, page - 1); i < page; i++) {
        pages.push(i);
      }
    } else {
      // Show all pages from 2 to current
      for (let i = 2; i < page; i++) {
        pages.push(i);
      }
    }

    // Show current page (if not first or last)
    if (page !== 1 && page !== totalPages) {
      pages.push(page);
    }

    // Show ellipsis or pages after current
    if (showEllipsisEnd) {
      // Show 2 pages after current
      for (let i = page + 1; i <= Math.min(page + 1, totalPages - 1); i++) {
        pages.push(i);
      }
      pages.push('...');
    } else {
      // Show all pages from current+1 to last-1
      for (let i = page + 1; i < totalPages; i++) {
        pages.push(i);
      }
    }

    // Always show last page (if more than 1 page)
    if (totalPages > 1) {
      pages.push(totalPages);
    }

    return pages;
  };
  const apiAction = useApiAction();
  const cacheHitRate = metricsData?.data?.email_manager?.cache_hit_rate;

  useEffect(() => {
    if (configData?.data?.email_limit) {
      setEmailLimit(configData.data.email_limit);
    }
  }, [configData]);
  
  // Reset page when search changes
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

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

  const handleTagManage = (emailAddress) => {
    setTagModal({ isOpen: true, email: emailAddress });
  };

  const handleCacheRefresh = async () => {
    setRefreshingCache(true);
    try {
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
    } finally {
      setRefreshingCache(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
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
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col font-sans">
      {/* Navbar */}
      <header className="bg-background border-b px-6 py-4 flex justify-between items-center sticky top-0 z-20 shadow-md backdrop-blur-sm">
        <div className="flex items-center gap-3">
           <div className="bg-primary p-2 rounded-lg text-primary-foreground">
               <Inbox className="w-5 h-5" />
           </div>
           <h1 className="text-xl font-bold tracking-tight">Outlooker</h1>
        </div>
        <div className="flex items-center gap-4">
           <Button 
             variant="ghost"
             onClick={handleLogout}
             className="text-muted-foreground hover:text-destructive flex items-center gap-2"
           >
             <LogOut className="w-4 h-4" /> 退出
           </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        
        {/* Toolbar */}
        <Card className="p-4 flex flex-col md:flex-row gap-4 justify-between items-center">
            <div className="relative w-full md:w-80">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
                <Input 
                  type="text" 
                  placeholder="搜索邮箱..." 
                  className="pl-10"
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                />
            </div>
            
            <div className="flex gap-2 w-full md:w-auto">
                <Button 
                  onClick={() => setShowImport(true)}
                  className="flex-1 md:flex-none gap-2"
                >
                    <Upload className="w-4 h-4" /> 导入
                </Button>
                <Button
                  variant="outline"
                  onClick={handleExport}
                  disabled={exporting}
                  className="flex-1 md:flex-none gap-2"
                >
                    <Download className={`w-4 h-4 ${exporting ? 'animate-pulse' : ''}`} />
                    {exporting ? '导出中...' : '导出'}
                </Button>
                <Button 
                  variant="outline"
                  size="icon"
                  onClick={() => queryClient.invalidateQueries(['accounts'])}
                  title="刷新"
                >
                    <RefreshCw className="w-4 h-4" />
                </Button>
            </div>
        </Card>

        {/* System overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">邮件获取限制</CardTitle>
              <Settings2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-4">
                <div className="text-2xl font-bold">每次最多 {emailLimit} 封</div>
                <div className="flex gap-3">
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={emailLimit}
                    onChange={(e) => setEmailLimit(e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    onClick={handleConfigSave}
                    disabled={savingConfig}
                  >
                    {savingConfig ? '保存中...' : '保存'}
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-base font-medium">系统指标</CardTitle>
              <Activity className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="flex justify-between items-center mb-4">
                 <div className="text-2xl font-bold">
                    {metricsData?.data?.email_manager?.accounts_count || 0} 个账户
                 </div>
                 <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCacheRefresh}
                    disabled={refreshingCache}
                    className="h-8 text-xs gap-1"
                  >
                    <RefreshCw className={`w-3 h-3 ${refreshingCache ? 'animate-spin' : ''}`} />
                    {refreshingCache ? '刷新中...' : '刷新缓存'}
                  </Button>
              </div>
              
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">缓存命中</dt>
                  <dd className="font-semibold">{metricsData?.data?.email_manager?.cache_hits ?? 0}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">缓存未命中</dt>
                  <dd className="font-semibold">{metricsData?.data?.email_manager?.cache_misses ?? 0}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">IMAP 复用</dt>
                  <dd className="font-semibold">{metricsData?.data?.email_manager?.client_reuses ?? 0}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">IMAP 创建</dt>
                  <dd className="font-semibold">{metricsData?.data?.email_manager?.client_creates ?? 0}</dd>
                </div>
                <div className="flex justify-between col-span-2 pt-2 border-t">
                  <dt className="text-muted-foreground">缓存命中率</dt>
                  <dd className="font-bold text-green-600">
                    {typeof cacheHitRate === 'number'
                      ? `${(cacheHitRate * 100).toFixed(1)}%`
                      : '--'}
                  </dd>
                </div>
              </dl>
              
              {metricsData?.data?.warning && (
                <div className="mt-3 rounded-md bg-yellow-500/10 p-3 text-sm text-yellow-900 dark:text-yellow-200 border border-yellow-500/30">
                  {metricsData.data.warning}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Table */}
        <Card className="overflow-hidden">
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                    <thead className="bg-muted text-muted-foreground font-medium border-b">
                        <tr>
                            <th className="px-6 py-4">邮箱账户</th>
                            <th className="px-6 py-4">标签</th>
                            <th className="px-6 py-4 text-right">操作</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y">
                        {isLoading ? (
                            [...Array(5)].map((_, i) => (
                                <tr key={i}>
                                    <td className="px-6 py-4"><Skeleton className="h-4 w-48" /></td>
                                    <td className="px-6 py-4"><Skeleton className="h-4 w-24" /></td>
                                    <td className="px-6 py-4 text-right"><Skeleton className="h-8 w-16 ml-auto" /></td>
                                </tr>
                            ))
                        ) : isError ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-12">
                                    <div className="flex flex-col items-center justify-center space-y-4">
                                        <XCircle className="w-12 h-12 text-destructive" />
                                        <div className="text-center space-y-2">
                                            <p className="text-destructive font-medium">加载账户列表失败</p>
                                            <p className="text-sm text-muted-foreground">
                                                请检查网络连接或稍后重试
                                            </p>
                                        </div>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            onClick={() => queryClient.invalidateQueries(['accounts'])}
                                            className="gap-2"
                                        >
                                            <RefreshCw className="w-4 h-4" />
                                            重新加载
                                        </Button>
                                    </div>
                                </td>
                            </tr>
                        ) : data?.data?.items?.length === 0 ? (
                            <tr>
                                <td colSpan={3} className="px-6 py-12">
                                    <div className="flex flex-col items-center justify-center space-y-4">
                                        <Inbox className="w-16 h-16 text-muted-foreground/40" />
                                        <div className="text-center space-y-2">
                                            <p className="text-muted-foreground font-semibold text-base">
                                                {debouncedSearch ? '未找到匹配的账户' : '暂无账户数据'}
                                            </p>
                                            <p className="text-sm text-muted-foreground/80">
                                                {debouncedSearch ? '尝试使用其他关键词搜索' : '点击"导入"按钮添加账户'}
                                            </p>
                                        </div>
                                        {!debouncedSearch && (
                                            <Button
                                                onClick={() => setShowImport(true)}
                                                className="gap-2"
                                            >
                                                <Upload className="w-4 h-4" />
                                                导入账户
                                            </Button>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            data?.data?.items?.map((account) => {
                                const isUsed = typeof account.is_used === 'boolean' ? account.is_used : null;
                                const lastUsedAt = account.last_used_at;

                                return (
                                <tr key={account.email} className="hover:bg-muted/80 transition-colors">
                                    <td className="px-6 py-4 font-medium">
                                        <div className="flex flex-col gap-1">
                                          <div className="flex items-center gap-2">
                                            <span>{account.email}</span>
                                            {isUsed !== null && (
                                              <Badge
                                                variant={isUsed ? 'outline' : 'secondary'}
                                                className="text-[11px] px-2 py-0.5 rounded-full"
                                              >
                                                {isUsed ? '已使用(公共池)' : '未使用(公共池)'}
                                              </Badge>
                                            )}
                                          </div>
                                          {isUsed && lastUsedAt && (
                                            <span className="text-xs text-muted-foreground">
                                              最后使用：{lastUsedAt}
                                            </span>
                                          )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex gap-1 flex-wrap">
                                            {accountTagsMap[account.email]?.map(tag => (
                                                <Badge key={tag} variant="secondary" className="text-xs">
                                                    {tag}
                                                </Badge>
                                            ))}
                                            {(!accountTagsMap[account.email] || accountTagsMap[account.email].length === 0) && (
                                                <span className="text-muted-foreground italic text-xs">无标签</span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex gap-2 justify-end">
                                            <Button
                                              variant="ghost"
                                              size="icon"
                                              onClick={() => setSelectedEmail(account.email)}
                                              className="h-8 w-8 text-muted-foreground hover:text-primary"
                                              title="查看邮件"
                                            >
                                                <Mail className="w-4 h-4" />
                                            </Button>
                                            <Button 
                                              variant="ghost"
                                              size="icon"
                                              className="h-8 w-8 text-muted-foreground hover:text-green-600"
                                              title="管理标签"
                                              onClick={() => handleTagManage(account.email)}
                                            >
                                                <Tag className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            )})
                        )}
                    </tbody>
                </table>
            </div>
            
            {/* Pagination */}
            <div className="border-t px-4 md:px-6 py-4 bg-muted/40">
                {/* Mobile Layout */}
                <div className="flex md:hidden flex-col gap-3">
                    <div className="flex items-center justify-between">
                        <p className="text-xs text-muted-foreground">
                            共 {totalRecords} 条
                        </p>
                        <select
                            value={pageSize}
                            onChange={(e) => handlePageSizeChange(e.target.value)}
                            className="text-xs border rounded px-2 py-1 bg-background"
                        >
                            <option value="10">10条/页</option>
                            <option value="20">20条/页</option>
                            <option value="50">50条/页</option>
                            <option value="100">100条/页</option>
                        </select>
                    </div>
                    <div className="flex items-center justify-between">
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="gap-1"
                        >
                            <ChevronLeft className="w-3 h-3" />
                            上一页
                        </Button>
                        <span className="text-sm font-medium">
                            {page} / {totalPages}
                        </span>
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="gap-1"
                        >
                            下一页
                            <ChevronRight className="w-3 h-3" />
                        </Button>
                    </div>
                </div>

                {/* Desktop Layout */}
                <div className="hidden md:flex items-center justify-between gap-4">
                    {/* Left: Total records and page size selector */}
                    <div className="flex items-center gap-4">
                        <p className="text-sm text-muted-foreground whitespace-nowrap">
                            共 {totalRecords} 条记录
                        </p>
                        <select
                            value={pageSize}
                            onChange={(e) => handlePageSizeChange(e.target.value)}
                            className="text-sm border rounded-md px-3 py-1.5 bg-background focus:ring-2 focus:ring-ring outline-none"
                        >
                            <option value="10">10 条/页</option>
                            <option value="20">20 条/页</option>
                            <option value="50">50 条/页</option>
                            <option value="100">100 条/页</option>
                        </select>
                    </div>

                    {/* Center: Page navigation */}
                    <div className="flex items-center gap-1">
                        <Button
                            variant="outline"
                            size="icon"
                            onClick={() => setPage(p => Math.max(1, p - 1))}
                            disabled={page === 1}
                            className="h-9 w-9"
                        >
                            <ChevronLeft className="w-4 h-4" />
                        </Button>

                        {/* Page numbers */}
                        {getPageNumbers().map((pageNum, idx) => (
                            pageNum === '...' ? (
                                <span key={`ellipsis-${idx}`} className="px-2 text-muted-foreground">
                                    ...
                                </span>
                            ) : (
                                <Button
                                    key={pageNum}
                                    variant={page === pageNum ? 'default' : 'outline'}
                                    size="icon"
                                    onClick={() => setPage(pageNum)}
                                    className="h-9 w-9"
                                >
                                    {pageNum}
                                </Button>
                            )
                        ))}

                        <Button
                            variant="outline"
                            size="icon"
                            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                            disabled={page >= totalPages}
                            className="h-9 w-9"
                        >
                            <ChevronRight className="w-4 h-4" />
                        </Button>
                    </div>

                    {/* Right: Jump to page */}
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-muted-foreground whitespace-nowrap">跳转到</span>
                        <Input
                            type="text"
                            value={jumpToPage}
                            onChange={(e) => setJumpToPage(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    handleJumpToPage();
                                }
                            }}
                            placeholder="页码"
                            className="w-16 h-9 text-center text-sm"
                        />
                        <Button
                            variant="outline"
                            size="sm"
                            onClick={handleJumpToPage}
                            disabled={!jumpToPage}
                            className="h-9"
                        >
                            跳转
                        </Button>
                    </div>
                </div>
            </div>
        </Card>
      </main>

      {/* Modals with Suspense */}
      <Suspense fallback={<div className="p-6 text-sm text-muted-foreground">正在加载资源...</div>}>
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

        {tagModal.isOpen && (
          <TagManageModal
            email={tagModal.email}
            currentTags={accountTagsMap[tagModal.email]}
            isOpen={tagModal.isOpen}
            onClose={() => setTagModal({ isOpen: false, email: null })}
            onSuccess={() => queryClient.invalidateQueries(['tags'])}
          />
        )}
      </Suspense>
    </div>
  );
}
