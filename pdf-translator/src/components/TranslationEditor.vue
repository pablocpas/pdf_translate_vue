<template>
  <div class="editor-container">
    <div class="editor-grid">
      <!-- JSON Editor -->
      <div class="editor-section">
        <h3 class="subtitle">Editor JSON</h3>
        <div class="monaco-wrapper">
          <vue-monaco-editor
            v-model:value="editorContent"
            language="json"
            theme="vs-dark"
            :options="editorOptions"
            @mount="handleMount"
          />
        </div>
        <div class="editor-actions">
          <button 
            class="save-button"
            :disabled="!isValidJson"
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
            height="800"
            frameborder="0"
            title="PDF Preview"
          ></iframe>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, shallowRef } from 'vue';
import { VueMonacoEditor } from '@guolao/vue-monaco-editor';
import { useTranslationStore } from '@/stores/translationStore';
import { getTranslationData, updateTranslationData } from '@/api/pdfs';

const translationStore = useTranslationStore();
const currentTask = computed(() => translationStore.currentTask);

const editorContent = ref('');
const isValidJson = ref(true);
const editorRef = shallowRef();

import type { editor } from 'monaco-editor';

const editorOptions: editor.IStandaloneEditorConstructionOptions = {
  automaticLayout: true,
  formatOnType: true,
  formatOnPaste: true,
  minimap: { enabled: false },
  fontSize: 14,
  lineNumbers: 'on' as const,
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
  if (!currentTask.value?.id || !editorRef.value) return;
  
  try {
    const data = await getTranslationData(currentTask.value.id);
    const formattedJson = JSON.stringify(data, null, 2);
    editorContent.value = formattedJson;
    editorRef.value.setValue(formattedJson);
  } catch (error) {
    console.error('Error loading translation data:', error);
  }
}

async function saveChanges() {
  if (!currentTask.value?.id || !isValidJson.value) return;
  
  try {
    const data = JSON.parse(editorContent.value);
    await updateTranslationData(currentTask.value.id, { pages: data });
    // Reload the PDF preview
    const iframe = document.querySelector('.pdf-viewer iframe') as HTMLIFrameElement;
    if (iframe) {
      iframe.src = iframe.src;
    }
  } catch (error) {
    console.error('Error saving translation data:', error);
  }
}

</script>

<style scoped>
.editor-container {
  padding: 1rem;
}

.editor-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
  height: calc(100vh - 200px);
}

.editor-section, .preview-section {
  background: #f8f9fa;
  border-radius: 12px;
  padding: 1rem;
  display: flex;
  flex-direction: column;
}

.subtitle {
  font-size: 1.125rem;
  margin: 0 0 1rem 0;
  color: #1a1b1e;
  font-weight: 600;
}

.monaco-wrapper {
  flex-grow: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #e9ecef;
  background: #1e1e1e;
  height: calc(100% - 100px);
}

.pdf-viewer {
  flex-grow: 1;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}

.editor-actions {
  margin-top: 1rem;
  display: flex;
  align-items: center;
  gap: 1rem;
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
}
</style>
