export function SkeletonBlock({ height = 20, width = "100%", style }) {
  return <div className="skeleton" style={{ height, width, ...style }} />;
}

export function MatchSkeleton() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="panel" style={{ display: "flex", justifyContent: "space-between" }}>
        <SkeletonBlock width={140} height={32} />
        <SkeletonBlock width={80} height={32} />
        <SkeletonBlock width={140} height={32} />
      </div>
      <div className="panel" style={{ display: "flex", gap: 16 }}>
        <SkeletonBlock width={64} height={64} style={{ borderRadius: "50%" }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          <SkeletonBlock width={180} height={24} />
          <SkeletonBlock width={240} height={14} />
        </div>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Array.from({ length: 8 }).map((_, i) => (
            <SkeletonBlock key={i} height={40} />
          ))}
        </div>
        <div className="panel">
          <SkeletonBlock height={280} />
        </div>
      </div>
    </div>
  );
}
