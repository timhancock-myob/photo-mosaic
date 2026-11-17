import { useHealth } from "./api/hooks";

export function App() {
  const health = useHealth();

  return (
    <main>
      <h1>Photo Mosaic</h1>
      <p>
        API:{" "}
        {health.isPending
          ? "connecting…"
          : health.isError
            ? "unavailable"
            : `${health.data.status} (core ${health.data.core_version})`}
      </p>
    </main>
  );
}
