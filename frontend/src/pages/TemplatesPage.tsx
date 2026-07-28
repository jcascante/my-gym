import { useEffect, useState } from 'react';
import { Alert, Spinner } from '@/components';
import TemplateListItem from '@/components/TemplateListItem';
import { listTemplates } from '@/api/templates';
import { getErrorMessage } from '@/api/errors';
import type { Template } from '@/types/template';

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<Template[]>([]);
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listTemplates();
      setTemplates(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTemplates();
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-dvh" role="status">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-neutral-50 dark:bg-neutral-900 py-8 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="display-md mb-2">Program Templates</h1>
          <p className="body-md text-neutral-600 dark:text-neutral-400">
            Browse all available program templates. Select one to see detailed configuration.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <Alert type="error" dismissible onDismiss={() => setError(null)} className="mb-6">
            <div className="flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={loadTemplates}
                className="ml-4 px-3 py-1 bg-error-600 hover:bg-error-700 text-white rounded text-sm font-medium"
              >
                Retry
              </button>
            </div>
          </Alert>
        )}

        {/* Empty State */}
        {templates.length === 0 && !error && (
          <div className="text-center py-12">
            <p className="body-lg text-neutral-600 dark:text-neutral-400">No templates found</p>
          </div>
        )}

        {/* Templates List */}
        {templates.length > 0 && (
          <div>
            {templates.map((template) => (
              <TemplateListItem
                key={template.slug}
                template={template}
                isExpanded={expandedSlug === template.slug}
                onToggle={() =>
                  setExpandedSlug(expandedSlug === template.slug ? null : template.slug)
                }
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
