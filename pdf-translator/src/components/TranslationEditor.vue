<template>
  <div class="editor-container">
    <div class="editor-grid">
      <!-- Panel Izquierdo: Editor de Textos -->
      <div class="editor-section">
        <h3 class="subtitle">Editor de traducciones</h3>
        
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <p>Cargando datos de traducción...</p>
        </div>
        
        <div v-else-if="translationPages.length === 0" class="empty-state">
          <p>No se encontraron datos de traducción</p>
        </div>
        
        <div v-else class="editor-content">
          <!-- 1. NAVEGADOR DE PÁGINAS -->
          <div class="page-navigator">
            <button
              v-for="page in translationPages"
              :key="page.page_number"
              :class="['page-tab', { 'active': page.page_number === currentPage + 1 }]"
              @click="setCurrentPage(page.page_number + 1)"
            >
              Pág {{ page.page_number + 1 }}
            </button>
          </div>

          <!-- 2. CONTENEDOR DE TRADUCCIONES CON SCROLL -->
          <div class="translations-container">
            <div 
              v-for="page in translationPages" 
              :key="page.page_number"
              v-show="page.page_number === currentPage + 1"
              class="page-group"
            >
              <!-- El título de la página ahora es estático arriba, se puede quitar si se prefiere -->
              <div 
                v-for="translation in page.translations"
                :key="translation.id"
                class="translation-item"
                :class="{ 'is-focused': focusedTranslationId === translation.id }"
              >
                <div class="original-text">
                  <label class="text-label">Texto original:</label>
                  <div class="text-display">{{ translation.original_text }}</div>
                </div>
                
                <div class="translated-text">
                  <label class="text-label" :for="`translation-${translation.id}`">
                    Texto traducido:
                  </label>
                  <textarea
                    :id="`translation-${translation.id}`"
                    v-model="translation.translated_text"
                    @input="markAsDirty"
                    @focus="focusedTranslationId = translation.id"
                    @blur="focusedTranslationId = null"
                    class="text-input"
                    rows="3"
                    placeholder="Escriba la traducción aquí..."
                  />
                </div>
              </div>
            </div>
          </div>
          
          <!-- 3. ACCIONES FLOTANTES (STICKY) -->
          <div class="editor-actions">
            <button 
              class="save-button"
              :disabled="loading || saving || !hasChanges"
              @click="saveChanges"
            >
              <span v-if="saving">Guardando...</span>
              <span v-else-if="hasChanges">Guardar cambios</span>
              <span v-else>Guardado</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Panel Derecho: Visor PDF -->
      <div class="preview-section">
        <h3 class="subtitle">Vista previa del PDF</h3>
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

    <!-- 4. Notificaciones (Toast) -->
    <div v-if="notification.message" :class="['notification', notification.type]">
      {{ notification.message }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue';
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

// --- NUEVOS ESTADOS PARA MEJORAR UX ---
const currentPage = ref(1);
const hasChanges = ref(false);
const focusedTranslationId = ref<string | number | null>(null);
const notification = reactive({ message: '', type: 'success' as 'success' | 'error', visible: false });

// Computed
const pdfPreviewUrl = computed(() => {
  if (!props.taskId) return '';
  // 5. NAVEGACIÓN EN EL PDF
  const baseUrl = `${import.meta.env.VITE_API_URL}/pdfs/download/translated/${props.taskId}?t=${pdfTimestamp.value}`;
  return `${baseUrl}#page=${currentPage.value}`;
});

// --- MÉTODOS MEJORADOS ---
function setCurrentPage(pageNumber: number) {
  currentPage.value = pageNumber;
}

function markAsDirty() {
  hasChanges.value = true;
}

function showNotification(message: string, type: 'success' | 'error' = 'success', duration = 3000) {
  notification.message = message;
  notification.type = type;
  setTimeout(() => {
    notification.message = '';
  }, duration);
}

async function loadTranslationData() {
  if (!props.taskId) {
    loading.value = false;
    return;
  }
  
  loading.value = true;
  hasChanges.value = false; // Resetear al cargar
  try {
    const data = await getTranslationData(props.taskId);
    translationPages.value = data.pages;
    if (data.pages.length > 0) {
      currentPage.value = data.pages[0].page_number + 1; // Empezar en la primera página
    }
  } catch (error) {
    console.error('Error loading translation data:', error);
    showNotification('Error al cargar los datos de traducción', 'error');
  } finally {
    loading.value = false;
  }
}

async function saveChanges() {
  if (!props.taskId || saving.value || !hasChanges.value) return;
  
  saving.value = true;
  try {
    const translationData: TranslationData = {
      pages: translationPages.value
    };
    
    await updateTranslationData(props.taskId, translationData);
    
    pdfTimestamp.value = Date.now();
    hasChanges.value = false; // Resetear estado de cambios
    
    showNotification('Cambios guardados con éxito', 'success');
  } catch (error) {
    console.error('Error saving translation data:', error);
    showNotification('Error al guardar los cambios', 'error');
  } finally {
    saving.value = false;
  }
}

// Watchers
watch(() => props.taskId, (newTaskId) => {
  if (newTaskId) {
    loadTranslationData();
  }
}, { immediate: true });
</script>

<style scoped>
/* Estilos existentes... (copiados y pegados) */
.editor-container {
  padding: 1rem;
  height: calc(100vh - 80px); /* Ajusta según tu header */
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative; /* Para las notificaciones */
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

/* --- NUEVOS ESTILOS Y AJUSTES --- */

.editor-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.page-navigator {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
  flex-shrink: 0;
  overflow-x: auto; /* Para muchas páginas en móvil */
  padding-bottom: 8px; /* Espacio para scrollbar */
}

.page-tab {
  padding: 0.5rem 1rem;
  border: 1px solid #dee2e6;
  background-color: #fff;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  color: #495057;
  transition: all 0.2s ease;
}

.page-tab:hover {
  background-color: #f1f3f5;
  border-color: #ced4da;
}

.page-tab.active {
  background-color: #228be6;
  color: white;
  border-color: #228be6;
  font-weight: 600;
}

.translations-container {
  flex: 1;
  overflow-y: auto;
  padding-right: 8px; /* Evita que el scrollbar se pegue al contenido */
}

.translation-item {
  background: white;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #e9ecef;
  transition: all 0.2s ease;
}

.translation-item.is-focused {
  border-color: #228be6;
  box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.15);
}

.original-text, .translated-text {
  margin-bottom: 0.75rem;
}

.translated-text { margin-bottom: 0; }

.text-label {
  display: block;
  font-size: 0.875rem;
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.25rem;
}

.text-display {
  background: #f1f3f5;
  padding: 0.5rem;
  border-radius: 4px;
  font-size: 0.875rem;
  line-height: 1.4;
  color: #495057;
  word-wrap: break-word;
}

.text-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ced4da;
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
}

.editor-actions {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e9ecef;
  flex-shrink: 0;
  background-color: #f8f9fa; /* Para que no se vea el contenido al hacer scroll */
}

.save-button {
  width: 100%;
  padding: 0.875rem;
  background: #495057; /* Color por defecto (Guardado) */
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
}

/* Estilo para cuando hay cambios */
.save-button:not(:disabled) {
  background: linear-gradient(45deg, #228be6, #15aabf);
}

.save-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25);
}

.save-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

/* Notificaciones */
.notification {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  color: white;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  transition: opacity 0.3s ease;
  z-index: 1000;
}
.notification.success {
  background-color: #28a745;
}
.notification.error {
  background-color: #dc3545;
}

@media (max-width: 1024px) {
  .editor-grid {
    grid-template-columns: 1fr;
    grid-template-rows: auto auto; /* O 1fr 1fr si quieres dividir el espacio equitativamente */
    min-height: 0;
  }
}
</style>