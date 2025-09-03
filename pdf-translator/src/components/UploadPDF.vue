<template>
  <div class="upload-container">
    <!-- Card principal -->
    <div class="upload-card" :class="{ 'is-processing': isProcessing }">
      <div class="card-header">
        <h2 class="title">Traductor de PDF</h2>
        <p class="subtitle">Traduce documentos PDF a múltiples idiomas</p>
      </div>

      <form @submit.prevent="handleSubmit">
        <FileUploader
          v-model="form.file"
          :error="errors.file"
        />

        <ConfigurationPanel
          v-model="form.config"
          :errors="{ languageModel: errors.config }"
          class="form-section"
        />

        <LanguageSelect
          class="form-section"
          v-model="form.targetLanguage"
          :error="errors.targetLanguage"
        />

        <button
          type="submit"
          class="submit-button"
          :disabled="isSubmitting || (isProcessing && pollingInterval !== null)"
        >
          <div class="button-content">
            <!-- Icono del botón -->
            <svg v-if="!isProcessing" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <svg v-else class="spinner" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
            </svg>
            
            <!-- Texto del botón -->
            <span v-if="isSubmitting">Subiendo archivo...</span>
            <span v-else-if="isProcessing">{{ currentStepText }}...</span>
            <span v-else>Traducir PDF</span>
          </div>
        </button>
      </form>

      <!-- Overlay de procesamiento -->
      <div class="processing-overlay" v-if="isProcessing">
        <div class="processing-content">
          <ErrorBanner
            v-if="errors.general"
            :message="errors.general"
            :error-code="errors.code"
            :show-retry="showRetryButton"
            @retry="handleRetry"
          />
          <template v-else>
            <!-- Círculo de progreso -->
            <ProgressCircle :progress="numericProgress" />
            <h3 class="processing-title">{{ currentStepText }}</h3>
            <p class="processing-description">Por favor, espera mientras procesamos tu archivo</p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useMutation } from '@tanstack/vue-query';
import { z } from 'zod';
import { useTranslationStore } from '@/stores/translationStore';
import { uploadPdf, getTranslationStatus } from '@/api/pdfs';
import type { TranslationTask, TranslationConfig, LanguageModelType } from '@/types';
import { ApiRequestError, NetworkError, ErrorCode } from '@/types/api';
import FileUploader from './FileUploader.vue';
import ConfigurationPanel from './ConfigurationPanel.vue';
import LanguageSelect from './LanguageSelect.vue';
import ErrorBanner from './ErrorBanner.vue';
import ProgressCircle from './ProgressCircle.vue';

const router = useRouter();
const translationStore = useTranslationStore();

// Constantes y validación
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_MIME_TYPES = ['application/pdf'];
const schema = z.object({
  config: z.object({
    languageModel: z.custom<LanguageModelType>((val): val is LanguageModelType => 
      val === 'openai/gpt-4o-mini' || val === 'openai/gpt-5-mini' || val === 'deepseek/deepseek-chat-v3.1' || val === 'meta-llama/llama-3.3-70b-instruct', 
      { message: 'Por favor selecciona un modelo de lenguaje válido' }),
    confidence: z.number().min(0.1).max(0.9)
  }),
  file: z.custom<File>((file) => file instanceof File && ALLOWED_MIME_TYPES.includes(file.type) && file.size <= MAX_FILE_SIZE, { message: `Por favor selecciona un archivo PDF de menos de ${MAX_FILE_SIZE / 1024 / 1024}MB` }),
  targetLanguage: z.string().min(1, 'Por favor selecciona un idioma'),
});

// Estado del componente
const form = reactive({
  config: {
    languageModel: 'openai/gpt-4o-mini' as LanguageModelType,
    confidence: 0.45
  } as TranslationConfig,
  file: null as File | null,
  targetLanguage: 'es',
});

interface Errors {
  config: string;
  file: string;
  targetLanguage: string;
  general: string;
  code?: ErrorCode;
}
const errors = reactive<Errors>({ config: '', file: '', targetLanguage: '', general: '', code: undefined });

const isSubmitting = ref(false); // Para el estado de subida inicial
const pollingInterval = ref<number | null>(null);
const currentTask = ref<TranslationTask | null>(null);
const lastProgress = ref<number>(0);
const simulatedProgress = ref<number>(0);
const progressInterval = ref<number | null>(null);
const isNavigatingToResult = ref<boolean>(false);

// Propiedades computadas

// Determinar si está procesando
const isProcessing = computed(() => {
  if (!currentTask.value) return false;
  return currentTask.value.status === 'PENDING' || 
         currentTask.value.status === 'PROCESSING' || 
         isNavigatingToResult.value;
});

