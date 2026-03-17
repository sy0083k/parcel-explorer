import { HttpError } from "../http";

export function resolveAdminErrorMessage(error: unknown, fallback: string): string {
  return error instanceof HttpError ? error.message : fallback;
}
