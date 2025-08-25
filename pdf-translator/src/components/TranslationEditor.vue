<template>
  <div class="editor-container">
    <div class="editor-grid">
      <!-- Panel Izquierdo: Editor de Textos -->
      <div class="editor-section">
        <h3 class="subtitle">Editor de Traducciones</h3>
        
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Cargando datos de traducción...</p>
        </div>
        
        <div v-else-if="translationPages.length === 0" class="empty-state">
          <p>No se encontraron datos de traducción</p>
        </div>
        
        <div v-else class="translations-container">
          <div 
            v-for="page in translationPages" 
            :key="page.page_number"
            class="page-group"
          >
            <h4 class="page-title">Página {{ page.page_number }}</h4>
            
            <div 
              v-for="translation in page.translations"
              :key="translation.id"
              class="translation-item"
            >
              <div class="original-text">
                <label class="text-label">Texto Original:</label>
                <div class="text-display">{{ translation.original_text }}</div>
              </div>
              
              <div class="translated-text">
                <label class="text-label" :for="`translation-${translation.id}`">
                  Texto Traducido:
                </label>
                <textarea
                  :id="`translation-${translation.id}`"
                  v-model="translation.translated_text"
                  class="text-input"
                  rows="3"
                  placeholder="Escriba la traducción aquí..."
                />
              </div>
            </div>
          </div>
          
          <div class="editor-actions">
            <button 
              class="save-button"
              :disabled="loading || saving"
              @click="saveChanges"
            >
              <span v-if="saving">Guardando...</span>
              <span v-else>Guardar Cambios</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Panel Derecho: Visor PDF -->
      <div class="preview-section">
        <h3 class="subtitle">Vista Previa del PDF</h3>
        <div class="pdf-viewer">
          <iframe
            :src="pdfPreviewUrl"
            width="100%"
            height="100%"
            frameborder="0"
            title="PDF Preview"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { getTranslationData, updateTranslationData } from '@/api/pdfs';
import type { TranslationData, PageTranslation } from '@/types/schemas';

// Props
interface Props {
  taskId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  taskId: undefined
});

// State
const loading = ref(true);
const saving = ref(false);
const translationPages = ref<PageTranslation[]>([]);
const pdfTimestamp = ref(Date.now());

// Computed
const pdfPreviewUrl = computed(() => {
  if (!props.taskId) return '';
  return `${import.meta.env.VITE_API_URL}/pdfs/download/translated/${props.taskId}?t=${pdfTimestamp.value}`;
});

// Methods
async function loadTranslationData() {
  if (!props.taskId) {
    console.warn('No taskId provided to TranslationEditor');
    loading.value = false;
    return;
  }
  
  loading.value = true;
  try {
    const data = await getTranslationData(props.taskId);
    translationPages.value = data.pages.map(page => ({
      page_number: page.page_number,
      translations: page.translations.map(translation => ({
        id: translation.id,
        original_text: translation.original_text,
        translated_text: translation.translated_text
      }))
    }));
  } catch (error) {
    console.error('Error loading translation data:', error);
    alert('Error al cargar los datos de traducción');
  } finally {
    loading.value = false;
  }
}

async function saveChanges() {
  if (!props.taskId || saving.value) return;
  
  saving.value = true;
  try {
    const translationData: TranslationData = {
      pages: translationPages.value
    };
    
    await updateTranslationData(props.taskId, translationData);
    
    // Update PDF timestamp to force refresh
    pdfTimestamp.value = Date.now();
    
    console.log('Translation data saved successfully');
  } catch (error) {
    console.error('Error saving translation data:', error);
    alert('Error al guardar los cambios');
  } finally {
    saving.value = false;
  }
}

// Watch for taskId changes and load data immediately when available
watch(() => props.taskId, (newTaskId, oldTaskId) => {
  if (newTaskId && newTaskId !== oldTaskId) {
    loadTranslationData();
  }
}, { immediate: true });

// Lifecycle - also try to load data on mount in case taskId is already available
onMounted(() => {
  if (props.taskId) {
    loadTranslationData();
  }
});
</script>

<style scoped>
.editor-container {
  padding: 1rem;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
}

.editor-section, .preview-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.subtitle {
  font-size: 1.125rem;
  margin: 0 0 1rem 0;
  color: #1a1b1e;
  font-weight: 600;
  flex-shrink: 0;
}

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #495057;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(34, 139, 230, 0.3);
  border-radius: 50%;
  border-top-color: #228be6;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.translations-container {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.page-group {
  margin-bottom: 2rem;
}

.page-title {
  font-size: 1rem;
  font-weight: 600;
  color: #228be6;
  margin: 0 0 1rem 0;
  padding: 0.5rem;
  background: rgba(34, 139, 230, 0.1);
  border-radius: 6px;
  border-left: 4px solid #228be6;
}

.translation-item {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #e9ecef;
  transition: box-shadow 0.2s ease;
}

.translation-item:hover {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.original-text, .translated-text {
  margin-bottom: 0.75rem;
}

.translated-text {
  margin-bottom: 0;
}

.text-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.25rem;
}

.text-display {
  background: #f8f9fa;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  line-height: 1.4;
  color: #495057;
  border: 1px solid #e9ecef;
  word-wrap: break-word;
}

.text-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  font-size: 0.875rem;
  line-height: 1.4;
  resize: vertical;
  min-height: 60px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.text-input:focus {
  outline: none;
  border-color: #228be6;
  box-shadow: 0 0 0 2px rgba(34, 139, 230, 0.1);
}

.pdf-viewer {
  flex: 1;
  border: 2px solid #e9ecef;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  min-height: 0;
}

.editor-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
  flex-shrink: 0;
}

.save-button {
  width: 100%;
  padding: 0.875rem;
  background: linear-gradient(45deg, #228be6, #15aabf);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
}

.save-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

/* Responsive Design */
@media (max-width: 1024px) {
  .editor-grid {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
  
  .editor-container {
    height: calc(100vh - 60px);
  }
}

@media (max-width: 768px) {
  .editor-container {
    padding: 0.5rem;
  }
  
  .editor-section, .preview-section {
    padding: 0.75rem;
  }
  
  .translation-item {
    padding: 0.75rem;
  }
}
</style>