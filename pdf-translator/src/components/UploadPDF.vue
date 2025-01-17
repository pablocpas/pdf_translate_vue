<template>
  <div class="upload-container">
    <div class="upload-card">
      <h2 class="title">Traductor de PDF</h2>
      
      <div v-if="errors.general" class="error-banner">
        {{ errors.general }}
      </div>

      <form @submit.prevent="handleSubmit">
        <FileUploader
          v-model="form.file"
          :error="errors.file"
        />

        <LanguageSelect
          v-model="form.targetLanguage"
          :error="errors.targetLanguage"
        />

        <button
          type="submit"
          class="submit-button"
          :disabled="isSubmitting || translationProgress > 0"
        >
          <span v-if="isSubmitting">Subiendo archivo...</span>
          <span v-else-if="translationProgress > 0">Traduciendo...</span>
          <span v-else>Traducir PDF</span>
        </button>
      </form>
    </div>
  </div>

  <ProgressBar
    :show="isSubmitting || translationProgress > 0"
    title="Procesando documento"
    :upload-progress="isSubmitting ? uploadProgress : null"
    :translation-progress="translationProgress > 0 ? translationProgress : null"
    :error="errors.general"
    :closeable="false"
    @close="() => {}"
  />
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useMutation, useQueryClient } from '@tanstack/vue-query';
import { z } from 'zod';
import { useAuthStore } from '@/stores/authStore';
import { useTranslationStore } from '@/stores/translationStore';
import { uploadPdf, getTranslationStatus } from '@/api/pdfs';
import { ApiRequestError, NetworkError } from '@/types/api';
import FileUploader from './FileUploader.vue';
import LanguageSelect from './LanguageSelect.vue';
import ProgressBar from './ProgressBar.vue';

const router = useRouter();
const authStore = useAuthStore();
const translationStore = useTranslationStore();
const queryClient = useQueryClient();

// Constantes
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ['application/pdf'];

// Esquema de validación
const schema = z.object({
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
  file: null as File | null,
  targetLanguage: '',
});

const errors = reactive({
  file: '',
  targetLanguage: '',
  general: '',
});

const uploadProgress = ref(0);
const translationProgress = ref(0);
const isSubmitting = ref(false);
const pollingInterval = ref<number | null>(null);

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
      originalFile: form.file!.name
    });
    return response;
  },
  onSuccess: async (data) => {
    // Iniciar polling para el progreso
    pollingInterval.value = window.setInterval(async () => {
      try {
        const taskStatus = await getTranslationStatus(data.taskId);
        console.log('Task status:', taskStatus); // Debug log
        
        // Actualizar el progreso solo si estamos en estado processing
        if (taskStatus.status === 'processing' && taskStatus.progress) {
          translationProgress.value = taskStatus.progress.percent || 0;
          console.log('Updated progress:', translationProgress.value); // Debug log
        }
        
        // Actualizar el store primero para mantener el estado sincronizado
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
    // Asegurarnos de que el archivo se envía con el tipo correcto
    const file = new File([form.file!], form.file!.name, {
      type: 'application/pdf'
    });
    formData.append('file', file);
    formData.append('target_language', form.targetLanguage);
    await mutation.mutateAsync(formData);
  } finally {
    isSubmitting.value = false;
  }
};
</script>

<style scoped>
.upload-container {
  max-width: 600px;
  margin: 2rem auto;
  padding: 0 1rem;
  animation: slideUp 0.5s ease-out;
}

.upload-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.upload-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 8px rgba(0, 0, 0, 0.05), 0 2px 4px rgba(0, 0, 0, 0.1);
}

.title {
  font-size: 1.625rem;
  margin: 0 0 2rem 0;
  color: #1a1b1e;
  font-weight: 700;
  text-align: center;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
}

.error-banner {
  background-color: #fff5f5;
  border: 2px solid #ffc9c9;
  border-radius: 8px;
  color: #e03131;
  padding: 1rem 1.25rem;
  margin-bottom: 2rem;
  font-size: 0.95rem;
  animation: shake 0.5s ease-in-out;
}

.submit-button {
  width: 100%;
  padding: 0.875rem;
  background: linear-gradient(45deg, #228be6, #15aabf);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.9375rem;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
  letter-spacing: -0.01em;
}

.submit-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25);
}

.submit-button:active {
  transform: translateY(1px);
}

.submit-button:disabled {
  background: linear-gradient(45deg, #74c0fc, #66d9e8);
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
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
</style>
