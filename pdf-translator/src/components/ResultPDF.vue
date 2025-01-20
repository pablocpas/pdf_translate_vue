<template>
  <div class="result-container">
    <div class="result-card">
      <h2 class="title">Resultado de la traducción</h2>

      <!-- Error general -->
      <div v-if="error" class="error-banner">
        {{ error }}
        <button class="retry-button" @click="checkStatus" :disabled="isLoading">
          Reintentar
        </button>
      </div>

      <!-- Estado de procesamiento -->
      <div v-if="isProcessing" class="processing-status">
        <div class="spinner"></div>
        <p class="status-text">Traduciendo documento...</p>
        <p class="status-detail">{{ currentTask?.status }}</p>
      </div>

      <!-- Resultado -->
      <div v-if="isCompleted" class="result-grid">
        <div class="pdf-section">
          <h3 class="subtitle">PDF Original</h3>
          <div class="pdf-viewer">
            <iframe
              :src="originalPdfUrl"
              width="100%"
              height="600"
              frameborder="0"
              title="PDF Original"
            ></iframe>
          </div>
          <a
            :href="originalPdfUrl"
            download
            class="download-button download-button-secondary"
          >
            Descargar Original
          </a>
        </div>
        
        <div class="pdf-section">
          <h3 class="subtitle">PDF Traducido</h3>
          <div class="pdf-viewer">
            <iframe
              :src="translatedPdfUrl"
              width="100%"
              height="600"
              frameborder="0"
              title="PDF Traducido"
            ></iframe>
          </div>
          <a
            :href="translatedPdfUrl"
            download
            class="download-button download-button-primary"
          >
            Descargar Traducción
          </a>
        </div>
      </div>

      <button
        class="new-translation-button"
        @click="router.push('/')"
        :disabled="isLoading"
      >
        Traducir otro PDF
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useTranslationStore } from '@/stores/translationStore';
import { getTranslationStatus } from '@/api/pdfs';
import { ApiRequestError, NetworkError } from '@/types/api';

const router = useRouter();
const translationStore = useTranslationStore();
const currentTask = computed(() => translationStore.currentTask);

const error = ref<string>('');
const isLoading = ref(false);
const checkInterval = ref<number>();

const originalPdfUrl = computed(() => 
  currentTask.value?.id ? 
  `${import.meta.env.VITE_API_URL}/pdfs/download/original/${currentTask.value.id}` : 
  ''
);

const translatedPdfUrl = computed(() => 
  currentTask.value?.id ? 
  `${import.meta.env.VITE_API_URL}/pdfs/download/translated/${currentTask.value.id}` : 
  ''
);

const isProcessing = computed(() => 
  currentTask.value?.status === 'pending' || 
  currentTask.value?.status === 'processing'
);

const isCompleted = computed(() => 
  currentTask.value?.status === 'completed'
);

async function checkStatus() {
  if (!currentTask.value?.id) {
    error.value = 'No hay tarea de traducción activa';
    return;
  }

  isLoading.value = true;
  error.value = '';

  try {
    const task = await getTranslationStatus(currentTask.value.id);
    translationStore.setCurrentTask(task);

    if (task.status === 'failed') {
      error.value = task.error || 'Error en la traducción';
      clearInterval(checkInterval.value);
    } else if (task.status === 'completed') {
      clearInterval(checkInterval.value);
    }
  } catch (e) {
    if (e instanceof ApiRequestError) {
      error.value = e.message;
    } else if (e instanceof NetworkError) {
      error.value = 'Error de conexión. Por favor, intenta de nuevo.';
    } else {
      error.value = 'Error inesperado al verificar el estado.';
    }
    clearInterval(checkInterval.value);
  } finally {
    isLoading.value = false;
  }
}

onMounted(() => {
  if (!currentTask.value) {
    router.push('/');
    return;
  }

  checkStatus();
  
  if (isProcessing.value) {
    checkInterval.value = window.setInterval(checkStatus, 5000);
  }
});

onUnmounted(() => {
  if (checkInterval.value) {
    clearInterval(checkInterval.value);
  }
});
</script>

<style scoped>
.result-container {
  max-width: 1200px;
  margin: 2rem auto;
  padding: 0 1rem;
  animation: fadeIn 0.5s ease-out;
}

.result-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 2.5rem;
}

.title {
  font-size: 1.625rem;
  margin: 0 0 2rem 0;
  color: #1a1b1e;
  text-align: center;
  font-weight: 700;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 1.125rem;
  margin: 0 0 1.25rem 0;
  color: #1a1b1e;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.error-banner {
  background-color: #fff5f5;
  border: 2px solid #ffc9c9;
  border-radius: 8px;
  color: #e03131;
  padding: 1.25rem;
  margin-bottom: 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  animation: shake 0.5s ease-in-out;
}

.retry-button {
  background: transparent;
  border: 2px solid #e03131;
  color: #e03131;
  padding: 0.625rem 1.25rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background: rgba(224, 49, 49, 0.1);
  transform: translateY(-1px);
}

.retry-button:active {
  transform: translateY(1px);
}

.retry-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.processing-status {
  text-align: center;
  padding: 3rem 2rem;
  background: #f8f9fa;
  border-radius: 12px;
  margin: 2rem 0;
}

.spinner {
  border: 4px solid rgba(34, 139, 230, 0.1);
  border-top: 4px solid #228be6;
  border-radius: 50%;
  width: 50px;
  height: 50px;
  animation: spin 1s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.status-text {
  font-size: 1.375rem;
  color: #1a1b1e;
  margin: 0 0 0.75rem;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.status-detail {
  color: #495057;
  margin: 0;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.result-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2.5rem;
  margin: 2rem 0;
}

@media (min-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr 1fr;
  }
}

.pdf-section {
  display: flex;
  flex-direction: column;
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.pdf-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}

.pdf-viewer {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 1.25rem;
  flex-grow: 1;
  background: white;
}

.download-button {
  display: block;
  width: 100%;
  padding: 0.875rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  text-align: center;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.download-button-primary {
  background: linear-gradient(45deg, #228be6, #15aabf);
  color: white;
}

.download-button-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25);
}

.download-button-secondary {
  background: white;
  color: #228be6;
  border: 2px solid #228be6;
}

.download-button-secondary:hover {
  background: rgba(34, 139, 230, 0.1);
  transform: translateY(-1px);
}

.new-translation-button {
  display: block;
  width: 100%;
  padding: 0.875rem;
  margin-top: 2.5rem;
  background: #f8f9fa;
  color: #1a1b1e;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.new-translation-button:hover {
  background: #e9ecef;
  transform: translateY(-1px);
}

.new-translation-button:active {
  transform: translateY(1px);
}

.new-translation-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

@keyframes fadeIn {
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
