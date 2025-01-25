<template>
  <div class="error-banner" :class="errorSeverity">
    <!-- Network Error Icon -->
    <svg v-if="isNetworkError" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <line x1="1" y1="1" x2="23" y2="23"></line>
      <path d="M16.72 11.06A10.94 10.94 0 0 1 19 12.55"></path>
      <path d="M5 12.55a10.94 10.94 0 0 1 5.17-2.39"></path>
      <path d="M10.71 5.05A16 16 0 0 1 22.58 9"></path>
      <path d="M1.42 9a15.91 15.91 0 0 1 4.7-2.88"></path>
      <path d="M8.53 16.11a6 6 0 0 1 6.95 0"></path>
      <line x1="12" y1="20" x2="12.01" y2="20"></line>
    </svg>
    <!-- File Error Icon -->
    <svg v-else-if="isFileError" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
      <polyline points="13 2 13 9 20 9"></polyline>
      <line x1="9" y1="14" x2="15" y2="14"></line>
    </svg>
    <!-- Translation Error Icon -->
    <svg v-else-if="isTranslationError" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M5 8h14"></path>
      <path d="M5 12h14"></path>
      <path d="M5 16h14"></path>
      <path d="M3 20h18"></path>
      <circle cx="12" cy="4" r="2"></circle>
    </svg>
    <!-- Default Error Icon -->
    <svg v-else xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    </svg>
    
    <div class="error-content">
      <span class="error-title">{{ title }}</span>
      <span class="error-message">{{ message }}</span>
      <button v-if="showRetry" @click="$emit('retry')" class="retry-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/>
        </svg>
        Intentar de nuevo
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { ErrorCode } from '@/types/api';

const props = defineProps<{
  errorCode?: ErrorCode;
  message: string;
  showRetry?: boolean;
}>();

defineEmits<{
  (e: 'retry'): void;
}>();

const isNetworkError = computed(() => {
  return props.errorCode === ErrorCode.NETWORK_ERROR || 
         props.errorCode === ErrorCode.TIMEOUT || 
         props.errorCode === ErrorCode.SERVER_ERROR;
});

const isFileError = computed(() => {
  return props.errorCode === ErrorCode.FILE_TOO_LARGE || 
         props.errorCode === ErrorCode.INVALID_FILE_TYPE || 
         props.errorCode === ErrorCode.FILE_CORRUPTED;
});

const isTranslationError = computed(() => {
  return props.errorCode === ErrorCode.TRANSLATION_FAILED || 
         props.errorCode === ErrorCode.LANGUAGE_NOT_SUPPORTED || 
         props.errorCode === ErrorCode.OCR_FAILED;
});

const errorSeverity = computed(() => {
  if (isNetworkError.value) return 'error-network';
  if (isFileError.value) return 'error-file';
  if (isTranslationError.value) return 'error-translation';
  return 'error-general';
});

const title = computed(() => {
  if (isNetworkError.value) return 'Error de conexión';
  if (isFileError.value) return 'Error en el archivo';
  if (isTranslationError.value) return 'Error de traducción';
  return 'Error';
});
</script>

<style scoped>
.error-banner {
  background-color: #fff5f5;
  border: 2px solid #ffc9c9;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  margin-bottom: 2rem;
  font-size: 0.95rem;
  animation: shake 0.5s ease-in-out;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  max-width: 400px;
  margin: 0 auto;
}

.error-banner.error-network {
  background-color: #fff4e6;
  border-color: #ffd8a8;
  color: #e8590c;
}

.error-banner.error-file {
  background-color: #f8f0fc;
  border-color: #eebefa;
  color: #ae3ec9;
}

.error-banner.error-translation {
  background-color: #e7f5ff;
  border-color: #a5d8ff;
  color: #1971c2;
}

.error-banner.error-general {
  background-color: #fff5f5;
  border-color: #ffc9c9;
  color: #e03131;
}

.error-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.error-title {
  font-weight: 600;
  font-size: 1rem;
}

.error-message {
  color: inherit;
  opacity: 0.9;
  font-size: 0.9rem;
  line-height: 1.4;
}

.retry-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 8px;
  background-color: rgba(0, 0, 0, 0.1);
  color: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.retry-button:hover {
  background-color: rgba(0, 0, 0, 0.15);
}

.retry-button:active {
  transform: translateY(1px);
}

.retry-button svg {
  opacity: 0.8;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
</style>
