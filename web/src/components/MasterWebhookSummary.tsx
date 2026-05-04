import { useEffect, useState } from 'react';
import { api } from '../context/AuthContext';

interface MasterWebhookConfig {
  id: string;
  organization_id: string;
  event_type: string;
  webhook_url_masked: string;
  is_active: boolean;
  has_secret: boolean;
  last_delivery_status?: string | null;
  last_delivery_at?: string | null;
}

const EVENT_LABELS: Record<string, string> = {
  assessment_completed: 'Assessment Results',
  user_registered: 'New Member Registration',
};

function relativeTime(iso?: string | null): string {
  if (!iso) return '—';
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return 'just now';
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

function statusColor(status?: string | null): string {
  if (status === 'success') return 'text-green-700';
  if (status === 'failed' || status === 'dead') return 'text-red-700';
  return 'text-brand-charcoal/60';
}

export function MasterWebhookSummary({ churchId }: { churchId: string }) {
  const [configs, setConfigs] = useState<MasterWebhookConfig[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get(`/master/organizations/${churchId}/webhooks`)
      .then(res => { if (!cancelled) setConfigs(res.data.webhooks); })
      .catch(() => { if (!cancelled) setError('Failed to load webhooks'); });
    return () => { cancelled = true; };
  }, [churchId]);

  if (error) {
    return <p className="font-body text-sm text-red-700">{error}</p>;
  }
  if (configs === null) {
    return <p className="font-body text-sm text-brand-gray-med">Loading webhooks…</p>;
  }

  // Always render both event types so admins can see what's missing.
  const byType = new Map(configs.map(c => [c.event_type, c]));
  const eventTypes = ['assessment_completed', 'user_registered'];

  return (
    <div className="space-y-2">
      {eventTypes.map(eventType => {
        const c = byType.get(eventType);
        if (!c) {
          return (
            <div key={eventType} className="flex items-center justify-between text-sm">
              <span className="font-body text-brand-charcoal/80">{EVENT_LABELS[eventType]}</span>
              <span className="font-body text-xs text-brand-charcoal/50 italic">not configured</span>
            </div>
          );
        }
        return (
          <div key={eventType} className="flex items-center justify-between text-sm">
            <div className="flex flex-col">
              <span className="font-body text-brand-charcoal/80">
                {EVENT_LABELS[eventType]}
                {!c.is_active && <span className="ml-2 text-xs italic text-amber-700">(disabled)</span>}
                {c.has_secret && <span className="ml-2 text-xs text-brand-charcoal/60">[signed]</span>}
              </span>
              <span className="font-mono text-xs text-brand-charcoal/50 truncate max-w-[420px]">
                {c.webhook_url_masked}
              </span>
            </div>
            <div className={`text-xs font-body ${statusColor(c.last_delivery_status)}`}>
              {c.last_delivery_status ? `${c.last_delivery_status} · ${relativeTime(c.last_delivery_at)}` : 'no deliveries yet'}
            </div>
          </div>
        );
      })}
    </div>
  );
}
