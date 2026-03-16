export function requireElement<T extends Element>(id: string, type: { new (): T }): T | null {
  const el = document.getElementById(id);
  return el instanceof type ? el : null;
}
