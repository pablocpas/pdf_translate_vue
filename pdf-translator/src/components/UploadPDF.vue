<template>
  <div class="upload-container">
    <!-- El :class ahora es más simple -->
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

        <ModelSelect
          v-model="form.model"
          :error="errors.model"
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
            <!-- Icono de spinner/subida -->
            <svg v-if="!isProcessing" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <svg v-else class="spinner" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="2" x2="12" y2="6"></line><line x1="12" y1="18" x2="12" y2="22"></line><line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line><line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line><line x1="2" y1="12" x2="6" y2="12"></line><line x1="18" y1="12" x2="22" y2="12"></line><line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line><line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
            </svg>
            
            <!-- Texto dinámico del botón -->
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
            <!-- El círculo de progreso ahora usa 'numericProgress' -->
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
import { ModelType, type TranslationTask } from '@/types';
import { ApiRequestError, NetworkError, ErrorCode } from '@/types/api';
import FileUploader from './FileUploader.vue';
import ModelSelect from './ModelSelect.vue';
import LanguageSelect from './LanguageSelect.vue';
import ErrorBanner from './ErrorBanner.vue';
import ProgressCircle from './ProgressCircle.vue';

const router = useRouter();
const translationStore = useTranslationStore();

// --- Constantes y Esquemas (sin cambios) ---
const MAX_FILE_SIZE = 10 * 1024 * 1024;
const ALLOWED_MIME_TYPES = ['application/pdf'];
const schema = z.object({
  model: z.custom<ModelType>((val): val is ModelType => val === 'primalayout' || val === 'publaynet', { message: 'Por favor selecciona un modelo válido' }),
  file: z.custom<File>((file) => file instanceof File && ALLOWED_MIME_TYPES.includes(file.type) && file.size <= MAX_FILE_SIZE, { message: `Por favor selecciona un archivo PDF de menos de ${MAX_FILE_SIZE / 1024 / 1024}MB` }),
  targetLanguage: z.string().min(1, 'Por favor selecciona un idioma'),
});

// --- Estado del Componente ---
const form = reactive({
  model: translationStore.selectedModel as ModelType,
  file: null as File | null,
  targetLanguage: 'es',
});

interface Errors {
  model: string;
  file: string;
  targetLanguage: string;
  general: string;
  code?: ErrorCode;
}
const errors = reactive<Errors>({ model: '', file: '', targetLanguage: '', general: '', code: undefined });

const isSubmitting = ref(false); // Para el estado de subida inicial
const pollingInterval = ref<number | null>(null);
const currentTask = ref<TranslationTask | null>(null);

// --- Computed Properties ---

// `isProcessing` ahora se basa en el estado de la tarea actual
const isProcessing = computed(() => {
  if (!currentTask.value) return false;
  return currentTask.value.status === 'PENDING' || currentTask.value.status === 'PROCESSING';
});

// Convierte el `step` de texto en un valor numérico para la UI
const getStepProgress = (step: string | undefined): number => {
  console.log('Current step:', step); // Debug
  switch(step) {
    case 'En cola': return 10;
    case 'Convirtiendo PDF a imágenes': return 30;
    case 'Procesando páginas en paralelo': return 60;
    case 'Ensamblando PDF final': return 90;
    case 'Finalizando traducción...': return 95;
    case 'Procesando resultado...': return 85;
    case 'Desconocido': return 5;
    default: 
      console.log('Unknown step, using 15%:', step);
      return 15; // Estado inicial o desconocido
  }
};

const numericProgress = computed(() => {
  if (currentTask.value?.status === 'COMPLETED') return 100;
  if (currentTask.value?.status === 'PROCESSING') {
    return getStepProgress(currentTask.value.progress?.step);
  }
  if (currentTask.value?.status === 'PENDING') return 5;
  return 0;
});

const currentStepText = computed(() => {
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

// --- Limpieza ---
onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }
});

// --- Funciones y Lógica ---

const validate = (): boolean => {
  errors.model = ''; errors.file = ''; errors.targetLanguage = ''; errors.general = ''; errors.code = undefined;
  const result = schema.safeParse(form);
  if (!result.success) {
    result.error.errors.forEach((error) => {
      const path = error.path[0] as keyof typeof errors;
      if (path === 'model' || path === 'file' || path === 'targetLanguage') {
        errors[path] = error.message;
      }
    });
    return false;
  }
  return true;
};

// Mutación para subir el archivo
const mutation = useMutation({
  mutationFn: (formData: FormData) => uploadPdf(formData),
  onSuccess: (data) => {
    // ANTES: Se creaba una tarea local.
    // DESPUÉS: Se inicia el polling inmediatamente con el taskId.
    startPolling(data.taskId);
  },
  onError: (error: Error) => {
    handleApiError(error);
  },
});

const startPolling = (taskId: string) => {
  if (pollingInterval.value) clearInterval(pollingInterval.value);

  pollingInterval.value = window.setInterval(async () => {
    try {
      const taskStatus = await getTranslationStatus(taskId);
      console.log('Polling status:', taskStatus); // Debug
      currentTask.value = taskStatus; // Actualiza la tarea local
      translationStore.setCurrentTask(taskStatus); // Actualiza la store global

      if (taskStatus.status === 'COMPLETED') {
        console.log('Task completed, redirecting to result');
        clearInterval(pollingInterval.value!);
        router.push('/result');
      } else if (taskStatus.status === 'FAILED') {
        console.log('Task failed:', taskStatus.error);
        clearInterval(pollingInterval.value!);
        errors.general = taskStatus.error || 'Error en la traducción';
        errors.code = ErrorCode.TRANSLATION_FAILED;
      }
    } catch (error) {
      handleApiError(error as Error, 'Error al consultar el estado de la traducción');
      clearInterval(pollingInterval.value!);
    }
  }, 2000); // Polling cada 2 segundos
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
  
  // Limpiar estado anterior
  currentTask.value = null;
  translationStore.clearCurrentTask();
  errors.general = '';
  errors.code = undefined;
  
  // Limpiar cualquier polling previo
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
  
  isSubmitting.value = true;
  
  const formData = new FormData();
  formData.append('file', form.file!);
  formData.append('tgtLang', form.targetLanguage); // Corregir nombre parámetro
  formData.append('modelType', form.model); // Corregir nombre parámetro
  
  await mutation.mutateAsync(formData);

  isSubmitting.value = false;
};
</script>

<style scoped>
/* Tu CSS existente aquí (sin cambios) */
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