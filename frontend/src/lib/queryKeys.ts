export const queryKeys = {
  accounts: (page?: number, search?: string, pageSize?: number) =>
    page === undefined && search === undefined && pageSize === undefined
      ? (['accounts'] as const)
      : (['accounts', page, search, pageSize] as const),
  tags: () => ['tags'] as const,
  systemConfig: () => ['system-config'] as const,
  systemMetrics: () => ['system-metrics'] as const,
  emailMessages: (email: string, refreshCounter?: number, page?: number, pageSize?: number) =>
    ['email-messages', email, refreshCounter, page, pageSize] as const,
  emailMessagesBase: (email: string) => ['email-messages', email] as const,
} as const;
