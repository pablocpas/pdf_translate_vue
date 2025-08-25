<template>
  <div class="editor-container">
    <!-- Header con información y acciones -->
    <div class="editor-header">
      <div class="header-info">
        <h2 class="editor-title">Editor de Traducciones</h2>
        <div class="translation-stats">
          <span class="stats-item">
            <strong>{{ totalPages }}</strong> páginas
          </span>
          <span class="stats-item">
            <strong>{{ totalTranslations }}</strong> traducciones
          </span>
          <span class="stats-item" v-if="hasChanges">
            <span class="changes-indicator">•</span> Cambios sin guardar
          </span>
        </div>
      </div>
      <div class="header-actions">
        <button 
          class="save-button"
          :disabled="loading || saving || !hasChanges"
          @click="saveChanges"
          :class="{ 'has-changes': hasChanges }"
        >
          <span class="button-icon">💾</span>
          <span v-if="saving">Guardando...</span>
          <span v-else>Guardar Cambios</span>
        </button>
      </div>
    </div>

    <div class="editor-grid">
      <!-- Panel Izquierdo: Editor de Textos -->
      <div class="editor-section">
        <div class="section-header">
          <h3 class="section-title">Textos Editables</h3>
          <div class="page-navigation" v-if="translationPages.length > 1">
            <button 
              v-for="page in translationPages"
              :key="page.page_number"
              :class="['page-nav-btn', { active: currentPage === page.page_number }]"
              @click="scrollToPage(page.page_number)"
            >
              {{ page.page_number }}
            </button>
          </div>
        </div>
        
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Cargando datos de traducción...</p>
        </div>
        
        <div v-else-if="translationPages.length === 0" class="empty-state">
          <div class="empty-icon">📄</div>
          <h3>No se encontraron traducciones</h3>
          <p>No hay datos de traducción disponibles para editar.</p>
        </div>
        
        <div v-else class="translations-container" @scroll="handleScroll">
          <div 
            v-for="page in translationPages" 
            :key="page.page_number"
            :data-page="page.page_number"
            class="page-group"
          >
            <div class="page-header">
              <h4 class="page-title">
                <span class="page-number">Página {{ page.page_number }}</span>
                <span class="translation-count">{{ page.translations.length }} elementos</span>
              </h4>
            </div>
            
            <div class="page-translations">
              <div 
                v-for="(translation, index) in page.translations"
                :key="translation.id"
                class="translation-item"
                :class="{ 'translation-modified': isModified(translation) }"
              >
                <div class="translation-number">{{ index + 1 }}</div>
                
                <div class="translation-content">
                  <div class="original-text">
                    <label class="text-label">
                      <span class="label-icon">📖</span>
                      Texto Original
                    </label>
                    <div class="text-display" :style="{ minHeight: getTextHeight(translation.original_text) }">
                      {{ translation.original_text }}
                    </div>
                  </div>
                  
                  <div class="translated-text">
                    <label class="text-label" :for="`translation-${translation.id}`">
                      <span class="label-icon">✏️</span>
                      Texto Traducido
                    </label>
                    <textarea
                      :id="`translation-${translation.id}`"
                      v-model="translation.translated_text"
                      class="text-input auto-resize"
                      placeholder="Escriba la traducción aquí..."
                      @input="onTextChange(translation)"
                      @focus="onTextFocus"
                      @blur="onTextBlur"
                      :style="{ minHeight: getTextHeight(translation.translated_text || translation.original_text) }"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Panel Derecho: Visor PDF -->
      <div class="preview-section">
        <div class="section-header">
          <h3 class="section-title">Vista Previa</h3>
          <div class="pdf-controls">
            <button 
              class="control-btn"
              @click="refreshPdf"
              title="Actualizar vista previa"
              :disabled="saving"
            >
              🔄
            </button>
          </div>
        </div>
        
        <div class="pdf-viewer">
          <div v-if="saving" class="pdf-loading-overlay">
            <div class="loading-spinner"></div>
            <p>Regenerando PDF...</p>
          </div>
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
import { ref, computed, onMounted, watch, nextTick } from 'vue';
import { getTranslationData, updateTranslationData } from '@/api/pdfs';
import type { TranslationData, PageTranslation, TranslationText } from '@/types/schemas';

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
const originalPages = ref<PageTranslation[]>([]);
const pdfTimestamp = ref(Date.now());
const currentPage = ref(1);

