<template>
  <div class="layout">
    <header class="header">
      <div class="header-content">
        <h1 class="title">PDF Translator</h1>
        <div class="nav-actions">
          <button
            v-if="authStore.token"
            class="btn-logout"
            @click="authStore.clearToken"
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </header>

    <main class="main-content">
      <router-view />
    </main>

    <footer class="footer">
      <p class="copyright">
        © {{ new Date().getFullYear() }} PDF Translator
      </p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/authStore';

const authStore = useAuthStore();
</script>

<style scoped>
.layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f8f9fa;
}

.header {
  height: 70px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  background: white;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
  transition: box-shadow 0.3s ease;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.title {
  font-size: 1.625rem;
  margin: 0;
  font-weight: 700;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
}

.btn-logout {
  padding: 0.625rem 1.25rem;
  border: none;
  background: transparent;
  color: #228be6;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9375rem;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.btn-logout:hover {
  background: rgba(34, 139, 230, 0.1);
  transform: translateY(-1px);
}

.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  animation: fadeIn 0.3s ease-out;
}

.footer {
  height: 50px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
}

.copyright {
  font-size: 0.8125rem;
  color: #495057;
  margin: 0;
  font-weight: 500;
  letter-spacing: -0.01em;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
