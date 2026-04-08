import axios from "axios";
import { api } from "./client";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const isAccessDenied = (err: unknown): boolean =>
  err instanceof ApiError && (err.status === 401 || err.status === 403);

// Intercept 401/403 and re-throw as typed ApiError
api.interceptors.response.use(
  (res) => res,
  (err: unknown) => {
    if (axios.isAxiosError(err) && err.response) {
      const { status, statusText } = err.response;
      if (status === 401 || status === 403) {
        return Promise.reject(new ApiError(status, statusText));
      }
    }
    return Promise.reject(err);
  },
);
