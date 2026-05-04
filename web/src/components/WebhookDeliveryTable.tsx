import { useEffect, useState } from 'react';
import { useWebhooks, type WebhookDelivery } from '../context/WebhookContext';

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString();
}

function StatusPill({ status }: { status: WebhookDelivery['status'] }) {
  const colors: Record<WebhookDelivery['status'], string> = {
    success: 'bg-green-100 text-green-800',
    failed: 'bg-amber-100 text-amber-800',
    dead: 'bg-red-100 text-red-800',
    pending: 'bg-gray-100 text-gray-700',
  };
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      {status}
    </span>
  );
}

export function WebhookDeliveryTable({ webhookId }: { webhookId: string }) {
  const { fetchDeliveries } = useWebhooks();
  const [deliveries, setDeliveries] = useState<WebhookDelivery[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    fetchDeliveries(webhookId, { limit: 25 })
      .then(res => { if (!cancelled) setDeliveries(res.deliveries); })
      .catch(() => { if (!cancelled) setDeliveries([]); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [webhookId, fetchDeliveries]);

  const toggleRow = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (isLoading) {
    return <p className="font-body text-sm text-brand-gray-med py-2">Loading deliveries...</p>;
  }

  if (deliveries.length === 0) {
    return (
      <p className="font-body text-sm text-brand-gray-med py-2">
        No deliveries yet. After an assessment is completed, attempts will appear here.
      </p>
    );
  }

  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-brand-gray-light">
          <th className="text-left py-2 font-body font-bold text-brand-charcoal/80">When</th>
          <th className="text-left py-2 font-body font-bold text-brand-charcoal/80">Event</th>
          <th className="text-left py-2 font-body font-bold text-brand-charcoal/80">Status</th>
          <th className="text-left py-2 font-body font-bold text-brand-charcoal/80">HTTP</th>
          <th className="text-left py-2 font-body font-bold text-brand-charcoal/80">Attempts</th>
        </tr>
      </thead>
      <tbody>
        {deliveries.map(d => {
          const isOpen = expanded.has(d.id);
          const failed = d.status === 'failed' || d.status === 'dead';
          return (
            <>
              <tr
                key={d.id}
                className={`border-b border-brand-gray-light/50 ${failed ? 'cursor-pointer hover:bg-red-50/50' : ''}`}
                onClick={failed ? () => toggleRow(d.id) : undefined}
              >
                <td className="py-2 font-body text-brand-charcoal/80">{formatTime(d.created_at)}</td>
                <td className="py-2 font-body text-brand-charcoal/80">{d.event_type}</td>
                <td className="py-2"><StatusPill status={d.status} /></td>
                <td className="py-2 font-body text-brand-charcoal/80">{d.http_status_code ?? '—'}</td>
                <td className="py-2 font-body text-brand-charcoal/80">{d.attempts}</td>
              </tr>
              {isOpen && d.error_message && (
                <tr key={`${d.id}-err`}>
                  <td colSpan={5} className="px-2 py-2 bg-red-50/50 border-b border-brand-gray-light/50">
                    <pre className="text-xs text-red-800 whitespace-pre-wrap break-words font-mono">
                      {d.error_message}
                    </pre>
                  </td>
                </tr>
              )}
            </>
          );
        })}
      </tbody>
    </table>
  );
}