// Computed
const pdfPreviewUrl = computed(() => {
  if (!props.taskId) return '';
  return `${import.meta.env.VITE_API_URL}/pdfs/download/translated/${props.taskId}?t=${pdfTimestamp.value}`;
});

const totalPages = computed(() => translationPages.value.length);

const totalTranslations = computed(() => 
  translationPages.value.reduce((total, page) => total + page.translations.length, 0)
);

const hasChanges = computed(() => {
  return JSON.stringify(translationPages.value) !== JSON.stringify(originalPages.value);
});

// Methods
function getTextHeight(text: string): string {
  if (!text) return '40px';
  const lines = text.split('\n').length;
  const wordsPerLine = 80; // aproximadamente
  const estimatedLines = Math.max(lines, Math.ceil(text.length / wordsPerLine));
  return `${Math.max(40, estimatedLines * 24)}px`;
}

function isModified(translation: TranslationText): boolean {
  const original = originalPages.value
    .flatMap(page => page.translations)
    .find(t => t.id === translation.id);
  return original?.translated_text !== translation.translated_text;
}

function onTextChange(translation: TranslationText): void {
  // Auto-resize is handled by CSS and style binding
  nextTick(() => {
    // Optional: Add any additional logic after text change
  });
}

function onTextFocus(): void {
  // Could add focus effects here
}

function onTextBlur(): void {
  // Could add blur effects here
}

