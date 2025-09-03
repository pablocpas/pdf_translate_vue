import axios, { 
  AxiosError, 
  AxiosResponse, 
  InternalAxiosRequestConfig,
  AxiosRequestConfig 
} from 'axios';
import { useTranslationStore } from '@/stores/translationStore';
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
      if (headers['Content-Type'] === 'application/json') {
        return JSON.stringify(data);
      }
      return data;
    }
  ],
});

// Interceptor de requests
apiClient.interceptors.request.use((config) => {
  return config;
});

// Interceptor de respuestas
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  async (error: AxiosError) => {
    console.error('API Error:', {
      status: error.response?.status,
      data: error.response?.data,
      config: {
        url: error.config?.url,
        method: error.config?.method,
      }
    });

    const config = error.config as CustomAxiosRequestConfig | undefined;
    
    // Reintentos para errores de red o servidor
    if (
      config &&
      (error.code === 'ECONNABORTED' || 
       (error.response?.status && error.response.status >= 500)) &&
      (config.retryCount || 0) < MAX_RETRIES
    ) {
      console.log('Retrying request...');
      const retryCount = (config.retryCount || 0) + 1;
      const newConfig = {
        ...config,
        retryCount
      };
      
      await new Promise(resolve => setTimeout(resolve, RETRY_DELAY * retryCount));
      return apiClient(newConfig);
    }

    if (!error.response) {
      console.error('Network error:', error.message);
      throw new NetworkError('Error de conexión');
    }

    const { status, data } = error.response;

    // Validar formato del error
    try {
      console.log('Attempting to parse error response:', data);
      const parsedError = ApiErrorSchema.parse(data);
      console.log('Parsed error:', parsedError);

      if (status === 401) {
        throw new AuthenticationError(parsedError.message);
      }

      throw new ApiRequestError(
        parsedError.message,
        status,
        parsedError
      );
    } catch (e) {
      console.error('Error parsing response:', e);
      if (e instanceof AuthenticationError || e instanceof ApiRequestError) {
        throw e;
      }
      // Fallback para errores no parseables
      throw new ApiRequestError(
        'Error inesperado del servidor',
        status
      );
    }
  }
);

export default apiClient;
