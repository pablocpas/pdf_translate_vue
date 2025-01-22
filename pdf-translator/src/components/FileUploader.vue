<template>
  <div class="form-group">
    <label class="form-label">
      Archivo PDF <span class="required">*</span>
      <span class="tooltip-icon" title="Tamaño máximo permitido: 10MB">?</span>
    </label>
    <div
      class="dropzone"
      :class="{
        'dropzone-active': isDragging,
        'dropzone-has-file': modelValue,
        'has-error': error
      }"
      @dragenter.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @dragover.prevent
      @drop.prevent="handleDrop"
      @click="triggerFileInput"
    >
      <input
        type="file"
        accept="application/pdf"
        @change="handleFileChange"
        class="file-input-hidden"
        ref="fileInput"
      />
      
      <div v-if="!modelValue" class="dropzone-placeholder">
        <div class="upload-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <div class="upload-text">
          <span class="primary-text">Arrastra tu archivo PDF aquí o</span>
          <span class="secondary-text">haz clic para seleccionar</span>
        </div>
      </div>

      <div v-else class="file-preview">
        <div class="file-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <line x1="9" y1="15" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="file-details">
          <span class="file-name">{{ modelValue.name }}</span>
          <span class="file-size">{{ fileSize }}</span>
        </div>
        <button class="remove-file" @click.stop="removeFile">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>
    <span v-if="error" class="error-text">{{ error }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';

// Constants
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ['application/pdf'];

const props = defineProps<{
  modelValue: File | null;
  error?: string;
}>();

const emit = defineEmits<{
  (e: 'update:modelValue', value: File | null): void;
}>();

const fileInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);

const fileSize = computed(() => {
  if (!props.modelValue) return '';
  const size = props.modelValue.size / 1024; // KB
  return size > 1024 
    ? `${(size / 1024).toFixed(2)} MB`
    : `${Math.round(size)} KB`;
});

const validateFile = (file: File): boolean => {
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    return false;
  }
  
  if (file.size > MAX_FILE_SIZE) {
    return false;
  }

  return true;
};

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) {
    const file = input.files[0];
    if (validateFile(file)) {
      emit('update:modelValue', file);
    } else {
      emit('update:modelValue', null);
    }
  }
  if (fileInput.value) fileInput.value.value = '';
};

const handleDrop = (event: DragEvent) => {
  isDragging.value = false;
  const file = event.dataTransfer?.files[0];
  if (file && validateFile(file)) {
    emit('update:modelValue', file);
  }
};

const triggerFileInput = () => {
  fileInput.value?.click();
};

const removeFile = () => {
  emit('update:modelValue', null);
  if (fileInput.value) fileInput.value.value = '';
};
</script>

<style scoped>
.form-group {
  margin-bottom: 1.25rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.required {
  color: #fa5252;
  margin-left: 4px;
}

.tooltip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #e9ecef;
  color: #495057;
  font-size: 11px;
  margin-left: 6px;
  cursor: help;
  transition: all 0.2s ease;
}

.tooltip-icon:hover {
  background: #dee2e6;
  color: #228be6;
}

.dropzone {
  width: 100%;
  min-height: 160px;
  border: 2px dashed #e9ecef;
  border-radius: 12px;
  background: #f8f9fa;
  transition: all 0.2s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  position: relative;
}

.dropzone:hover {
  border-color: #74c0fc;
  background: #f1f3f5;
}

.dropzone-active {
  border-color: #228be6;
  background: rgba(34, 139, 230, 0.05);
}

.dropzone-has-file {
  background: white;
  border-style: solid;
  border-color: #228be6;
}

.has-error {
  border-color: #fa5252;
  background: #fff5f5;
}

.file-input-hidden {
  display: none;
}

.dropzone-placeholder {
  text-align: center;
}

.upload-icon {
  color: #228be6;
  margin-bottom: 0.75rem;
}

.upload-text {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.primary-text {
  color: #495057;
  font-size: 1rem;
  font-weight: 500;
}

.secondary-text {
  color: #228be6;
  font-weight: 600;
  font-size: 0.9375rem;
}

.file-preview {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 0.75rem;
  background: white;
  border-radius: 8px;
}

.file-icon {
  color: #228be6;
  flex-shrink: 0;
}

.file-details {
  flex: 1;
  min-width: 0;
}

.file-name {
  display: block;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  margin-bottom: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-size {
  display: block;
  color: #868e96;
  font-size: 0.8125rem;
  font-weight: 500;
}

.remove-file {
  background: none;
  border: none;
  padding: 0.5rem;
  color: #868e96;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.remove-file:hover {
  color: #fa5252;
  background: #fff5f5;
}

.error-text {
  display: block;
  margin-top: 0.5rem;
  color: #fa5252;
  font-size: 0.8125rem;
  font-weight: 500;
  animation: shake 0.5s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
</style>
