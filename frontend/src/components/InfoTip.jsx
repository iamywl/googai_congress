// Small "i" affordance that reveals a one-line explanation of a metric on hover
// or keyboard focus. Purely presentational; the bubble is positioned and styled
// in App.css (.infotip / .infotip-bubble).
export default function InfoTip({ text, label }) {
  return (
    <span
      className="infotip"
      tabIndex={0}
      role="note"
      aria-label={label ? `${label}: ${text}` : text}
    >
      <span className="infotip-icon" aria-hidden="true">
        i
      </span>
      <span className="infotip-bubble" role="tooltip">
        {text}
      </span>
    </span>
  );
}
