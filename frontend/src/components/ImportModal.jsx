import React, { useState } from 'react';
import { X, Upload, AlertCircle } from 'lucide-react';
import api from '../lib/api';
import { useApiAction } from '../lib/hooks';

export default function ImportModal({ isOpen, onClose, onSuccess }) {
  const [text, setText] = useState('');
  const [mergeMode, setMergeMode] = useState('update');
  const [step, setStep] = useState(1); // 1: Input, 2: Confirm
  const [previewData, setPreviewData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const apiAction = useApiAction({ showSuccessToast: false });

  if (!isOpen) return null;

  const handleParse = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    const response = await apiAction(
      () => api.post('/api/parse-import-text', { text }),
      { errorMessage: '解析失败' },
    );
    setLoading(false);

    if (response.ok) {
      setPreviewData(response.data.data);
      setStep(2);
    } else {
      setError(response.data?.message || '解析失败');
    }
  };

  const handleImport = async () => {
    if (!previewData?.accounts?.length) {
      setError('请先完成解析步骤');
      return;
    }
    setLoading(true);
    setError(null);
    const response = await apiAction(
      () =>
        api.post('/api/import', {
          accounts: previewData.accounts,
          merge_mode: mergeMode,
        }),
      {
        successMessage: '导入成功',
        errorMessage: '导入失败',
        showSuccessToast: true,
      },
    );
    setLoading(false);

    if (response.ok) {
      setResult(response.data);
      setStep(3);
      if (onSuccess) onSuccess();
    } else if (response.data) {
      setResult(response.data);
      setStep(3);
      if (response.data.message) {
        setError(response.data.message);
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
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl w-full max-w-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-semibold text-lg">批量导入账户</h3>
          <button onClick={reset} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto flex-1">
          {step === 1 && (
            <div className="space-y-4">
              <div className="bg-blue-50 text-blue-700 p-4 rounded-lg text-sm flex gap-2">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <div>
                  <p className="font-bold mb-1">支持格式：</p>
                  <ul className="list-disc pl-4 space-y-1">
                    <li>邮箱----密码----refresh_token----client_id</li>
                    <li>邮箱----refresh_token</li>
                  </ul>
                </div>
              </div>
              
              <textarea
                className="w-full h-64 border rounded-lg p-4 font-mono text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="请粘贴账户数据，每行一条..."
                value={text}
                onChange={e => setText(e.target.value)}
              />
              
              <div className="flex justify-end gap-3">
                <select 
                  value={mergeMode} 
                  onChange={e => setMergeMode(e.target.value)}
                  className="border rounded-lg px-3 py-2 text-sm"
                >
                  <option value="update">更新现有 (Update)</option>
                  <option value="skip">跳过重复 (Skip)</option>
                  <option value="replace">清空并替换 (Replace)</option>
                </select>
                <button
                  onClick={handleParse}
                  disabled={loading || !text.trim()}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                >
                  {loading ? '解析中...' : '下一步：解析预览'}
                </button>
              </div>
            </div>
          )}

          {step === 2 && previewData && (
            <div className="space-y-4">
               <div className="flex justify-between items-center">
                   <p className="font-medium">
                       解析成功：{previewData.parsed_count} 条，错误：{previewData.error_count} 条
                   </p>
                   {previewData.error_count > 0 && (
                       <span className="text-red-500 text-sm">请检查下方错误</span>
                   )}
               </div>
               
               <div className="max-h-64 overflow-y-auto border rounded-lg bg-gray-50 p-4 space-y-2">
                   {previewData.accounts.slice(0, 10).map((acc, i) => (
                       <div key={i} className="text-xs font-mono truncate border-b last:border-0 pb-1">
                           {acc.email}
                       </div>
                   ))}
                   {previewData.accounts.length > 10 && (
                       <div className="text-xs text-gray-500 text-center pt-2">
                           ...还有 {previewData.accounts.length - 10} 条
                       </div>
                   )}
               </div>

               {previewData.errors.length > 0 && (
                   <div className="max-h-32 overflow-y-auto border border-red-200 bg-red-50 rounded-lg p-4 text-xs text-red-600 font-mono">
                       {previewData.errors.map((err, i) => (
                           <div key={i}>{err}</div>
                       ))}
                   </div>
               )}

               <div className="flex justify-end gap-3 pt-4">
                   <button
                     onClick={() => setStep(1)}
                     className="px-4 py-2 border rounded-lg hover:bg-gray-50"
                   >
                       上一步
                   </button>
                   <button
                     onClick={handleImport}
                     disabled={loading || previewData.parsed_count === 0}
                     className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50"
                   >
                       {loading ? '导入中...' : `确认导入 ${previewData.parsed_count} 条账户`}
                   </button>
               </div>
            </div>
          )}

          {step === 3 && result && (
            <div className="text-center space-y-6 py-8">
                <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto">
                    <Upload className="w-8 h-8" />
                </div>
                <div>
                    <h3 className="text-xl font-bold text-gray-900">导入完成</h3>
                    <p className="text-gray-500 mt-2">{result.message}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4 max-w-sm mx-auto text-sm space-y-1 text-left">
                    <div className="flex justify-between"><span>新增：</span><span className="font-mono font-bold text-green-600">{result.added_count}</span></div>
                    <div className="flex justify-between"><span>更新：</span><span className="font-mono font-bold text-blue-600">{result.updated_count}</span></div>
                    <div className="flex justify-between"><span>跳过：</span><span className="font-mono font-bold text-gray-600">{result.skipped_count}</span></div>
                    <div className="flex justify-between"><span>错误：</span><span className="font-mono font-bold text-red-600">{result.error_count}</span></div>
                </div>
                <button
                  onClick={reset}
                  className="bg-gray-900 text-white px-6 py-2 rounded-lg hover:bg-gray-800"
                >
                    完成
                </button>
            </div>
          )}
          
          {error && (
             <div className="bg-red-50 text-red-600 p-4 rounded-lg mt-4">
                 {error}
             </div>
          )}
        </div>
      </div>
    </div>
  );
}

