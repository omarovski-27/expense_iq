import axios from "axios";
import toast from "react-hot-toast";

const client = axios.create({
  baseURL: (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api",
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail || "Something went wrong";
    toast.error(message);
    return Promise.reject(error);
  }
);

export default client;
