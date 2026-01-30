import { useState } from 'react';
import { Upload, AlertCircle } from 'lucide-react';
import api from '@/lib/api';
import { useApiAction, useAsyncTask } from '@/lib/hooks';
import { Dialog } from './ui/Dialog';
import { Button } from './ui/Button';
import { Alert, AlertDescription } from './ui/Alert';
import { Badge } from './ui/Badge';
import type { ApiResponse } from '@/types';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface ParsedAccount {
  email: string;
  password?: string;
  client_id?: string;
  refresh_token: string;
}

interface PreviewData {
  accounts: ParsedAccount[];
  parsed_count: number;
  error_count: number;
  errors: string[];
}

interface ImportResult {
  message: string;
  added_count: number;
  updated_count: number;
  skipped_count: number;
  error_count: number;
}

type MergeMode = 'update' | 'skip' | 'replace';

export default function ImportModal({ isOpen, onClose, onSuccess }: ImportModalProps) {
  const [text, setText] = useState('');
  const [mergeMode, setMergeMode] = useState<MergeMode>('update');
  const [step, setStep] = useState(1); // 1: Input, 2: Confirm, 3: Result
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const { loading, run } = useAsyncTask();
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const apiAction = useApiAction({ showSuccessToast: false });

  const handleParse = async () => {
    if (!text.trim()) return;
    setError(null);
    const response = await run(() =>
      apiAction(
        () => api.post<ApiResponse<PreviewData>>('/api/parse-import-text', { text }),
        { errorMessage: '解析失败' },
      )
    );

    if (response.ok && response.data) {
      setPreviewData(response.data as PreviewData);
      setStep(2);
    } else {
      setError((response.data as { message?: string })?.message || '解析失败');
    }
  };

  const handleImport = async () => {
    if (!previewData?.accounts?.length) {
      setError('请先完成解析步骤');
      return;
    }
    setError(null);
    const response = await run(() =>
      apiAction(
        () =>
          api.post<ApiResponse<ImportResult>>('/api/import', {
            accounts: previewData.accounts,
            merge_mode: mergeMode,
          }),
        {
          successMessage: '导入成功',
          errorMessage: '导入失败',
          showSuccessToast: true,
        },
      )
    );

    if (response.ok && response.data) {
      setResult(response.data as ImportResult);
      setStep(3);
      if (onSuccess) onSuccess();
    } else if (response.data) {
      setResult(response.data as ImportResult);
      setStep(3);
      if ((response.data as { message?: string }).message) {
        setError((response.data as { message?: string }).message || null);
      }
    } else {
      setError('导入失败');
    }
  };

  const reset = () => {
    setText('');
    setStep(1);
    setPreviewData(null);
    setResult(null);
    setError(null);
    onClose();
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={reset}
      title="批量导入账户"
      className="max-w-2xl"
    >
      {/* Content */}
      <div className="py-2 overflow-y-auto max-h-[70vh]">
        {step === 1 && (
          <div className="space-y-4">
            <div className="bg-blue-500/10 text-blue-700 dark:text-blue-300 p-4 rounded-lg text-sm flex gap-2 border border-blue-500/30">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div>
                <p className="font-bold mb-1">支持格式：</p>
                <ul className="list-disc pl-4 space-y-1">
                  <li>邮箱----密码----client_id----refresh_token----恢复邮箱----恢复密码</li>
                  <li>邮箱----密码----refresh_token----client_id</li>
                  <li>邮箱----refresh_token</li>
                </ul>
              </div>
            </div>

            <textarea
              className="w-full h-64 border rounded-lg p-4 font-mono text-sm focus:ring-2 focus:ring-ring outline-none bg-background"
              placeholder="请粘贴账户数据，每行一条..."
              value={text}
              onChange={e => setText(e.target.value)}
            />

            <div className="flex justify-end gap-3">
              <select
                value={mergeMode}
                onChange={e => setMergeMode(e.target.value as MergeMode)}
                className="border rounded-md px-3 py-2 text-sm bg-background focus:ring-2 focus:ring-ring outline-none"
              >
                <option value="update">更新现有 (Update)</option>
                <option value="skip">跳过重复 (Skip)</option>
                <option value="replace">清空并替换 (Replace)</option>
              </select>
              <Button
                onClick={handleParse}
                disabled={loading || !text.trim()}
              >
                {loading ? '解析中...' : '下一步：解析预览'}
              </Button>
            </div>
          </div>
        )}

        {step === 2 && previewData && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="font-medium">
                解析成功：<span className="text-green-600">{previewData.parsed_count}</span> 条，
                错误：<span className="text-destructive">{previewData.error_count}</span> 条
              </p>
            </div>

            <div className="max-h-64 overflow-y-auto border rounded-lg bg-muted/80 p-4 space-y-2">
              {previewData.accounts.slice(0, 10).map((acc, i) => (
                <div key={i} className="text-xs font-mono truncate border-b border-border last:border-0 pb-1">
                  {acc.email}
                </div>
              ))}
              {previewData.accounts.length > 10 && (
                <div className="text-xs text-muted-foreground text-center pt-2">
                  ...还有 {previewData.accounts.length - 10} 条
                </div>
              )}
            </div>

            {previewData.errors.length > 0 && (
              <div className="max-h-32 overflow-y-auto border border-destructive/40 bg-destructive/15 rounded-lg p-4 text-xs text-destructive dark:text-red-400 font-mono">
                {previewData.errors.map((err, i) => (
                  <div key={i}>{err}</div>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-3 pt-4">
              <Button
                variant="outline"
                onClick={() => setStep(1)}
              >
                上一步
              </Button>
              <Button
                onClick={handleImport}
                disabled={loading || previewData.parsed_count === 0}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {loading ? '导入中...' : `确认导入 ${previewData.parsed_count} 条账户`}
              </Button>
            </div>
          </div>
        )}

        {step === 3 && result && (
          <div className="text-center space-y-6 py-8">
            <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto">
              <Upload className="w-8 h-8" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-foreground">导入完成</h3>
              <p className="text-muted-foreground mt-2">{result.message}</p>
            </div>
            <div className="bg-muted/80 rounded-lg p-4 max-w-sm mx-auto text-sm space-y-2 text-left border">
              <div className="flex justify-between"><span>新增：</span><Badge variant="default" className="bg-green-600">{result.added_count}</Badge></div>
              <div className="flex justify-between"><span>更新：</span><Badge variant="default" className="bg-blue-600">{result.updated_count}</Badge></div>
              <div className="flex justify-between"><span>跳过：</span><Badge variant="secondary">{result.skipped_count}</Badge></div>
              <div className="flex justify-between"><span>错误：</span><Badge variant="destructive">{result.error_count}</Badge></div>
            </div>
            <Button
              onClick={reset}
              size="lg"
            >
              完成
            </Button>
          </div>
        )}

        {error && (
          <Alert variant="destructive" className="mt-4">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>
    </Dialog>
  );
}
