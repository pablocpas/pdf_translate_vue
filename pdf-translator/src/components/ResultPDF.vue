<template>
  <div class="result-container">
    <div v-if="showEditor" class="editor-view">
      <TranslationEditor :task-id="currentTask?.id" />
      <button class="back-button" @click="showEditor = false">
        Volver a la Vista PDF
      </button>
    </div>
    <div v-else class="result-view">
    <div class="result-card">
      <h2 class="title">Resultado de la traducción</h2>

      <!-- Estado de procesamiento -->
      <div v-if="isProcessing" class="PROCESSING-status">
        <div class="spinner"></div>
        <p class="status-text">Procesando documento...</p>
        <p class="status-detail">{{ currentTask?.progress?.step || 'Iniciando proceso...' }}</p>
        <p v-if="currentTask?.progress?.details" class="status-detail">{{ currentTask.progress.details }}</p>
      </div>

      <!-- Resultado -->
      <div v-if="isCompleted" class="result-grid">
        <div class="pdf-section">
          <h3 class="subtitle">PDF Original</h3>
          <div class="pdf-viewer">
            <iframe
              :src="originalPdfUrl"
              width="100%"
              height="800"
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
              height="800"
              frameborder="0"
              title="PDF Traducido"
            ></iframe>
          </div>
          <div class="pdf-actions">
            <a
              :href="translatedPdfUrl"
              download
              class="download-button download-button-primary"
            >
              Descargar Traducción
            </a>
            <button
              class="edit-button"
              @click="showEditor = true"
            >
              Editar Traducción
            </button>
          </div>
        </div>
      </div>

      <button
        class="new-translation-button"
        @click="router.push('/')"
      >
        Traducir otro PDF
      </button>
    </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import TranslationEditor from './TranslationEditor.vue';
import { useRouter } from 'vue-router';
import { useTranslationStore } from '@/stores/translationStore';
import { getTranslationStatus } from '@/api/pdfs';

const router = useRouter();
const showEditor = ref(false);
const translationStore = useTranslationStore();
const currentTask = computed(() => translationStore.currentTask);
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
  currentTask.value?.status === 'PENDING' || 
  currentTask.value?.status === 'PROCESSING'
);

const isCompleted = computed(() => 
  currentTask.value?.status === 'COMPLETED'
);

async function checkStatus() {
  if (!currentTask.value?.id) {
    router.push('/');
    return;
  }

  try {
    const task = await getTranslationStatus(currentTask.value.id);
    translationStore.setCurrentTask(task);

    if (task.status === 'FAILED' || task.status === 'COMPLETED') {
      clearInterval(checkInterval.value);
    }
  } catch (e) {
    console.error('Error al verificar estado:', e);
    clearInterval(checkInterval.value);
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
  max-width: 1800px;
  margin: 1rem auto;
  padding: 0 1rem;
  animation: fadeIn 0.5s ease-out;
  min-height: calc(100vh - 2rem);
}

.result-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05), 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(0, 0, 0, 0.1);
  padding: 1.5rem;
  height: 100%;
  display: flex;
  flex-direction: column;
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

.PROCESSING-status {
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
  gap: 1.5rem;
  margin: 1.5rem 0;
  flex: 1;
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
  padding: 1rem;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  height: 100%;
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

.pdf-actions {
  display: flex;
  gap: 1rem;
}

.edit-button {
  display: block;
  width: 100%;
  padding: 0.875rem;
  background: white;
  color: #228be6;
  border: 2px solid #228be6;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  text-decoration: none;
  text-align: center;
}

.edit-button:hover {
  background: rgba(34, 139, 230, 0.1);
  transform: translateY(-1px);
}

.back-button {
  display: block;
  width: 100%;
  padding: 0.875rem;
  margin-top: 1rem;
  background: #f8f9fa;
  color: #1a1b1e;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.back-button:hover {
  background: #e9ecef;
  transform: translateY(-1px);
}

.editor-view {
  animation: fadeIn 0.3s ease-out;
}

.result-view {
  animation: fadeIn 0.3s ease-out;
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
</style>