// Convertir paso a progreso numérico
const getStepProgress = (step: string | undefined): number => {
  const stepProgressMap: Record<string, number> = {
    'Iniciando traducción': 5,
    'Preparando documento': 10,
    'Analizando páginas': 25,
    'Traduciendo contenido': 45,
    'Finalizando documento': 85,
    'Procesando': 20
  };
  
  return stepProgressMap[step || 'Procesando'] || 20;
};

const numericProgress = computed(() => {
  if (!currentTask.value) return 0;
  
  let baseProgress: number;
  
  switch (currentTask.value.status) {
    case 'COMPLETED':
      baseProgress = 100;
      break;
    case 'PROCESSING':
      baseProgress = getStepProgress(currentTask.value.progress?.step);
      break;
    case 'PENDING':
      baseProgress = 5;
      break;
    case 'FAILED':
      baseProgress = 0;
      break;
    default:
      baseProgress = 0;
  }
  
  // Usar progreso simulado durante traducción
  if (currentTask.value.progress?.step === 'Traduciendo contenido' && simulatedProgress.value > baseProgress) {
    baseProgress = Math.min(simulatedProgress.value, 75); // Máximo 75% en simulación
  }
  
  // Prevenir retroceso del progreso
  if (baseProgress < lastProgress.value && baseProgress !== 0 && baseProgress !== 100) {
    baseProgress = Math.max(baseProgress, lastProgress.value);
  }
  
  lastProgress.value = baseProgress;
  return baseProgress;
});

const currentStepText = computed(() => {
  console.log('currentStepText computed:', {
    status: currentTask.value?.status,
    isNavigatingToResult: isNavigatingToResult.value,
    step: currentTask.value?.progress?.step
  });
  
  if (currentTask.value?.status === 'COMPLETED' || isNavigatingToResult.value) {
    return 'Traducción completada';
  }
  return currentTask.value?.progress?.step || 'Iniciando proceso';
});


const showRetryButton = computed(() => {
  return errors.code === ErrorCode.NETWORK_ERROR || 
         errors.code === ErrorCode.TIMEOUT || 
         errors.code === ErrorCode.SERVER_ERROR ||
         errors.code === ErrorCode.TRANSLATION_FAILED || 
         errors.code === ErrorCode.LANGUAGE_NOT_SUPPORTED || 
         errors.code === ErrorCode.OCR_FAILED;
});

// Limpieza al desmontar
onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }
  stopProgressSimulation();
});

// Funciones principales

const validate = (): boolean => {
  errors.config = ''; errors.file = ''; errors.targetLanguage = ''; errors.general = ''; errors.code = undefined;
  const result = schema.safeParse(form);
  if (!result.success) {
    result.error.errors.forEach((error) => {
      const path = error.path[0] as keyof typeof errors;
      if (path === 'config' || path === 'file' || path === 'targetLanguage') {
        errors[path] = error.message;
      }
    });
    return false;
  }
  return true;
};

// Mutación de subida
const mutation = useMutation({
  mutationFn: (formData: FormData) => uploadPdf(formData),
  onSuccess: (data) => {
    startPolling(data.taskId);
  },
  onError: (error: Error) => {
    handleApiError(error);
  },
});

const startProgressSimulation = (step: string) => {
  if (step !== 'Traduciendo contenido') return;
  
  if (progressInterval.value) clearInterval(progressInterval.value);
  
  simulatedProgress.value = 45;  // Valor inicial
  progressInterval.value = window.setInterval(() => {
    if (simulatedProgress.value < 75) {
      simulatedProgress.value += Math.random() * 2;
    }
  }, 1500);
};

const stopProgressSimulation = () => {
  if (progressInterval.value) {
    clearInterval(progressInterval.value);
    progressInterval.value = null;
  }
};

