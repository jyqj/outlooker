import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, TimerReset } from 'lucide-react';

import api, { clearAuthTokens, getStoredAccessToken } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { ProtocolBindWizard } from '@/components/outlook/protocol/ProtocolBindWizard';
import { DashboardHeader } from '../dashboard/components/DashboardHeader';

export default function OutlookTasksPage() {
  const navigate = useNavigate();
  const [tasks, setTasks] = useState<Array<Record<string, unknown>>>([]);
  const [selectedTask, setSelectedTask] = useState<Record<string, unknown> | null>(null);
  const [steps, setSteps] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(false);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/outlook/tasks');
      setTasks(res.data?.data?.items ?? []);
    } finally {
      setLoading(false);
    }
  };

  const loadTaskDetail = async (taskId: number) => {
    const res = await api.get(`/api/outlook/tasks/${taskId}`);
    setSelectedTask(res.data?.data?.task ?? null);
    setSteps(res.data?.data?.steps ?? []);
  };

  const handleLogout = async () => {
    try {
      await api.post('/api/admin/logout', {});
    } finally {
      clearAuthTokens();
      navigate('/admin/login');
    }
  };

  useEffect(() => {
    void loadTasks();
  }, []);

  useEffect(() => {
    const token = getStoredAccessToken();
    if (!token) {
      return;
    }
    const source = new EventSource(`/api/outlook/tasks/events/stream?token=${encodeURIComponent(token)}`);
    source.onmessage = () => {
      void loadTasks();
      if (selectedTask?.id) {
        void loadTaskDetail(Number(selectedTask.id));
      }
    };
    return () => {
      source.close();
    };
  }, [selectedTask?.id]);

  return (
    <div className="min-h-screen bg-muted/60 flex flex-col">
      <DashboardHeader onLogout={handleLogout} />
      <main className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">Outlook 任务中心</h2>
            <p className="text-sm text-muted-foreground">这里将展示协议绑定、换绑与重试任务。</p>
          </div>
          <Button variant="outline" onClick={() => navigate('/admin')}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            返回后台
          </Button>
          <Button onClick={() => loadTasks()}>
            <RefreshCw className="w-4 h-4 mr-2" />
            刷新任务
          </Button>
        </div>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TimerReset className="w-5 h-5" />
              任务状态
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading ? (
              <p className="text-sm text-muted-foreground">正在加载任务...</p>
            ) : tasks.length === 0 ? (
              <p className="text-sm text-muted-foreground">暂无协议任务。</p>
            ) : (
              tasks.map((task) => (
                <div key={String(task.id)} className="rounded-xl border p-4 flex items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="font-medium">#{String(task.id)} · {String(task.task_type)}</div>
                    <div className="text-sm text-muted-foreground">
                      {String(task.target_email)} · 状态: {String(task.status)} · 重试: {String(task.retry_count ?? 0)}
                    </div>
                    {task.error_message ? (
                      <div className="text-xs text-destructive">{String(task.error_message)}</div>
                    ) : null}
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" onClick={() => loadTaskDetail(Number(task.id))}>查看详情</Button>
                    <Button variant="outline" onClick={() => api.post(`/api/outlook/tasks/${String(task.id)}/cancel`).then(() => loadTasks())}>
                      取消
                    </Button>
                    <Button onClick={() => api.post(`/api/outlook/tasks/${String(task.id)}/retry`).then(() => loadTasks())}>
                      重试
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>任务详情</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!selectedTask ? (
              <p className="text-sm text-muted-foreground">选择一条任务后查看步骤详情。</p>
            ) : (
              <>
                <div className="text-sm text-muted-foreground">
                  当前任务: #{String(selectedTask.id)} · {String(selectedTask.task_type)} · {String(selectedTask.status)}
                </div>
                <div className="space-y-2">
                  {steps.map((step, index) => (
                    <div key={`${String(step.id ?? index)}`} className="rounded-lg border p-3">
                      <div className="font-medium">{String(step.step)} · {String(step.status)}</div>
                      <div className="text-xs text-muted-foreground">{String(step.detail ?? '')}</div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <ProtocolBindWizard />
      </main>
    </div>
  );
}
