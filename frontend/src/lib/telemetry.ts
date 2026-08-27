type SentryModule = typeof import('@sentry/react');

const sentryDsn = import.meta.env.VITE_SENTRY_DSN?.trim();
let sentryModulePromise: Promise<SentryModule | null> | null = null;
let sentryInitializationPromise: Promise<SentryModule | null> | null = null;

function loadSentry(): Promise<SentryModule | null> {
  if (!sentryDsn) {
    return Promise.resolve(null);
  }

  if (!sentryModulePromise) {
    sentryModulePromise = import('@sentry/react').catch((error: unknown) => {
      if (import.meta.env.DEV && typeof console !== 'undefined') {
        console.warn('[Outlooker] Failed to load telemetry', error);
      }
      return null;
    });
  }

  return sentryModulePromise;
}

function initializeSentry(): Promise<SentryModule | null> {
  if (!sentryInitializationPromise) {
    sentryInitializationPromise = loadSentry().then((Sentry) => {
      if (!Sentry || !sentryDsn) {
        return null;
      }

      Sentry.init({
        dsn: sentryDsn,
        environment: import.meta.env.MODE,
        integrations: [
          Sentry.browserTracingIntegration(),
          Sentry.replayIntegration(),
        ],
        tracesSampleRate: import.meta.env.PROD ? 0.1 : 1.0,
        replaysSessionSampleRate: 0.1,
        replaysOnErrorSampleRate: 1.0,
      });

      return Sentry;
    });
  }

  return sentryInitializationPromise;
}

export async function initializeTelemetry(): Promise<void> {
  await initializeSentry();
}

export function captureException(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  if (!sentryDsn) {
    return;
  }

  void initializeSentry().then((Sentry) => {
    Sentry?.captureException(error, context ? { extra: context } : undefined);
  });
}