const startPolling = (taskId: string) => {
  if (pollingInterval.value) clearInterval(pollingInterval.value);

  pollingInterval.value = window.setInterval(async () => {
    try {
      const taskStatus = await getTranslationStatus(taskId);
      const previousStep = currentTask.value?.progress?.step;
      currentTask.value = taskStatus;
      translationStore.setCurrentTask(taskStatus);

      // Controlar progreso simulado
      if (taskStatus.progress?.step === 'Traduciendo contenido' && previousStep !== 'Traduciendo contenido') {
        startProgressSimulation('Traduciendo contenido');
      } else if (taskStatus.progress?.step !== 'Traduciendo contenido') {
        stopProgressSimulation();
      }

      if (taskStatus.status === 'COMPLETED') {
        stopProgressSimulation();
        clearInterval(pollingInterval.value!);
        isNavigatingToResult.value = true;
        
        // Esperar antes de navegar
        setTimeout(() => {
          router.push('/result');
        }, 1500);
      } else if (taskStatus.status === 'FAILED') {
        stopProgressSimulation();
        clearInterval(pollingInterval.value!);
        errors.general = taskStatus.error || 'Error en la traducción';
        errors.code = ErrorCode.TRANSLATION_FAILED;
      }
    } catch (error) {
      handleApiError(error as Error, 'Error al consultar el estado de la traducción');
      stopProgressSimulation();
      clearInterval(pollingInterval.value!);
    }
  }, 2000);
};

const handleApiError = (error: Error, defaultMessage = 'Error inesperado. Por favor, intenta de nuevo.') => {
  if (error instanceof ApiRequestError) {
    errors.general = error.getUserMessage();
    errors.code = error.error?.code || error.errorCode;
  } else if (error instanceof NetworkError) {
    errors.general = error.message;
    errors.code = ErrorCode.NETWORK_ERROR;
  } else {
    errors.general = defaultMessage;
    errors.code = ErrorCode.UNKNOWN_ERROR;
  }
  console.error('API Error:', error);
};

const handleRetry = () => {
  errors.general = '';
  errors.code = undefined;
  handleSubmit();
};

const handleSubmit = async () => {
  if (!validate()) return;
  
  // Reiniciar estado
  currentTask.value = null;
  translationStore.clearCurrentTask();
  lastProgress.value = 0;
  simulatedProgress.value = 0;
  errors.general = '';
  errors.code = undefined;
  isNavigatingToResult.value = false;
  
  // Limpiar intervalos previos
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
  stopProgressSimulation();
  
  isSubmitting.value = true;
  
  const formData = new FormData();
  formData.append('file', form.file!);
  formData.append('tgtLang', form.targetLanguage);
  formData.append('languageModel', form.config.languageModel);
  formData.append('confidence', form.config.confidence.toString());
  
  await mutation.mutateAsync(formData);
  isSubmitting.value = false;
};
</script>

<style scoped>
/* Estilos del componente */
.upload-container { max-width: 1000px; margin: 1rem auto; padding: 0 1rem; animation: slideUp 0.5s ease-out; }
.upload-card { background: white; border-radius: 16px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 10px 15px rgba(0, 0, 0, 0.1); border: 1px solid rgba(0, 0, 0, 0.1); padding: 1.5rem; transition: all 0.3s ease; position: relative; overflow: hidden; }
.is-processing { /* Puedes usar esta clase si quieres cambiar el estilo del card durante el proceso */ }
.card-header { text-align: center; margin-bottom: 1.5rem; }
.title { font-size: 2rem; margin: 0 0 0.75rem 0; color: #1a1b1e; font-weight: 800; background: linear-gradient(45deg, #228be6, #15aabf); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -0.02em; }
.subtitle { color: #868e96; font-size: 1.125rem; font-weight: 500; letter-spacing: -0.01em; }
.form-section { margin-bottom: 1.25rem; }
.submit-button { width: 100%; padding: 1rem; margin-top: 1rem; background: linear-gradient(45deg, #228be6, #15aabf); color: white; border: none; border-radius: 12px; font-weight: 600; font-size: 1rem; cursor: pointer; transition: all 0.2s ease; position: relative; overflow: hidden; }
.button-content { display: flex; align-items: center; justify-content: center; gap: 0.75rem; }
.submit-button:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(34, 139, 230, 0.25); }
.submit-button:active:not(:disabled) { transform: translateY(1px); }
.submit-button:disabled { background: linear-gradient(45deg, #74c0fc, #66d9e8); cursor: not-allowed; transform: none; box-shadow: none; }
.spinner { animation: spin 1s linear infinite; }
.processing-overlay { position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: rgba(255, 255, 255, 0.95); display: flex; align-items: center; justify-content: center; animation: fadeIn 0.3s ease; }
.processing-content { text-align: center; padding: 2rem; width: 100%; max-width: 500px; }
.processing-title { font-size: 1.25rem; font-weight: 600; color: #1a1b1e; margin-bottom: 0.5rem; }
.processing-description { color: #868e96; font-size: 0.9375rem; }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@media (max-width: 640px) { .upload-container { margin: 0.5rem auto; padding: 0 0.5rem; } .upload-card { padding: 1rem; border-radius: 12px; } .title { font-size: 1.5rem; } .subtitle { font-size: 1rem; } }
</style>