import axios, { 
  AxiosError, 
  AxiosResponse, 
  InternalAxiosRequestConfig,
  AxiosRequestConfig 
} from 'axios';
import { useAuthStore } from '@/stores/authStore';
import { ApiErrorSchema, ApiRequestError, AuthenticationError, NetworkError } from '@/types/api';

const MAX_RETRIES = 3;
const RETRY_DELAY = 1000;

interface CustomAxiosRequestConfig extends InternalAxiosRequestConfig {
  retryCount?: number;
}

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 30000,
  headers: {
    'Accept': 'application/json',
  },
  transformRequest: [
    function (data, headers) {
      if (data instanceof FormData) {
        headers['Content-Type'] = 'multipart/form-data';
        return data;
      }
      return JSON.stringify(data);
    }
  ],
});

// Interceptor para añadir token de autenticación
apiClient.interceptors.request.use((config) => {
  const store = useAuthStore();
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`;
  }
  return config;
});

// Interceptor para manejar errores y validar respuestas
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    const config = error.config as CustomAxiosRequestConfig | undefined;
    
    // Reintentar en caso de errores de red o 5xx
    if (
      config &&
      (error.code === 'ECONNABORTED' || 
       (error.response?.status && error.response.status >= 500)) &&
      (config.retryCount || 0) < MAX_RETRIES
    ) {
      const retryCount = (config.retryCount || 0) + 1;
      const newConfig = {
        ...config,
        retryCount
      };
      
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * retryCount));
      return apiClient(newConfig);
    }

    if (!error.response) {
      throw new NetworkError('Error de conexión');
    }

    const { status, data } = error.response;

    // Validar formato del error
    try {
      const parsedError = ApiErrorSchema.parse(data);

      if (status === 401) {
        const authStore = useAuthStore();
        authStore.clearToken();
        throw new AuthenticationError(parsedError.message);
      }

      throw new ApiRequestError(
        parsedError.message,
        status,
        parsedError
      );
    } catch (e) {
      if (e instanceof AuthenticationError || e instanceof ApiRequestError) {
        throw e;
      }
      // Si el error no tiene el formato esperado
      throw new ApiRequestError(
        'Error inesperado del servidor',
        status
      );
    }
  }
);

export default apiClient;