function scrollToPage(pageNumber: number): void {
  const pageElement = document.querySelector(`[data-page="${pageNumber}"]`);
  if (pageElement) {
    pageElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function handleScroll(event: Event): void {
  const container = event.target as HTMLElement;
  const pageElements = container.querySelectorAll('[data-page]');
  
  for (const element of Array.from(pageElements)) {
    const rect = element.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    
    if (rect.top <= containerRect.top + 100) {
      currentPage.value = parseInt(element.getAttribute('data-page') || '1');
    }
  }
}

function refreshPdf(): void {
  pdfTimestamp.value = Date.now();
}

async function loadTranslationData() {
  if (!props.taskId) {
    console.warn('No taskId provided to TranslationEditor');
    loading.value = false;
    return;
  }
  
  loading.value = true;
  try {
    const data = await getTranslationData(props.taskId);
    const mappedPages = data.pages.map(page => ({
      page_number: page.page_number,
      translations: page.translations.map(translation => ({
        id: translation.id,
        original_text: translation.original_text,
        translated_text: translation.translated_text
      }))
    }));
    
    translationPages.value = mappedPages;
    originalPages.value = JSON.parse(JSON.stringify(mappedPages)); // Deep copy
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
    
    // Update original data to reflect saved state
    originalPages.value = JSON.parse(JSON.stringify(translationPages.value));
    
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
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: #f7f9fc;
}

/* Header Styles */
.editor-header {
  background: white;
  padding: 1.5rem;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.editor-title {
  font-size: 1.5rem;
  margin: 0 0 0.5rem 0;
  color: #1a1b1e;
  font-weight: 700;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.translation-stats {
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
}

.stats-item {
  color: #6c757d;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.changes-indicator {
  color: #28a745;
  font-size: 1.2rem;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-actions {
  display: flex;
  gap: 1rem;
}

.save-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
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
  box-shadow: 0 6px 12px rgba(34, 139, 230, 0.3);
}

.save-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.save-button.has-changes {
  animation: glow 2s infinite;
}

@keyframes glow {
  0%, 100% { box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25); }
  50% { box-shadow: 0 6px 16px rgba(34, 139, 230, 0.4); }
}

.button-icon {
  font-size: 1rem;
}

/* Main Grid */
.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  flex: 1;
  min-height: 0;
  padding: 1.5rem;
}

/* Section Styles */
.editor-section, .preview-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  border: 1px solid #e9ecef;
}

.section-header {
  padding: 1rem 1.5rem 0.5rem 1.5rem;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.section-title {
  font-size: 1.125rem;
  margin: 0;
  color: #1a1b1e;
  font-weight: 600;
}

/* Page Navigation */
.page-navigation {
  display: flex;
  gap: 0.25rem;
}

.page-nav-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e9ecef;
  background: white;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6c757d;
}

.page-nav-btn:hover {
  background: #f8f9fa;
  border-color: #228be6;
}

.page-nav-btn.active {
  background: #228be6;
  color: white;
  border-color: #228be6;
}

/* PDF Controls */
.pdf-controls {
  display: flex;
  gap: 0.5rem;
}

.control-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #e9ecef;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.control-btn:hover:not(:disabled) {
  background: #f8f9fa;
  border-color: #228be6;
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Loading and Empty States */
.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: #6c757d;
  padding: 3rem 2rem;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 0.5rem 0;
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

/* Translations Container */
.translations-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.translations-container::-webkit-scrollbar {
  width: 6px;
}

.translations-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.translations-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.translations-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* Page Groups */
.page-group {
  margin-bottom: 2rem;
}

.page-header {
  margin-bottom: 1rem;
}

.page-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 1.125rem;
  font-weight: 600;
  color: #228be6;
  margin: 0;
  padding: 1rem;
  background: rgba(34, 139, 230, 0.08);
  border-radius: 8px;
  border-left: 4px solid #228be6;
}

.page-number {
  font-weight: 700;
}

.translation-count {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6c757d;
  background: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
}

/* Translation Items */
.page-translations {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.translation-item {
  background: #fafbfc;
  border-radius: 12px;
  border: 2px solid #f0f0f0;
  transition: all 0.2s ease;
  display: flex;
  gap: 1rem;
  position: relative;
  overflow: hidden;
}

.translation-item:hover {
  border-color: #e3f2fd;
  box-shadow: 0 2px 8px rgba(34, 139, 230, 0.1);
}

.translation-item.translation-modified {
  border-color: #28a745;
  background: #f8fff9;
}

.translation-item.translation-modified::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: #28a745;
}

.translation-number {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  background: #228be6;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
  font-weight: 600;
  margin: 1rem 0 0 1rem;
}

.translation-content {
  flex: 1;
  padding: 1rem 1rem 1rem 0;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Text Areas */
.original-text, .translated-text {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.text-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
}

.label-icon {
  font-size: 1rem;
}

.text-display {
  background: white;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5;
  color: #495057;
  border: 1px solid #e9ecef;
  word-wrap: break-word;
  white-space: pre-wrap;
}

.text-input {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  font-size: 0.875rem;
  line-height: 1.5;
  resize: none;
  transition: all 0.2s ease;
  font-family: inherit;
  background: white;
}

.text-input:focus {
  outline: none;
  border-color: #228be6;
  box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.1);
}

.text-input::placeholder {
  color: #adb5bd;
  font-style: italic;
}

/* PDF Viewer */
.pdf-viewer {
  flex: 1;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  min-height: 0;
  margin: 1rem;
  border: 1px solid #e9ecef;
  position: relative;
}

.pdf-loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 10;
  backdrop-filter: blur(2px);
}

.pdf-loading-overlay .loading-spinner {
  width: 32px;
  height: 32px;
  border-width: 2px;
}

/* Responsive Design */
@media (max-width: 1200px) {
  .editor-grid {
    gap: 1rem;
    padding: 1rem;
  }
}

@media (max-width: 1024px) {
  .editor-grid {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
  
  .editor-container {
    height: calc(100vh - 60px);
  }
  
  .editor-header {
    padding: 1rem;
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .header-actions {
    justify-content: center;
  }
}

@media (max-width: 768px) {
  .editor-grid {
    padding: 0.5rem;
    gap: 0.5rem;
  }
  
  .section-header {
    padding: 0.75rem 1rem 0.5rem 1rem;
  }
  
  .translations-container {
    padding: 0.75rem;
  }
  
  .translation-item {
    flex-direction: column;
    gap: 0.75rem;
  }
  
  .translation-number {
    align-self: flex-start;
    margin: 0;
  }
  
  .translation-content {
    padding: 0 0 0.75rem 0;
  }
  
  .translation-stats {
    flex-direction: column;
    gap: 0.5rem;
    align-items: flex-start;
  }
}

@media (max-width: 480px) {
  .editor-header {
    padding: 0.75rem;
  }
  
  .editor-title {
    font-size: 1.25rem;
  }
  
  .page-navigation {
    flex-wrap: wrap;
  }
}
</style>