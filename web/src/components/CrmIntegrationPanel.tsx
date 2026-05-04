import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  useWebhooks,
  type WebhookConfig,
  type WebhookEventType,
} from '../context/WebhookContext';
import { WebhookDeliveryTable } from './WebhookDeliveryTable';

interface SectionDef {
  eventType: WebhookEventType;
  title: string;
  blurb: string;
  placeholder: string;
}

const SECTIONS: SectionDef[] = [
  {
    eventType: 'assessment_completed',
    title: 'Assessment Results Webhook',
    blurb:
      'When a member completes an assessment, send their results to this URL. Use this to push GPS or MyImpact results into your CRM (ROCK RMS, Planning Center, etc.).',
    placeholder: 'https://your-crm.example.com/hooks/gps-assessment',
  },
  {
    eventType: 'user_registered',
    title: 'New Member Registration Webhook',
    blurb:
      'When a new member registers for your church, send their info to this URL. Use this to add new members to email nurture (Kit, Mailchimp) via Zapier.',
    placeholder: 'https://hooks.zapier.com/hooks/catch/...',
  },
];


function WebhookSection({
  section,
  config,
  readOnly,
}: {
  section: SectionDef;
  config: WebhookConfig | undefined;
  readOnly: boolean;
}) {
  const { createWebhook, updateWebhook, deleteWebhook, testWebhook } = useWebhooks();

  const [url, setUrl] = useState(config?.webhook_url ?? '');
  const [isActive, setIsActive] = useState(config?.is_active ?? true);
  const [generateSecret, setGenerateSecret] = useState(false);
  const [savedSecret, setSavedSecret] = useState<string | null>(null);
  const [showLog, setShowLog] = useState(false);
  const [busy, setBusy] = useState<'save' | 'test' | 'delete' | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setUrl(config?.webhook_url ?? '');
    setIsActive(config?.is_active ?? true);
  }, [config?.id, config?.webhook_url, config?.is_active]);

  const handleSave = async () => {
    if (!url.trim()) {
      toast.error('Webhook URL is required');
      return;
    }
    setBusy('save');
    try {
      const result = config
        ? await updateWebhook(config.id, {
            webhook_url: url.trim(),
            is_active: isActive,
            generate_secret: generateSecret || undefined,
          })
        : await createWebhook({
            webhook_url: url.trim(),
            event_type: section.eventType,
            is_active: isActive,
            generate_secret: generateSecret,
          });
      if (result.secret_plaintext) {
        setSavedSecret(result.secret_plaintext);
      }
      setGenerateSecret(false);
      toast.success(config ? 'Webhook updated' : 'Webhook created');
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Failed to save webhook';
      toast.error(typeof detail === 'string' ? detail : 'Failed to save webhook');
    } finally {
      setBusy(null);
    }
  };

  const handleTest = async () => {
    if (!config) {
      toast.error('Save the webhook before testing');
      return;
    }
    setBusy('test');
    try {
      const result = await testWebhook(config.id);
      if (result.ok) {
        toast.success(`Test delivery succeeded (HTTP ${result.status_code})`);
      } else {
        toast.error(`Test failed: ${result.error ?? 'unknown error'}`);
      }
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Test failed');
    } finally {
      setBusy(null);
    }
  };

  const handleDelete = async () => {
    if (!config) return;
    setBusy('delete');
    try {
      await deleteWebhook(config.id);
      setUrl('');
      setIsActive(true);
      setSavedSecret(null);
      setConfirmDelete(false);
      toast.success('Webhook removed');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to remove webhook');
    } finally {
      setBusy(null);
    }
  };

  const sectionId = `webhook-${section.eventType}`;

  return (
    <div className="border border-brand-gray-light rounded-xl p-5 mb-4 bg-white">
      <h4 className="font-body font-bold text-lg text-brand-charcoal mb-1">
        {section.title}
      </h4>
      <p className="font-body text-sm text-brand-charcoal/70 mb-4">{section.blurb}</p>

      <label htmlFor={`${sectionId}-url`} className="block font-body text-sm font-bold text-brand-charcoal mb-1">
        Destination URL
      </label>
      <input
        id={`${sectionId}-url`}
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder={section.placeholder}
        disabled={readOnly || busy !== null}
        className="w-full h-[44px] px-4 bg-[rgba(136,192,195,0.17)] border border-brand-teal-light rounded-xl font-body text-base text-brand-charcoal placeholder:text-brand-charcoal/50 focus:outline-none focus:ring-2 focus:ring-brand-teal/30 disabled:opacity-60"
      />

      <div className="mt-3 flex items-center justify-between flex-wrap gap-3">
        <label className="inline-flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            disabled={readOnly || busy !== null}
            className="w-4 h-4 accent-brand-teal"
          />
          <span className="font-body text-sm text-brand-charcoal">Active</span>
        </label>

        <label className="inline-flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={generateSecret}
            onChange={(e) => setGenerateSecret(e.target.checked)}
            disabled={readOnly || busy !== null}
            className="w-4 h-4 accent-brand-teal"
          />
          <span className="font-body text-sm text-brand-charcoal">
            {config?.has_secret ? 'Regenerate signing secret' : 'Generate signing secret'}
          </span>
        </label>
      </div>

      {savedSecret && (
        <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded text-sm">
          <p className="font-bold text-amber-900 mb-1">Signing secret (shown once)</p>
          <code className="block font-mono text-xs text-amber-900 break-all bg-white px-2 py-1 rounded border border-amber-200">
            {savedSecret}
          </code>
          <p className="text-xs text-amber-800 mt-2">
            Copy this now. After this page closes you can only regenerate, never view, the secret.
            Verify each request by computing HMAC-SHA256 over the raw body and comparing to the
            <code className="mx-1 font-mono">X-GPS-Signature</code> header.
          </p>
        </div>
      )}

      {config?.has_secret && !savedSecret && (
        <p className="mt-3 text-xs text-brand-charcoal/60">
          Signing secret configured (<span className="font-mono">{config.secret_masked}</span>).
          Tick &ldquo;Regenerate&rdquo; and Save to rotate it.
        </p>
      )}

      <div className="mt-5 flex flex-wrap gap-3">
        <button
          onClick={handleSave}
          disabled={readOnly || busy !== null}
          className="h-[40px] px-5 bg-brand-teal text-white font-body font-bold text-sm rounded-xl hover:bg-brand-teal/90 transition-colors disabled:opacity-50"
        >
          {busy === 'save' ? 'Saving...' : config ? 'Save changes' : 'Create webhook'}
        </button>

        {config && (
          <button
            onClick={handleTest}
            disabled={readOnly || busy !== null}
            className="h-[40px] px-5 bg-brand-teal-light text-brand-charcoal font-body font-bold text-sm rounded-xl hover:bg-brand-teal-light/80 transition-colors disabled:opacity-50"
          >
            {busy === 'test' ? 'Testing...' : 'Test connection'}
          </button>
        )}

        {config && (
          <button
            onClick={() => setConfirmDelete(true)}
            disabled={readOnly || busy !== null}
            className="h-[40px] px-5 bg-white border border-red-300 text-red-700 font-body font-bold text-sm rounded-xl hover:bg-red-50 transition-colors disabled:opacity-50"
          >
            Remove
          </button>
        )}

        {config && (
          <button
            onClick={() => setShowLog(s => !s)}
            disabled={busy !== null}
            className="h-[40px] px-5 bg-transparent text-brand-teal font-body font-bold text-sm hover:underline disabled:opacity-50"
          >
            {showLog ? 'Hide delivery log' : 'Show delivery log'}
          </button>
        )}
      </div>

      {confirmDelete && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="font-body text-sm text-red-800 mb-2">
            Remove this webhook? Future events will no longer be delivered.
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDelete}
              disabled={busy !== null}
              className="h-[36px] px-4 bg-red-600 text-white font-body font-bold text-sm rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
            >
              {busy === 'delete' ? 'Removing...' : 'Yes, remove'}
            </button>
            <button
              onClick={() => setConfirmDelete(false)}
              className="h-[36px] px-4 bg-white border border-brand-gray-light text-brand-charcoal font-body font-bold text-sm rounded-lg hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {config && showLog && (
        <div className="mt-5 pt-4 border-t border-brand-gray-light">
          <h5 className="font-body font-bold text-sm text-brand-charcoal mb-2">Recent deliveries (30 days)</h5>
          <WebhookDeliveryTable webhookId={config.id} />
        </div>
      )}
    </div>
  );
}


export function CrmIntegrationPanel({ readOnly = false }: { readOnly?: boolean }) {
  const { webhooks, isLoading, loadError, loadWebhooks } = useWebhooks();

  useEffect(() => {
    loadWebhooks();
  }, [loadWebhooks]);

  const byType = new Map(webhooks.map(w => [w.event_type, w]));

  return (
    <div>
      <h3 className="font-body font-bold text-lg text-brand-charcoal mb-2">CRM Integration</h3>
      <p className="font-body text-sm text-brand-charcoal/70 mb-4">
        Push GPS data into your church management system. Configure separate webhooks for assessment
        completions and new member registrations.
      </p>

      {isLoading && webhooks.length === 0 ? (
        <p className="font-body text-sm text-brand-gray-med py-2">Loading webhooks...</p>
      ) : loadError ? (
        <p className="font-body text-sm text-red-700 py-2">{loadError}</p>
      ) : (
        SECTIONS.map(section => (
          <WebhookSection
            key={section.eventType}
            section={section}
            config={byType.get(section.eventType)}
            readOnly={readOnly}
          />
        ))
      )}
    </div>
  );
}
