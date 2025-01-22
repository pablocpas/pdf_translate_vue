<template>
  <div class="upload-container">
    <div class="upload-card" :class="{ 'is-processing': isProcessing }">
      <div class="card-header">
        <h2 class="title">Traductor de PDF</h2>
        <p class="subtitle">Traduce documentos PDF a múltiples idiomas</p>
      </div>
      
      <div v-if="errors.general" class="error-banner">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        {{ errors.general }}
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
          :disabled="isSubmitting || translationProgress >= 0"
        >
          <div class="button-content">
            <svg v-if="!isProcessing" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <svg v-else class="spinner" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="2" x2="12" y2="6"></line>
              <line x1="12" y1="18" x2="12" y2="22"></line>
              <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
              <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
              <line x1="2" y1="12" x2="6" y2="12"></line>
              <line x1="18" y1="12" x2="22" y2="12"></line>
              <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
              <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
            </svg>
            <span v-if="isSubmitting">Subiendo archivo...</span>
            <span v-else-if="translationProgress >= 0">Traduciendo ({{ Math.round(translationProgress) }}%)...</span>
            <span v-else>Traducir PDF</span>
          </div>
        </button>
      </form>

      <div class="processing-overlay" v-if="isProcessing">
        <div class="processing-content">
          <div class="progress-circle">
            <svg class="progress" viewBox="0 0 100 100">
              <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stop-color="#228be6" />
                  <stop offset="100%" stop-color="#15aabf" />
                </linearGradient>
              </defs>
              <circle class="progress-background" cx="50" cy="50" r="45"></circle>
              <circle 
                class="progress-bar" 
                cx="50" 
                cy="50" 
                r="45"
                :style="{
                  strokeDashoffset: `${((100 - translationProgress) / 100) * 283}px`
                }"
              ></circle>
            </svg>
            <span class="progress-text">{{ Math.round(translationProgress) }}%</span>
          </div>
          <h3 class="processing-title">Traduciendo documento</h3>
          <p class="processing-description">Por favor, espera mientras procesamos tu archivo</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { z } from 'zod';
import { useAuthStore } from '@/stores/authStore';
import { useTranslationStore } from '@/stores/translationStore';
import { uploadPdf, getTranslationStatus } from '@/api/pdfs';
import { ApiRequestError, NetworkError } from '@/types/api';
import FileUploader from './FileUploader.vue';
import ModelSelect from './ModelSelect.vue';
import LanguageSelect from './LanguageSelect.vue';

const router = useRouter();
const authStore = useAuthStore();
const translationStore = useTranslationStore();
const queryClient = useQueryClient();

// Constantes
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ['application/pdf'];

// Esquema de validación
const schema = z.object({
  model: z.string().min(1, 'Por favor selecciona un modelo'),
  file: z.custom<File>(
    (file) => file instanceof File && 
              ALLOWED_MIME_TYPES.includes(file.type) &&
              file.size <= MAX_FILE_SIZE,
    {
      message: `Por favor selecciona un archivo PDF de menos de ${MAX_FILE_SIZE / 1024 / 1024}MB`
    }
  ),
  targetLanguage: z.string().min(1, 'Por favor selecciona un idioma'),
});

// Estado del formulario
const form = reactive({
  model: translationStore.selectedModel,
  file: null as File | null,
  targetLanguage: 'es',
});

const errors = reactive({
  model: '',
  file: '',
  targetLanguage: '',
  general: '',
});

const uploadProgress = ref(0);
const translationProgress = ref(-1);
const isSubmitting = ref(false);
const pollingInterval = ref<number | null>(null);

const isProcessing = computed(() => {
  return isSubmitting.value || translationProgress.value >= 0;
});

// Cleanup al desmontar
onUnmounted(() => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
  }
});

const validate = () => {
  // Limpiar errores previos
  Object.keys(errors).forEach(key => {
    errors[key as keyof typeof errors] = '';
  });
  
  const result = schema.safeParse(form);
  if (!result.success) {
    result.error.errors.forEach((error) => {
      const path = error.path[0] as keyof typeof errors;
      errors[path] = error.message;
    });
    return false;
  }
  return true;
};

