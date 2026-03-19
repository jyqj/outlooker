export const queryKeys = {
  accounts: (page?: number, search?: string, pageSize?: number) =>
    page === undefined && search === undefined && pageSize === undefined
      ? (['accounts'] as const)
      : (['accounts', page, search, pageSize] as const),
  tags: () => ['tags'] as const,
  tagStats: () => ['tag-stats'] as const,
  systemConfig: () => ['system-config'] as const,
  systemMetrics: () => ['system-metrics'] as const,
  dashboardSummary: () => ['dashboard-summary'] as const,
  emailMessages: (email: string, refreshCounter?: number, page?: number, pageSize?: number) =>
    ['email-messages', email, refreshCounter, page, pageSize] as const,
  emailMessagesBase: (email: string) => ['email-messages', email] as const,
  outlookAccounts: (status?: string, accountType?: string, limit?: number, offset?: number) =>
    ['outlook-accounts', status, accountType, limit, offset] as const,
  outlookAccountDetail: (email: string) => ['outlook-account-detail', email] as const,
  outlookProfile: (email: string, refresh?: boolean) => ['outlook-profile', email, refresh] as const,
  outlookAuthMethods: (email: string) => ['outlook-auth-methods', email] as const,
  outlookMailboxSettings: (email: string) => ['outlook-mailbox-settings', email] as const,
  outlookRegionalSettings: (email: string) => ['outlook-regional-settings', email] as const,
} as const;
