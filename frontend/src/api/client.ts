import axios from "axios";
import toast from "react-hot-toast";
import { getDeviceKey } from "./ingest";

const env = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env;
const baseURL = env?.VITE_API_URL ?? "http://localhost:8000/api";

// Fired when the server rejects the device key (missing or wrong).
// KeyGate listens for it and shows the "enter your device key" screen.
export const AUTH_REQUIRED_EVENT = "expenseiq:auth-required";

const client = axios.create({
  baseURL,
});

// Every API call carries the device key saved on this device.
client.interceptors.request.use((config) => {
  const key = getDeviceKey();
  if (key) config.headers.set("X-API-Key", key);
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      toast.error("Cannot reach server. It may be waking up. Try again in 30 seconds.");
      return Promise.reject(error);
    }

    if (error.response.status === 401) {
      // No toast: the key screen explains what to do.
      window.dispatchEvent(new Event(AUTH_REQUIRED_EVENT));
      return Promise.reject(error);
    }

    if (error.response.status === 503) {
      toast.error("AI service temporarily unavailable.");
      return Promise.reject(error);
    }

    if (error.response.status === 500) {
      toast.error("Server error. Please try again.");
      return Promise.reject(error);
    }

    const message = error.response.data?.detail || "Something went wrong";
    toast.error(message);
    return Promise.reject(error);
  }
);

export default client;
