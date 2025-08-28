<template>
  <div class="layout">
    <header class="header">
      <div class="header-content">
        <router-link to="/" class="title-link">
          <h1 class="title">PDF Translator</h1>
        </router-link>
        <div class="controls-container">
          <div class="nav-actions">
            <a
              href="https://github.com/pablocpas/pdf_translate_vue"
              target="_blank"
              rel="noopener noreferrer"
              class="btn-github"
            >
              <svg height="20" width="20" viewBox="0 0 16 16" class="github-icon">
                <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
              </svg>
              GitHub
            </a>
          </div>
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

.controls-container {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.title-link {
  text-decoration: none;
}

.title {
  font-size: 1.625rem;
  margin: 0;
  font-weight: 700;
  background: linear-gradient(45deg, #228be6, #15aabf);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
  transition: opacity 0.2s ease;
}

.title:hover {
  opacity: 0.85;
}

.btn-github,
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
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
}

.btn-github:hover,
.btn-logout:hover {
  background: rgba(34, 139, 230, 0.1);
  transform: translateY(-1px);
}

.main-content {
  flex: 1;
  padding: 1rem;
  max-width: 1400px;
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
