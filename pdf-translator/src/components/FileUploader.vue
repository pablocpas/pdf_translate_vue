<template>
  <div class="form-group">
    <label class="form-label">
      Archivo PDF <span class="required">*</span>
    </label>
    <input
      type="file"
      accept="application/pdf"
      @change="handleFileChange"
      class="file-input"
      :class="{ 'has-error': error }"
      ref="fileInput"
    />
    <div class="file-info" v-if="modelValue">
      <span class="file-name">{{ modelValue.name }}</span>
      <span class="file-size">({{ fileSize }})</span>
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

const fileSize = computed(() => {
  if (!props.modelValue) return '';
  const size = props.modelValue.size / 1024; // KB
  return size > 1024 
    ? `${(size / 1024).toFixed(2)} MB`
    : `${Math.round(size)} KB`;
});

const handleFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (input.files?.length) {
    const file = input.files[0];
    
    // Validate file type
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      emit('update:modelValue', null);
      if (fileInput.value) fileInput.value.value = '';
      return;
    }
    
    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      emit('update:modelValue', null);
      if (fileInput.value) fileInput.value.value = '';
      return;
    }

    emit('update:modelValue', file);
  } else {
    emit('update:modelValue', null);
  }
};
</script>

<style scoped>
.form-group {
  margin-bottom: 1.75rem;
}

.form-label {
  display: block;
  margin-bottom: 0.625rem;
  font-weight: 600;
  color: #1a1b1e;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.required {
  color: #fa5252;
  margin-left: 4px;
}

.file-input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e9ecef;
  border-radius: 8px;
  background: white;
  transition: all 0.2s ease;
  font-size: 0.9375rem;
  letter-spacing: -0.01em;
}

.file-input:hover {
  border-color: #74c0fc;
}

.file-input:focus {
  outline: none;
  border-color: #228be6;
  box-shadow: 0 0 0 3px rgba(34, 139, 230, 0.15);
}

.has-error {
  border-color: #fa5252;
}

.error-text {
  display: block;
  margin-top: 0.5rem;
  color: #fa5252;
  font-size: 0.8125rem;
  font-weight: 500;
  animation: shake 0.5s ease-in-out;
  letter-spacing: -0.01em;
}

.file-info {
  margin-top: 0.625rem;
  font-size: 0.875rem;
  color: #495057;
  padding: 0.5rem 0.75rem;
  background: #f8f9fa;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  letter-spacing: -0.01em;
}

.file-name {
  font-weight: 600;
  color: #228be6;
  letter-spacing: -0.01em;
}

.file-size {
  color: #868e96;
  font-weight: 500;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
</style>
