/**
 * Platform Detection Display Component
 * 
 * Shows platform detection results including confidence score,
 * parser execution status, and extracted entities.
 */

import { useMemo } from "react";
import { Badge, Card, ProgressBar, EntityPill } from "@/components/ui";
import type { PlatformDetectionData } from "@/hooks/usePlatformDetection";

interface PlatformEntity {
  entity_type: string;
  value: string;
  source_file?: string;
}

interface PlatformDetectionCardProps {
  data: PlatformDetectionData | null;
  loading?: boolean;
}

const PLATFORM_LABELS: Record<string, string> = {
  blue_prism: "Blue Prism",
  uipath: "UiPath",
  appian: "Appian",
  automation_anywhere: "Automation Anywhere",
  pega: "Pega",
  unknown: "Unknown Platform",
};

const PLATFORM_COLORS: Record<string, string> = {
  blue_prism: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  uipath: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  appian: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  automation_anywhere: "bg-red-500/10 text-red-400 border-red-500/20",
  pega: "bg-green-500/10 text-green-400 border-green-500/20",
  unknown: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

export function PlatformDetectionCard({ data, loading = false }: PlatformDetectionCardProps) {
  // Group entities by type (memoized for performance) - must be called before early returns
  const entitiesByType = useMemo(() => {
    if (!data) return {};
    const grouped: Record<string, PlatformEntity[]> = {};
    data.extracted_entities.forEach((entity) => {
      if (!grouped[entity.entity_type]) {
        grouped[entity.entity_type] = [];
      }
      grouped[entity.entity_type].push(entity);
    });
    return grouped;
  }, [data]);

  // Early returns after hooks
  if (loading) {
    return (
      <Card className="p-6 animate-pulse">
        <div className="h-4 bg-dark-bg-secondary rounded w-1/3 mb-4"></div>
        <div className="h-8 bg-dark-bg-secondary rounded w-2/3"></div>
      </Card>
    );
  }

  if (!data) {
    return (
      <Card className="p-6">
        <p className="text-dark-text-secondary text-sm">
          No platform detection data available
        </p>
      </Card>
    );
  }

  const platformLabel = PLATFORM_LABELS[data.detected_platform] || data.detected_platform;
  const platformColor = PLATFORM_COLORS[data.detected_platform] || PLATFORM_COLORS.unknown;
  const confidencePercent = Math.round(data.confidence_score * 100);

  return (
    <Card className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-dark-text-primary mb-1">
            Platform Detection
          </h3>
          <p className="text-xs text-dark-text-tertiary uppercase tracking-wider">
            {data.detection_method} detection
          </p>
        </div>
        {data.parser_executed && data.parser_version && (
          <Badge variant="success" className="text-xs">
            Parser v{data.parser_version}
          </Badge>
        )}
      </div>

      {/* Platform and Confidence */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-dark-text-tertiary mb-2">Detected Platform</p>
          <span className={`inline-flex items-center px-3 py-1 rounded-md border text-sm font-medium ${platformColor}`}>
            {platformLabel}
          </span>
        </div>
        <div>
          <p className="text-xs text-dark-text-tertiary mb-2">Confidence Score</p>
          <ProgressBar value={confidencePercent} variant="primary" size="md" />
        </div>
      </div>

      {/* Extracted Entities */}
      {data.extracted_entities.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-dark-text-primary mb-3">
            Extracted Entities ({data.extracted_entities.length})
          </h4>
          <div className="space-y-3">
            {Object.entries(entitiesByType).map(([type, entities]) => (
              <div key={type} className="space-y-2">
                <p className="text-xs font-medium text-dark-text-secondary uppercase tracking-wider">
                  {type.replace(/_/g, " ")} ({entities.length})
                </p>
                <div className="flex flex-wrap gap-2">
                  {entities.map((entity, idx) => (
                    <EntityPill
                      key={`${type}-${idx}`}
                      label={entity.value}
                      tooltip={entity.source_file}
                      variant="default"
                      size="md"
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Entities Message */}
      {data.parser_executed && data.extracted_entities.length === 0 && (
        <div className="text-center py-4">
          <p className="text-dark-text-tertiary text-sm">
            Parser executed but no entities extracted
          </p>
        </div>
      )}

      {/* Parser Not Executed */}
      {!data.parser_executed && data.detected_platform !== "unknown" && (
        <div className="rounded-md bg-yellow-500/10 border border-yellow-500/20 p-3">
          <p className="text-xs text-yellow-400">
            <strong>Note:</strong> Confidence score below parser execution threshold. 
            Platform detected but entities not extracted.
          </p>
        </div>
      )}
    </Card>
  );
}

export default PlatformDetectionCard;
