<template>
  <div class="editor-container">
    <div class="editor-grid">
      <!-- JSON Editor -->
      <div class="editor-section">
        <h3 class="subtitle">Editor JSON</h3>
        <div class="monaco-wrapper">
          <div v-if="loading" class="loading-overlay">
            <div class="loading-spinner"></div>
            <p>Cargando datos...</p>
          </div>
          <vue-monaco-editor
            v-model:value="editorContent"
            language="json"
            wordWrap="on"
            theme="vs-dark"
            :options="editorOptions"
            @mount="handleMount"
          />
        </div>
        <div class="editor-actions">
          <button 
            class="save-button"
            :disabled="!isValidJson || loading"
            @click="saveChanges"
          >
            Guardar Cambios
          </button>
          <span v-if="!isValidJson" class="error-message">
            JSON inválido
          </span>
        </div>
      </div>

      <!-- PDF Preview -->
      <div class="preview-section">
        <h3 class="subtitle">Vista Previa</h3>
        <div class="pdf-viewer">
          <iframe
            :src="translatedPdfUrl"
            width="100%"
            frameborder="0"
            title="PDF Preview"
          ></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, shallowRef } from 'vue';
import { VueMonacoEditor } from '@guolao/vue-monaco-editor';
import { useTranslationStore } from '@/stores/translationStore';
import { getTranslationData, updateTranslationData } from '@/api/pdfs';
import type { editor } from 'monaco-editor';

const translationStore = useTranslationStore();
const currentTask = computed(() => translationStore.currentTask);

const editorContent = ref('');
const isValidJson = ref(true);
const editorRef = shallowRef();
const loading = ref(true);

const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
  wordWrap: 'on',
  minimap: { enabled: false },
  fontSize: 14,
  lineNumbers: 'off' as const,
  roundedSelection: false,
  scrollBeyondLastLine: false
};

const translatedPdfUrl = computed(() => 
  currentTask.value?.id ? 
  `${import.meta.env.VITE_API_URL}/pdfs/download/translated/${currentTask.value.id}` : 
  ''
);

const handleMount = (editor: editor.IStandaloneCodeEditor) => {
  editorRef.value = editor;
  editor.onDidChangeModelContent(() => {
    const value = editor.getValue();
    editorContent.value = value;
    try {
      JSON.parse(value);
      isValidJson.value = true;
    } catch {
      isValidJson.value = false;
    }
  });
  loadTranslationData();
};

async function loadTranslationData() {
  if (!currentTask.value?.id || !editorRef.value) {
    console.log('Cannot load translation data:', {
      taskId: currentTask.value?.id,
      hasEditor: !!editorRef.value
    });
    return;
  }
  
  loading.value = true;
  console.log('Loading translation data for task:', currentTask.value.id);
  try {
    const data = await getTranslationData(currentTask.value.id);
    console.log('Received translation data:', data);
    
    // Data should already be in the correct format with translations and positions
    const formattedJson = JSON.stringify(data, null, 2);
    editorContent.value = formattedJson;
    editorRef.value.setValue(formattedJson);
    editorRef.value.getAction('editor.action.formatDocument').run();
    console.log('Editor content set');
  } catch (error) {
    console.error('Error loading translation data:', error);
  } finally {
    loading.value = false;
  }
}

async function saveChanges() {
  if (!currentTask.value?.id || !isValidJson.value) return;
  
  loading.value = true;
  try {
    const data = JSON.parse(editorContent.value);
    
    // Sanitize text content to handle special characters
    const sanitizedTranslations = data.translations.map((translation: any) => ({
      ...translation,
      original_text: translation.original_text.replace(/'/g, ""),
      translated_text: translation.translated_text.replace(/'/g, "")
    }));

    const translationData = {
      translations: sanitizedTranslations,
      positions: data.positions
    };

    console.log('Saving data:', translationData);
    await updateTranslationData(currentTask.value.id, translationData);
    // Reload the PDF preview
    const iframe = document.querySelector('.pdf-viewer iframe') as HTMLIFrameElement;
    if (iframe) {
      iframe.src = iframe.src;
    }
  } catch (error) {
    console.error('Error saving translation data:', error);
  } finally {
    loading.value = false;
  }
}

// Watch for changes in currentTask
watch(() => currentTask.value?.id, (newId) => {
  if (newId && editorRef.value) {
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
  position: relative;
}

.subtitle {
  font-size: 1.125rem;
  margin: 0 0 1rem 0;
  color: #1a1b1e;
  font-weight: 600;
  flex-shrink: 0;
}

.monaco-wrapper {
  flex: 1;
  border-radius: 8px;
  border: 2px solid #e9ecef;
  background: #1e1e1e;
  position: relative;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 100;
  color: white;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.pdf-viewer {
  flex: 1;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  position: relative;
  min-height: 0;
}

.pdf-viewer iframe {
  height: 100%;
}

.editor-actions {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  position: relative;
  z-index: 50;
  flex-shrink: 0;
}

.save-button {
  padding: 0.5rem 1rem;
  background: linear-gradient(45deg, #228be6, #15aabf);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  z-index: 50;
}

.save-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(34, 139, 230, 0.25);
}

.save-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  color: #e03131;
  font-size: 0.875rem;
  position: relative;
  z-index: 50;
}
</style>
