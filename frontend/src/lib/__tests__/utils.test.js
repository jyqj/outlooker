describe('logError', () => {
  it('logs message with prefix when enabled', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.resetModules();
    const { logError } = await import('../utils');

    const error = new Error('boom');
    await logError('测试日志', error);

    expect(consoleSpy).toHaveBeenCalledWith('[Outlook Manager] 测试日志', error);
    consoleSpy.mockRestore();
  });
});
