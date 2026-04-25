import axios from "axios";
import toast from "react-hot-toast";

const env = (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env;
const baseURL = env?.VITE_API_URL ?? "http://localhost:8000/api";

const client = axios.create({
  baseURL,
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (!error.response) {
      toast.error("Cannot reach server. It may be waking up. Try again in 30 seconds.");
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