// Mutación para subir archivo
const mutation = useMutation({
  mutationFn: async (formData: FormData) => {
    const response = await uploadPdf(formData);
    translationStore.setCurrentTask({
      id: response.taskId,
      status: 'pending',
      originalFile: form.file!.name,
      progress: null,
      error: null,
      translatedFile: null
    });
    return response;
  },
  onSuccess: async (data) => {
    // Iniciar polling para el progreso
    pollingInterval.value = window.setInterval(async () => {
      try {
        const taskStatus = await getTranslationStatus(data.taskId);
        
        if(taskStatus.status === 'pending') {
          translationProgress.value = 0;
        }
        
        if (taskStatus.status === 'processing' && taskStatus.progress) {
          translationProgress.value = taskStatus.progress.percent || 0;
        }
        
        translationStore.setCurrentTask(taskStatus);
        
        if (taskStatus.status === 'completed') {
          clearInterval(pollingInterval.value!);
          router.push('/result');
        } else if (taskStatus.status === 'failed') {
          clearInterval(pollingInterval.value!);
          errors.general = taskStatus.error || 'Error en la traducción';
        }
      } catch (error) {
        console.error('Error al consultar estado:', error);
      }
    }, 1000);
  },
  onError: (error: Error) => {
    if (error instanceof ApiRequestError) {
      errors.general = `Error: ${error.message}`;
    } else if (error instanceof NetworkError) {
      errors.general = 'Error de conexión. Por favor, intenta de nuevo.';
    } else {
      errors.general = 'Error inesperado. Por favor, intenta de nuevo.';
    }
    console.error('Error al subir archivo:', error);
  },
});

const handleSubmit = async () => {
  if (!validate()) return;
  
  isSubmitting.value = true;
  uploadProgress.value = 0;
  translationProgress.value = 0;
  errors.general = '';
  
  try {
    const formData = new FormData();
    const file = new File([form.file!], form.file!.name, {
      type: 'application/pdf'
    });
    formData.append('file', file);
    formData.append('target_language', form.targetLanguage);
    formData.append('model', form.model);
    await mutation.mutateAsync(formData);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.upload-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 0 1.5rem;
  animation: slideUp 0.5s ease-out;
}

.upload-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 
              0 10px 15px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.card-header {
  text-align: center;
  margin-bottom: 2.5rem;
}

.title {
  font-size: 2rem;
  margin: 0 0 0.75rem 0;
  color: #1a1b1e;
  font-weight: 800;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
}

.subtitle {
  color: #868e96;
  font-size: 1.125rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.error-banner {
  background-color: #fff5f5;
  border: 2px solid #ffc9c9;
  border-radius: 12px;
  color: #e03131;
  padding: 1rem 1.25rem;
  margin-bottom: 2rem;
  font-size: 0.95rem;
  animation: shake 0.5s ease-in-out;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.form-section {
  margin-bottom: 1.75rem;
}

.submit-button {
  width: 100%;
  padding: 1rem;
  margin-top: 1rem;
  background: linear-gradient(45deg, #228be6, #15aabf);
  color: white;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.button-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
}

.submit-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(34, 139, 230, 0.25);
}

.submit-button:active {
  transform: translateY(1px);
}

.submit-button:disabled {
  background: linear-gradient(45deg, #74c0fc, #66d9e8);
  cursor: not-allowed;
  transform: none;
}

.spinner {
  animation: spin 1s linear infinite;
}

.processing-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.3s ease;
}

.processing-content {
  text-align: center;
  padding: 2rem;
}

.progress-circle {
  position: relative;
  width: 120px;
  height: 120px;
  margin: 0 auto 1.5rem;
}

.progress {
  transform: rotate(-90deg);
  width: 100%;
  height: 100%;
}

.progress-background {
  fill: none;
  stroke: #e9ecef;
  stroke-width: 8;
}

.progress-bar {
  fill: none;
  stroke: url(#gradient);
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.3s ease;
}

.progress-text {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1.5rem;
  font-weight: 700;
  color: #228be6;
}

.processing-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a1b1e;
  margin-bottom: 0.5rem;
}

.processing-description {
  color: #868e96;
  font-size: 0.9375rem;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@media (max-width: 640px) {
  .upload-container {
    margin: 1rem auto;
    padding: 0 1rem;
  }

  .upload-card {
    padding: 1.5rem;
    border-radius: 12px;
  }

  .title {
    font-size: 1.5rem;
  }

  .subtitle {
    font-size: 1rem;
  }
}
</style>
