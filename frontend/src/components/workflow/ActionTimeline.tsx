import { ActionEventItem } from "../../types";

interface ActionTimelineProps {
  events: ActionEventItem[];
}

export function ActionTimeline({ events }: ActionTimelineProps) {
  return (
    <div className="action-timeline">
      {events.length === 0 ? (
        <span className="muted">No status events yet.</span>
      ) : (
        events.map((item) => (
          <div className="timeline-event" key={item.id}>
            <span className="timeline-dot" />
            <div>
              <strong>{item.event_type.replaceAll("_", " ")}</strong>
              <time dateTime={item.timestamp}>{new Date(item.timestamp).toLocaleString()}</time>
              <p>
                {String(
                  item.detail?.detail ||
                    item.detail?.to ||
                    item.detail?.comments ||
                    "Workflow event recorded"
                )}
              </p>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
